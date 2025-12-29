"""
Proxy Pool Abstraction with Rotation, Health Scoring, Retry/Backoff, and Circuit Breaker.

Features:
- Proxy rotation with weighted selection based on health
- Health scoring with success/failure tracking
- Exponential backoff for failed proxies
- Circuit breaker pattern to prevent cascading failures
- Automatic proxy recovery and health monitoring
- Integration with structured logging and metrics
"""

import asyncio
import time
import random
import math
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import threading
from contextlib import asynccontextmanager

# Try to import metrics for integration
try:
    from logging_metrics import metrics
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    metrics = None


# ============================================================================
# PROXY CONFIGURATION
# ============================================================================

@dataclass
class ProxyConfig:
    """Configuration for a single proxy."""
    server: str  # e.g., "http://proxy.example.com:8080"
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"  # http, https, socks5
    region: Optional[str] = None  # Optional region identifier
    tags: List[str] = field(default_factory=list)  # Optional tags for filtering
    
    def to_playwright_config(self) -> Dict[str, Any]:
        """Convert to Playwright proxy configuration."""
        config = {"server": self.server}
        if self.username and self.password:
            config["username"] = self.username
            config["password"] = self.password
        return config
    
    def __hash__(self):
        return hash(self.server)
    
    def __eq__(self, other):
        if not isinstance(other, ProxyConfig):
            return False
        return self.server == other.server


