"""
Proxy Management module for LinkedIn Scraper
Manages rotating proxies with failure tracking
"""

import os
import random
from typing import Dict, Optional
from logger import logger

class ProxyRotator:
    """Manages rotating proxies for requests with failure tracking"""
    
    def __init__(self, proxy_file: str = "proxies.txt"):
        """
        Initialize proxy rotator
        
        Args:
            proxy_file: Path to file containing proxies (one per line)
                       Format: host:port or host:port:username:password
        """
        self.proxy_file = proxy_file
        self.proxies = []
        self.failed_proxies = set()
        self.current_proxy_index = 0
        self.proxies_loaded = False
        self.proxy = True # Enabled by default
        self.load_proxies()
    
    def load_proxies(self):
        """Load proxies from file"""
        if os.path.exists(self.proxy_file):
            try:
                with open(self.proxy_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            self.proxies.append(line)
                if self.proxies:
                    self.proxies_loaded = True
                    logger.info(f"Loaded {len(self.proxies)} proxies from {self.proxy_file}")
                else:
                    logger.warning(f"Proxy file '{self.proxy_file}' is empty. No proxies loaded.")
            except Exception as e:
                logger.error(f"Error loading proxy file: {e}")
        else:
            logger.warning(f"Proxy file '{self.proxy_file}' not found. No proxies loaded.", 
                           context={"hint": "Create file with host:port format to enable rotation"})
            self.proxy = False
            
    def mark_proxy_failed(self, proxy_server: str):
        """Mark a proxy as failed so it's skipped in rotation"""
        self.failed_proxies.add(proxy_server)
        logger.warning(f"Marked proxy as failed: {proxy_server}", context={"failed_count": len(self.failed_proxies)})
        
        # If all proxies failed, reset to try again
        if len(self.failed_proxies) >= len(self.proxies) and len(self.proxies) > 0:
            logger.warning("All proxies marked as failed. Resetting failure list.")
            self.failed_proxies.clear()

    def get_proxy_config(self) -> Optional[Dict]:
        """
        Get next working proxy configuration for Playwright
        """
        if not self.proxies:
            return None
        
        attempts = 0
        while attempts < len(self.proxies):
            proxy_str = self.proxies[self.current_proxy_index]
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
            
            # Helper to format proxy config
            config = self._parse_proxy(proxy_str)
            if not config:
                attempts += 1
                continue

            server = config["server"]
            
            # Skip if marked as failed
            if server in self.failed_proxies:
                attempts += 1
                continue
                
            return config
            
        # If we get here, all proxies might be failed or invalid. 
        # Just return the next one and hope for the best (or the reset logic above handles it next time)
        return self._parse_proxy(self.proxies[0]) if self.proxies else None

    def _parse_proxy(self, proxy_str: str) -> Optional[Dict]:
        parts = proxy_str.split(':')
        if len(parts) == 2:
            return {"server": f"http://{proxy_str}"}
        elif len(parts) == 4:
            return {
                "server": f"http://{parts[0]}:{parts[1]}",
                "username": parts[2],
                "password": parts[3]
            }
        else:
            logger.warning(f"Invalid proxy format: {proxy_str}")
            return None
    
    def get_random_proxy(self) -> Optional[Dict]:
        """Get a random working proxy"""
        if not self.proxies:
            return None
        
        # Try a few times to get a non-failed proxy
        for _ in range(10):
            proxy_str = random.choice(self.proxies)
            config = self._parse_proxy(proxy_str)
            if config:
                server = config["server"]
                if server not in self.failed_proxies:
                    return config
        
        return None
