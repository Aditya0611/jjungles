"""
Proxy Pool Manager with rotation, health scoring, retry/backoff, and circuit breaker.

Provides a robust proxy management system for multi-platform scraping with:
- Automatic rotation
- Health scoring and tracking
- Retry with exponential backoff
- Circuit breaker pattern
- Failure tracking and recovery
"""
import time
import random
import logging
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
from threading import Lock
from datetime import datetime, timedelta


class ProxyHealth(Enum):
    """Proxy health states."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CIRCUIT_OPEN = "circuit_open"  # Circuit breaker tripped


@dataclass
class ProxyStats:
    """Statistics for a single proxy."""
    proxy: Dict[str, str]
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    consecutive_failures: int = 0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    last_used: Optional[datetime] = None
    health_score: float = 100.0  # 0-100, higher is better
    health_state: ProxyHealth = ProxyHealth.HEALTHY
    circuit_breaker_open_until: Optional[datetime] = None
    total_latency: float = 0.0
    average_latency: float = 0.0
    
    def update_success(self, latency: float = 0.0):
        """
        Record a successful request and update health metrics.
        
        Resets consecutive failure count and updates success rate.
        
        Args:
            latency: Operation latency in seconds (optional)
        """
        self.total_requests += 1
        self.successful_requests += 1
        self.consecutive_failures = 0
        self.last_success = datetime.utcnow()
        self.last_used = datetime.utcnow()
        
        # Update latency
        if latency > 0:
            self.total_latency += latency
            self.average_latency = self.total_latency / self.successful_requests
        
        # Improve health score
        self.health_score = min(100.0, self.health_score + 2.0)
        
        # Close circuit breaker if it was open
        if self.health_state == ProxyHealth.CIRCUIT_OPEN:
            self.health_state = ProxyHealth.HEALTHY
            self.circuit_breaker_open_until = None
    
    def update_failure(self, error_type: str = "unknown"):
        """
        Record a failed request and update health metrics.
        
        Increments failure counts and may trigger circuit breaker.
        
        Args:
            error_type: Category of error (e.g., 'timeout', '403', 'connection')
        """
        self.total_requests += 1
        self.failed_requests += 1
        self.consecutive_failures += 1
        self.last_failure = datetime.utcnow()
        self.last_used = datetime.utcnow()
        
        # Decrease health score based on failure type
        penalty = 5.0  # Default penalty
        if "timeout" in error_type.lower():
            penalty = 3.0  # Timeouts are less severe
        elif "auth" in error_type.lower():
            penalty = 10.0  # Auth failures are more severe
        
        self.health_score = max(0.0, self.health_score - penalty)
        
        # Update health state based on score
        if self.health_score >= 70:
            self.health_state = ProxyHealth.HEALTHY
        elif self.health_score >= 40:
            self.health_state = ProxyHealth.DEGRADED
        else:
            self.health_state = ProxyHealth.UNHEALTHY
    
    def calculate_success_rate(self) -> float:
        """Calculate success rate (0-1)."""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    def should_use(self, circuit_breaker_threshold: int = 5, 
                   circuit_breaker_timeout: int = 300) -> bool:
        """Check if proxy should be used based on circuit breaker."""
        # Check if circuit breaker is open
        if self.circuit_breaker_open_until:
            if datetime.utcnow() < self.circuit_breaker_open_until:
                return False
            else:
                # Circuit breaker timeout expired, try again
                self.circuit_breaker_open_until = None
                self.health_state = ProxyHealth.UNHEALTHY
        
        # Open circuit breaker if too many consecutive failures
        if self.consecutive_failures >= circuit_breaker_threshold:
            self.health_state = ProxyHealth.CIRCUIT_OPEN
            self.circuit_breaker_open_until = datetime.utcnow() + timedelta(seconds=circuit_breaker_timeout)
            return False
        
        return True


class ProxyPool:
    """
    Proxy pool manager with rotation, health scoring, retry/backoff, and circuit breaker.
    
    Features:
    - Automatic proxy rotation
    - Health scoring based on success/failure rates
    - Exponential backoff on retries
    - Circuit breaker to prevent using failed proxies
    - Thread-safe operations
    """
    
    def __init__(
        self,
        proxies: List[Dict[str, str]],
        rotation_strategy: str = "health_based",  # "round_robin", "health_based", "random"
        circuit_breaker_threshold: int = 5,  # Consecutive failures before opening circuit
        circuit_breaker_timeout: int = 300,  # Seconds before retrying failed proxy
        health_check_enabled: bool = True,
        health_check_interval: int = 60,  # Seconds between health checks
        max_retries: int = 3,
        initial_backoff: float = 1.0,  # Initial backoff in seconds
        max_backoff: float = 60.0,  # Maximum backoff in seconds
        backoff_multiplier: float = 2.0
    ):
        """
        Initialize proxy pool.
        
        Args:
            proxies: List of proxy dictionaries with 'server' key (and optionally 'username', 'password')
            rotation_strategy: Strategy for selecting next proxy
            circuit_breaker_threshold: Consecutive failures before opening circuit
            circuit_breaker_timeout: Seconds before retrying failed proxy
            health_check_enabled: Enable periodic health checks
            health_check_interval: Seconds between health checks
            max_retries: Maximum retries per request
            initial_backoff: Initial backoff delay in seconds
            max_backoff: Maximum backoff delay in seconds
            backoff_multiplier: Multiplier for exponential backoff
        """
        if not proxies:
            raise ValueError("At least one proxy must be provided")
        
        self.proxies = proxies
        self.rotation_strategy = rotation_strategy
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout
        self.health_check_enabled = health_check_enabled
        self.health_check_interval = health_check_interval
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.backoff_multiplier = backoff_multiplier
        
        # Initialize proxy stats
        self.proxy_stats: Dict[str, ProxyStats] = {}
        for proxy in proxies:
            proxy_key = self._get_proxy_key(proxy)
            self.proxy_stats[proxy_key] = ProxyStats(proxy=proxy)
        
        # Thread safety
        self._lock = Lock()
        
        # Rotation state
        self._current_index = 0
        self._last_health_check = datetime.utcnow()
        
        # Logger
        self.logger = logging.getLogger(__name__)
    
    def _get_proxy_key(self, proxy: Dict[str, str]) -> str:
        """Get unique key for proxy."""
        return f"{proxy.get('server', 'unknown')}"
    
    def get_next_proxy(self) -> Optional[Dict[str, str]]:
        """
        Get next proxy based on rotation strategy.
        
        Returns:
            Proxy dictionary or None if no healthy proxies available
        """
        with self._lock:
            available_proxies = self._get_available_proxies()
            
            if not available_proxies:
                self.logger.warning("No healthy proxies available")
                return None
            
            if self.rotation_strategy == "round_robin":
                return self._round_robin_select(available_proxies)
            elif self.rotation_strategy == "health_based":
                return self._health_based_select(available_proxies)
            elif self.rotation_strategy == "random":
                return self._random_select(available_proxies)
            else:
                return self._health_based_select(available_proxies)
    
    def _get_available_proxies(self) -> List[Dict[str, str]]:
        """Get list of available (healthy) proxies."""
        available = []
        for proxy in self.proxies:
            proxy_key = self._get_proxy_key(proxy)
            stats = self.proxy_stats[proxy_key]
            
            if stats.should_use(self.circuit_breaker_threshold, self.circuit_breaker_timeout):
                available.append(proxy)
        
        return available
    
    def _round_robin_select(self, proxies: List[Dict[str, str]]) -> Dict[str, str]:
        """Round-robin proxy selection."""
        if not proxies:
            return None
        
        proxy = proxies[self._current_index % len(proxies)]
        self._current_index += 1
        return proxy
    
    def _health_based_select(self, proxies: List[Dict[str, str]]) -> Dict[str, str]:
        """Select proxy based on health score."""
        if not proxies:
            return None
        
        # Sort by health score (highest first)
        scored_proxies = []
        for proxy in proxies:
            proxy_key = self._get_proxy_key(proxy)
            stats = self.proxy_stats[proxy_key]
            
            # Calculate composite score
            score = stats.health_score
            success_rate = stats.calculate_success_rate()
            
            # Prefer proxies with recent success
            recency_bonus = 0.0
            if stats.last_success:
                seconds_since_success = (datetime.utcnow() - stats.last_success).total_seconds()
                if seconds_since_success < 300:  # Recent success within 5 minutes
                    recency_bonus = 10.0
            
            composite_score = (score * 0.7) + (success_rate * 100 * 0.2) + recency_bonus
            
            scored_proxies.append((composite_score, proxy))
        
        # Sort by score (highest first) and return top proxy
        scored_proxies.sort(key=lambda x: x[0], reverse=True)
        return scored_proxies[0][1]
    
    def _random_select(self, proxies: List[Dict[str, str]]) -> Dict[str, str]:
        """Random proxy selection."""
        if not proxies:
            return None
        return random.choice(proxies)
    
    def mark_success(self, proxy: Dict[str, str], latency: float = 0.0):
        """Mark proxy as successful."""
        with self._lock:
            proxy_key = self._get_proxy_key(proxy)
            if proxy_key in self.proxy_stats:
                self.proxy_stats[proxy_key].update_success(latency)
                self.logger.debug(f"Proxy {proxy_key} marked as successful (health: {self.proxy_stats[proxy_key].health_score:.1f})")
    
    def mark_failure(self, proxy: Dict[str, str], error_type: str = "unknown"):
        """Mark proxy as failed."""
        with self._lock:
            proxy_key = self._get_proxy_key(proxy)
            if proxy_key in self.proxy_stats:
                stats = self.proxy_stats[proxy_key]
                stats.update_failure(error_type)
                
                # Check if circuit breaker should open
                if stats.consecutive_failures >= self.circuit_breaker_threshold:
                    stats.health_state = ProxyHealth.CIRCUIT_OPEN
                    stats.circuit_breaker_open_until = datetime.utcnow() + timedelta(seconds=self.circuit_breaker_timeout)
                    self.logger.warning(
                        f"Circuit breaker opened for proxy {proxy_key} "
                        f"({stats.consecutive_failures} consecutive failures)"
                    )
                else:
                    self.logger.debug(
                        f"Proxy {proxy_key} marked as failed "
                        f"(health: {stats.health_score:.1f}, failures: {stats.consecutive_failures})"
                    )
    
    def execute_with_retry(
        self,
        operation: Callable,
        operation_name: str = "operation",
        *args,
        **kwargs
    ) -> Any:
        """
        Execute operation with proxy rotation and retry logic.
        
        Args:
            operation: Function to execute (should accept proxy as keyword arg)
            operation_name: Name of operation for logging
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation (proxy will be added)
        
        Returns:
            Result of operation
        
        Raises:
            Exception: If all proxies fail after retries
        """
        last_exception = None
        used_proxies = set()
        
        for attempt in range(self.max_retries):
            # Get next proxy
            proxy = self.get_next_proxy()
            
            if not proxy:
                # No healthy proxies available
                if used_proxies:
                    # Reset circuit breakers and try again
                    self.logger.warning("No healthy proxies, resetting circuit breakers and retrying...")
                    self._reset_circuit_breakers()
                    proxy = self.get_next_proxy()
                
                if not proxy:
                    error_msg = "No healthy proxies available after reset"
                    self.logger.error(error_msg)
                    if last_exception:
                        raise Exception(error_msg) from last_exception
                    raise Exception(error_msg)
            
            proxy_key = self._get_proxy_key(proxy)
            used_proxies.add(proxy_key)
            
            # Calculate backoff delay
            if attempt > 0:
                backoff_delay = min(
                    self.initial_backoff * (self.backoff_multiplier ** (attempt - 1)),
                    self.max_backoff
                )
                self.logger.info(f"Waiting {backoff_delay:.1f}s before retry {attempt + 1}/{self.max_retries}...")
                time.sleep(backoff_delay)
            
            try:
                start_time = time.time()
                
                # Execute operation with proxy
                result = operation(*args, proxy=proxy, **kwargs)
                
                # Calculate latency
                latency = time.time() - start_time
                
                # Mark success
                self.mark_success(proxy, latency)
                
                self.logger.info(
                    f"{operation_name} succeeded with proxy {proxy_key} "
                    f"(attempt {attempt + 1}/{self.max_retries}, latency: {latency:.2f}s)"
                )
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Determine error type
                error_type = type(e).__name__
                error_str = str(e).lower()
                if "timeout" in error_str:
                    error_type = "timeout"
                elif "proxy" in error_str or "connection" in error_str:
                    error_type = "connection"
                elif "auth" in error_str:
                    error_type = "authentication"
                
                # Mark failure
                self.mark_failure(proxy, error_type)
                
                self.logger.warning(
                    f"{operation_name} failed with proxy {proxy_key} "
                    f"(attempt {attempt + 1}/{self.max_retries}): {str(e)[:100]}"
                )
                
                # If this was the last attempt, raise exception
                if attempt == self.max_retries - 1:
                    self.logger.error(
                        f"{operation_name} failed after {self.max_retries} attempts with all proxies"
                    )
                    raise
        
        # Should not reach here, but just in case
        if last_exception:
            raise Exception(f"{operation_name} failed after {self.max_retries} attempts") from last_exception
        raise Exception(f"{operation_name} failed after {self.max_retries} attempts")
    
    def _reset_circuit_breakers(self):
        """Reset all circuit breakers (use with caution)."""
        with self._lock:
            for stats in self.proxy_stats.values():
                if stats.health_state == ProxyHealth.CIRCUIT_OPEN:
                    stats.circuit_breaker_open_until = None
                    stats.health_state = ProxyHealth.UNHEALTHY
                    self.logger.info(f"Circuit breaker reset for proxy {self._get_proxy_key(stats.proxy)}")
    
    def get_proxy_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all proxies."""
        with self._lock:
            stats_dict = {}
            for proxy_key, stats in self.proxy_stats.items():
                stats_dict[proxy_key] = {
                    'proxy': stats.proxy,
                    'total_requests': stats.total_requests,
                    'successful_requests': stats.successful_requests,
                    'failed_requests': stats.failed_requests,
                    'consecutive_failures': stats.consecutive_failures,
                    'health_score': round(stats.health_score, 2),
                    'health_state': stats.health_state.value,
                    'success_rate': round(stats.calculate_success_rate() * 100, 2),
                    'average_latency': round(stats.average_latency, 3),
                    'last_success': stats.last_success.isoformat() if stats.last_success else None,
                    'last_failure': stats.last_failure.isoformat() if stats.last_failure else None,
                    'circuit_breaker_open': stats.circuit_breaker_open_until is not None,
                    'circuit_breaker_open_until': stats.circuit_breaker_open_until.isoformat() if stats.circuit_breaker_open_until else None
                }
            return stats_dict
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary of proxy pool."""
        with self._lock:
            total_proxies = len(self.proxy_stats)
            healthy = sum(1 for s in self.proxy_stats.values() if s.health_state == ProxyHealth.HEALTHY)
            degraded = sum(1 for s in self.proxy_stats.values() if s.health_state == ProxyHealth.DEGRADED)
            unhealthy = sum(1 for s in self.proxy_stats.values() if s.health_state == ProxyHealth.UNHEALTHY)
            circuit_open = sum(1 for s in self.proxy_stats.values() if s.health_state == ProxyHealth.CIRCUIT_OPEN)
            
            total_requests = sum(s.total_requests for s in self.proxy_stats.values())
            total_successful = sum(s.successful_requests for s in self.proxy_stats.values())
            total_failed = sum(s.failed_requests for s in self.proxy_stats.values())
            
            overall_success_rate = (total_successful / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'total_proxies': total_proxies,
                'healthy': healthy,
                'degraded': degraded,
                'unhealthy': unhealthy,
                'circuit_open': circuit_open,
                'total_requests': total_requests,
                'total_successful': total_successful,
                'total_failed': total_failed,
                'overall_success_rate': round(overall_success_rate, 2),
                'available_proxies': len(self._get_available_proxies())
            }
    
    def health_check(self, test_url: str = "https://www.google.com", timeout: int = 5) -> Dict[str, bool]:
        """
        Perform health check on all proxies using standard library (no requests dependency).
        
        Args:
            test_url: URL to test proxy connectivity
            timeout: Timeout for health check
        
        Returns:
            Dictionary mapping proxy keys to health check results
        """
        if not self.health_check_enabled:
            return {}
        
        results = {}
        
        import urllib.request
        import urllib.error
        
        for proxy_key, stats in self.proxy_stats.items():
            proxy = stats.proxy
            try:
                # Configure proxy handler
                proxy_url = proxy['server']
                if 'username' in proxy and 'password' in proxy:
                    # Format: http://username:password@server:port
                    if not proxy_url.startswith('http'):
                        proxy_url = f"http://{proxy_url}"
                    # Insert auth
                    scheme, rest = proxy_url.split('://', 1)
                    proxy_url = f"{scheme}://{proxy['username']}:{proxy['password']}@{rest}"
                
                # Create opener with proxy
                proxy_handler = urllib.request.ProxyHandler({
                    'http': proxy_url,
                    'https': proxy_url
                })
                opener = urllib.request.build_opener(proxy_handler)
                
                # Make request
                with opener.open(test_url, timeout=timeout) as response:
                    results[proxy_key] = response.status == 200
                
                if results[proxy_key]:
                    self.mark_success(proxy)
                else:
                    self.mark_failure(proxy, "health_check_failed")
                    
            except Exception as e:
                results[proxy_key] = False
                self.mark_failure(proxy, f"health_check_{type(e).__name__}")
        
        return results