class ProxyState(Enum):
    """Proxy state for circuit breaker."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit breaker open, proxy failing
    HALF_OPEN = "half_open"  # Testing if proxy recovered


@dataclass
class ProxyHealth:
    """Health metrics for a proxy."""
    proxy: ProxyConfig
    state: ProxyState = ProxyState.CLOSED
    
    # Success/failure tracking
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    
    # Timing metrics
    total_response_time: float = 0.0
    last_success_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    last_used_time: Optional[datetime] = None
    
    # Circuit breaker state
    consecutive_failures: int = 0
    circuit_breaker_opened_at: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None
    
    # Backoff state
    backoff_until: Optional[datetime] = None
    backoff_multiplier: float = 1.0
    
    def get_success_rate(self) -> float:
        """Calculate success rate (0.0 to 1.0)."""
        if self.total_requests == 0:
            return 1.0  # Assume healthy if never used
        return self.successful_requests / self.total_requests
    
    def get_avg_response_time(self) -> float:
        """Calculate average response time in seconds."""
        if self.successful_requests == 0:
            return 0.0
        return self.total_response_time / self.successful_requests
    
    def get_health_score(self) -> float:
        """Calculate health score (0.0 to 1.0) based on multiple factors."""
        if self.total_requests == 0:
            return 1.0  # New proxy, assume healthy
        
        # Base score from success rate (0-0.6 weight)
        success_rate = self.get_success_rate()
        base_score = success_rate * 0.6
        
        # Recency bonus (0-0.2 weight) - recent success is good
        recency_score = 0.0
        if self.last_success_time:
            time_since_success = (datetime.now(timezone.utc) - self.last_success_time).total_seconds()
            # Decay over 1 hour
            recency_score = max(0.0, 1.0 - (time_since_success / 3600.0)) * 0.2
        
        # Response time penalty (0-0.2 weight) - faster is better
        response_time_score = 0.0
        avg_time = self.get_avg_response_time()
        if avg_time > 0:
            # Penalize if average > 5 seconds
            response_time_score = max(0.0, 1.0 - (avg_time / 5.0)) * 0.2
        
        # Circuit breaker penalty
        circuit_penalty = 0.0
        if self.state == ProxyState.OPEN:
            circuit_penalty = -0.5  # Heavy penalty for open circuit
        elif self.state == ProxyState.HALF_OPEN:
            circuit_penalty = -0.2  # Moderate penalty for half-open
        
        total_score = base_score + recency_score + response_time_score + circuit_penalty
        return max(0.0, min(1.0, total_score))
    
    def is_available(self) -> bool:
        """Check if proxy is available for use."""
        now = datetime.now(timezone.utc)
        
        # Check circuit breaker
        if self.state == ProxyState.OPEN:
            if self.cooldown_until and now < self.cooldown_until:
                return False
            # Try half-open state
            self.state = ProxyState.HALF_OPEN
            return True
        
        # Check backoff
        if self.backoff_until and now < self.backoff_until:
            return False
        
        return True
    
    def record_success(self, response_time: float = 0.0):
        """Record a successful request."""
        self.total_requests += 1
        self.successful_requests += 1
        self.total_response_time += response_time
        self.last_success_time = datetime.now(timezone.utc)
        self.last_used_time = self.last_success_time
        self.consecutive_failures = 0
        
        # Reset circuit breaker if half-open
        if self.state == ProxyState.HALF_OPEN:
            self.state = ProxyState.CLOSED
            self.circuit_breaker_opened_at = None
        
        # Reset backoff
        self.backoff_until = None
        self.backoff_multiplier = 1.0
    
    def record_failure(self, error_category: str = "unknown"):
        """Record a failed request."""
        self.total_requests += 1
        self.failed_requests += 1
        self.last_failure_time = datetime.now(timezone.utc)
        self.last_used_time = self.last_failure_time
        self.consecutive_failures += 1
        
        # Apply exponential backoff
        base_backoff = 60.0  # 1 minute base
        backoff_seconds = base_backoff * (2 ** min(self.consecutive_failures - 1, 5))  # Cap at 32 minutes
        self.backoff_until = datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds)
        self.backoff_multiplier = min(32.0, 2.0 ** self.consecutive_failures)
        
        # Circuit breaker logic
        failure_threshold = 5  # Open circuit after 5 consecutive failures
        if self.consecutive_failures >= failure_threshold and self.state == ProxyState.CLOSED:
            self.state = ProxyState.OPEN
            self.circuit_breaker_opened_at = datetime.now(timezone.utc)
            # Cooldown period: 5 minutes
            self.cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=5)
        
        # If half-open and fails, immediately open again
        if self.state == ProxyState.HALF_OPEN:
            self.state = ProxyState.OPEN
            self.circuit_breaker_opened_at = datetime.now(timezone.utc)
            self.cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=5)


# ============================================================================
# PROXY POOL MANAGER
# ============================================================================

class ProxyPool:
    """Proxy pool with rotation, health scoring, retry/backoff, and circuit breaker."""
    
    def __init__(
        self,
        proxies: Optional[List[ProxyConfig]] = None,
        max_concurrent_per_proxy: int = 3,
        rotation_strategy: str = "weighted_random",  # weighted_random, round_robin, health_only
        min_health_score: float = 0.3,  # Minimum health score to use proxy
        enable_circuit_breaker: bool = True,
        circuit_breaker_failure_threshold: int = 5,
        circuit_breaker_cooldown_seconds: int = 300,
    ):
        """
        Initialize proxy pool.
        
        Args:
            proxies: List of proxy configurations
            max_concurrent_per_proxy: Maximum concurrent requests per proxy
            rotation_strategy: Strategy for proxy selection
            min_health_score: Minimum health score to use proxy
            enable_circuit_breaker: Enable circuit breaker pattern
            circuit_breaker_failure_threshold: Failures before opening circuit
            circuit_breaker_cooldown_seconds: Cooldown period for circuit breaker
        """
        self.proxies: Dict[str, ProxyHealth] = {}
        self.max_concurrent_per_proxy = max_concurrent_per_proxy
        self.rotation_strategy = rotation_strategy
        self.min_health_score = min_health_score
        self.enable_circuit_breaker = enable_circuit_breaker
        self.circuit_breaker_failure_threshold = circuit_breaker_failure_threshold
        self.circuit_breaker_cooldown_seconds = circuit_breaker_cooldown_seconds
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Current proxy index for round-robin
        self._round_robin_index = 0
        
        # Active request tracking per proxy
        self._active_requests: Dict[str, int] = defaultdict(int)
        
        # Add initial proxies
        if proxies:
            for proxy in proxies:
                self.add_proxy(proxy)
        
        # Metrics tracking
        self._metrics = {
            "proxy_selections_total": 0,
            "proxy_successes_total": 0,
            "proxy_failures_total": 0,
            "circuit_breaker_opens_total": 0,
            "proxy_rotations_total": 0,
        }
    
    def add_proxy(self, proxy: ProxyConfig):
        """Add a proxy to the pool."""
        proxy_key = self._get_proxy_key(proxy)
        with self._lock:
            if proxy_key not in self.proxies:
                self.proxies[proxy_key] = ProxyHealth(proxy=proxy)
    
    def remove_proxy(self, proxy: ProxyConfig):
        """Remove a proxy from the pool."""
        proxy_key = self._get_proxy_key(proxy)
        with self._lock:
            if proxy_key in self.proxies:
                del self.proxies[proxy_key]
                if proxy_key in self._active_requests:
                    del self._active_requests[proxy_key]
    
    def get_proxy(self, tags: Optional[List[str]] = None, exclude_proxies: Optional[List[str]] = None) -> Optional[ProxyConfig]:
        """
        Get an available proxy based on rotation strategy.
        
        Args:
            tags: Optional tags to filter proxies
            exclude_proxies: List of proxy keys to exclude
            
        Returns:
            ProxyConfig or None if no available proxy
        """
        with self._lock:
            available_proxies = self._get_available_proxies(tags=tags, exclude_proxies=exclude_proxies)
            
            if not available_proxies:
                return None
            
            if self.rotation_strategy == "round_robin":
                proxy = self._select_round_robin(available_proxies)
            elif self.rotation_strategy == "health_only":
                proxy = self._select_best_health(available_proxies)
            else:  # weighted_random (default)
                proxy = self._select_weighted_random(available_proxies)
            
            if proxy:
                proxy_key = self._get_proxy_key(proxy)
                self._active_requests[proxy_key] += 1
                self._metrics["proxy_selections_total"] += 1
                self._metrics["proxy_rotations_total"] += 1
                
                # Update external metrics if available
                if METRICS_AVAILABLE and metrics:
                    metrics.increment("proxy_selections_total")
            
            return proxy
    
    def release_proxy(self, proxy: ProxyConfig):
        """Release a proxy after use (decrement active request count)."""
        proxy_key = self._get_proxy_key(proxy)
        with self._lock:
            if proxy_key in self._active_requests:
                self._active_requests[proxy_key] = max(0, self._active_requests[proxy_key] - 1)
    
    def record_success(self, proxy: ProxyConfig, response_time: float = 0.0):
        """Record a successful request for a proxy."""
        proxy_key = self._get_proxy_key(proxy)
        with self._lock:
            if proxy_key in self.proxies:
                self.proxies[proxy_key].record_success(response_time)
                self._metrics["proxy_successes_total"] += 1
                
                # Update external metrics if available
                if METRICS_AVAILABLE and metrics:
                    metrics.increment("proxy_successes_total")
                    metrics.observe_histogram("proxy_response_time_seconds", response_time)
            self.release_proxy(proxy)
    
    def record_failure(self, proxy: ProxyConfig, error_category: str = "unknown"):
        """Record a failed request for a proxy."""
        proxy_key = self._get_proxy_key(proxy)
        with self._lock:
            if proxy_key in self.proxies:
                self.proxies[proxy_key].record_failure(error_category)
                if self.proxies[proxy_key].state == ProxyState.OPEN:
                    self._metrics["circuit_breaker_opens_total"] += 1
                    # Update external metrics if available
                    if METRICS_AVAILABLE and metrics:
                        metrics.increment("proxy_circuit_breaker_opens_total")
                self._metrics["proxy_failures_total"] += 1
                
                # Update external metrics if available
                if METRICS_AVAILABLE and metrics:
                    metrics.increment("proxy_failures_total", labels={"error_category": error_category})
            self.release_proxy(proxy)
    
    def get_proxy_health(self, proxy: ProxyConfig) -> Optional[ProxyHealth]:
        """Get health metrics for a proxy."""
        proxy_key = self._get_proxy_key(proxy)
        with self._lock:
            return self.proxies.get(proxy_key)
    
    def get_all_proxy_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health metrics for all proxies."""
        with self._lock:
            return {
                self._get_proxy_key(health.proxy): {
                    "proxy": health.proxy.server,
                    "state": health.state.value,
                    "health_score": health.get_health_score(),
                    "success_rate": health.get_success_rate(),
                    "avg_response_time": health.get_avg_response_time(),
                    "total_requests": health.total_requests,
                    "successful_requests": health.successful_requests,
                    "failed_requests": health.failed_requests,
                    "consecutive_failures": health.consecutive_failures,
                    "active_requests": self._active_requests.get(self._get_proxy_key(health.proxy), 0),
                    "last_success_time": health.last_success_time.isoformat() if health.last_success_time else None,
                    "last_failure_time": health.last_failure_time.isoformat() if health.last_failure_time else None,
                }
                for health in self.proxies.values()
            }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get pool metrics."""
        with self._lock:
            return {
                **self._metrics,
                "total_proxies": len(self.proxies),
                "available_proxies": len(self._get_available_proxies()),
                "active_requests": sum(self._active_requests.values()),
            }
    
    def reset_proxy(self, proxy: ProxyConfig):
        """Reset a proxy's health metrics (for testing/recovery)."""
        proxy_key = self._get_proxy_key(proxy)
        with self._lock:
            if proxy_key in self.proxies:
                health = self.proxies[proxy_key]
                health.state = ProxyState.CLOSED
                health.consecutive_failures = 0
                health.backoff_until = None
                health.cooldown_until = None
                health.circuit_breaker_opened_at = None
    
    # Private methods
    
    def _get_proxy_key(self, proxy: ProxyConfig) -> str:
        """Get unique key for proxy."""
        return proxy.server
    
    def _get_available_proxies(
        self, 
        tags: Optional[List[str]] = None,
        exclude_proxies: Optional[List[str]] = None
    ) -> List[ProxyConfig]:
        """Get list of available proxies."""
        available = []
        exclude_set = set(exclude_proxies or [])
        
        for health in self.proxies.values():
            proxy_key = self._get_proxy_key(health.proxy)
            
            # Check exclusions
            if proxy_key in exclude_set:
                continue
            
            # Check tags filter
            if tags and not any(tag in health.proxy.tags for tag in tags):
                continue
            
            # Check availability
            if not health.is_available():
                continue
            
            # Check health score
            if health.get_health_score() < self.min_health_score:
                continue
            
            # Check concurrent request limit
            active = self._active_requests.get(proxy_key, 0)
            if active >= self.max_concurrent_per_proxy:
                continue
            
            available.append(health.proxy)
        
        return available
    
    def _select_round_robin(self, proxies: List[ProxyConfig]) -> Optional[ProxyConfig]:
        """Select proxy using round-robin strategy."""
        if not proxies:
            return None
        
        proxy = proxies[self._round_robin_index % len(proxies)]
        self._round_robin_index = (self._round_robin_index + 1) % len(proxies)
        return proxy
    
    def _select_best_health(self, proxies: List[ProxyConfig]) -> Optional[ProxyConfig]:
        """Select proxy with best health score."""
        if not proxies:
            return None
        
        best_proxy = None
        best_score = -1.0
        
        for proxy in proxies:
            proxy_key = self._get_proxy_key(proxy)
            health = self.proxies.get(proxy_key)
            if health:
                score = health.get_health_score()
                if score > best_score:
                    best_score = score
                    best_proxy = proxy
        
        return best_proxy
    
    def _select_weighted_random(self, proxies: List[ProxyConfig]) -> Optional[ProxyConfig]:
        """Select proxy using weighted random based on health scores."""
        if not proxies:
            return None
        
        # Calculate weights based on health scores
        weights = []
        for proxy in proxies:
            proxy_key = self._get_proxy_key(proxy)
            health = self.proxies.get(proxy_key)
            if health:
                # Weight = health_score^2 to favor healthier proxies more
                weight = health.get_health_score() ** 2
                weights.append(weight)
            else:
                weights.append(0.0)
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight == 0:
            # Fallback to uniform random
            return random.choice(proxies)
        
        # Select based on weighted random
        rand = random.uniform(0, total_weight)
        cumulative = 0.0
        for i, weight in enumerate(weights):
            cumulative += weight
            if rand <= cumulative:
                return proxies[i]
        
        # Fallback
        return proxies[-1]


# ============================================================================
# CONTEXT MANAGER FOR PROXY USAGE
# ============================================================================

@asynccontextmanager
async def use_proxy(
    proxy_pool: ProxyPool,
    tags: Optional[List[str]] = None,
    exclude_proxies: Optional[List[str]] = None,
    max_retries: int = 3,
    base_backoff: float = 1.0,
):
    """
    Context manager for using a proxy with automatic retry and backoff.
    
    Usage:
        async with use_proxy(proxy_pool) as proxy:
            if proxy:
                # Use proxy
                context = await browser.new_context(proxy=proxy.to_playwright_config())
                # ... do work ...
                proxy_pool.record_success(proxy)
            else:
                # No proxy available
                pass
    """
    proxy = None
    last_error = None
    
    for attempt in range(max_retries):
        try:
            proxy = proxy_pool.get_proxy(tags=tags, exclude_proxies=exclude_proxies)
            if proxy:
                yield proxy
                return
            else:
                # No proxy available, wait and retry
                if attempt < max_retries - 1:
                    backoff_time = base_backoff * (2 ** attempt)
                    await asyncio.sleep(backoff_time)
        except Exception as e:
            last_error = e
            if proxy:
                proxy_pool.record_failure(proxy, error_category="unknown")
            if attempt < max_retries - 1:
                backoff_time = base_backoff * (2 ** attempt)
                await asyncio.sleep(backoff_time)
            proxy = None
    
    # All retries exhausted
    yield None
    if last_error:
        raise last_error


# ============================================================================
# PROXY POOL FROM ENVIRONMENT
# ============================================================================

def create_proxy_pool_from_env() -> Optional[ProxyPool]:
    """Create proxy pool from environment variables."""
    import os
    
    # Single proxy from env (backward compatibility)
    proxy_server = os.environ.get("PROXY_SERVER")
    if proxy_server:
        proxy_config = ProxyConfig(
            server=proxy_server,
            username=os.environ.get("PROXY_USERNAME"),
            password=os.environ.get("PROXY_PASSWORD"),
        )
        return ProxyPool(proxies=[proxy_config])
    
    # Multiple proxies from env (comma-separated)
    proxy_list = os.environ.get("PROXY_LIST")
    if proxy_list:
        proxies = []
        for proxy_str in proxy_list.split(","):
            proxy_str = proxy_str.strip()
            if proxy_str:
                # Format: "http://user:pass@host:port" or "http://host:port"
                if "@" in proxy_str:
                    # Has auth
                    parts = proxy_str.split("@")
                    auth_part = parts[0].replace("http://", "").replace("https://", "")
                    server_part = parts[1]
                    if ":" in auth_part:
                        username, password = auth_part.split(":", 1)
                    else:
                        username, password = auth_part, None
                    server = f"http://{server_part}"
                else:
                    server = proxy_str
                    username = os.environ.get("PROXY_USERNAME")
                    password = os.environ.get("PROXY_PASSWORD")
                
                proxies.append(ProxyConfig(
                    server=server,
                    username=username,
                    password=password,
                ))
        
        if proxies:
            return ProxyPool(proxies=proxies)
    
    return None

