import itertools
from typing import List, Optional
from .logger import logger

class ProxyRotator:
    """
    Rotates through a list of proxies in a round-robin fashion with strict enforcement.
    """
    def __init__(self, proxies: List[str], strict_mode: bool = False):
        """
        Initialize the rotator with a list of proxies.
        
        Args:
            proxies: List of proxy strings.
            strict_mode: If True, raises exception when no proxies are available.
        """
        self.proxies = [p.strip() for p in proxies if p.strip()]
        self.strict_mode = strict_mode
        self._cycle = itertools.cycle(self.proxies) if self.proxies else None
        
        # Strict mode validation
        if self.strict_mode and not self.proxies:
            error_msg = (
                "PROXY ENFORCEMENT FAILURE: No proxies available in strict mode. "
                "Scraper cannot run without proxies. Please configure PROXY_LIST in .env file."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        if self.proxies:
            logger.info(f"ProxyRotator initialized with {len(self.proxies)} proxies (strict_mode={strict_mode})")
            logger.info(f"Proxy list: {', '.join(self.proxies)}")
        else:
            logger.warning("ProxyRotator initialized with NO proxies (strict_mode=False)")

    def get_next(self) -> Optional[str]:
        """
        Get the next proxy in the cycle.
        
        Returns:
            The next proxy string or None if no proxies are available.
            
        Raises:
            RuntimeError: If strict_mode is enabled and no proxies are available.
        """
        if not self._cycle:
            if self.strict_mode:
                error_msg = "PROXY ENFORCEMENT FAILURE: No proxies available for rotation."
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            logger.warning("No proxies available, returning None")
            return None
            
        proxy = next(self._cycle)
        logger.info(f"Rotating to proxy: {proxy}")
        return proxy

    def get_all(self) -> List[str]:
        """Get all available proxies."""
        return self.proxies
    
    def has_proxies(self) -> bool:
        """Check if any proxies are available."""
        return len(self.proxies) > 0

# Global rotator instance (can be initialized with config)
_rotator = None

def init_rotator(proxy_list_str: str, strict_mode: bool = False):
    """
    Initialize the global proxy rotator.
    
    Args:
        proxy_list_str: Comma-separated list of proxies.
        strict_mode: If True, enforces proxy usage (no bypass allowed).
        
    Raises:
        ValueError: If strict_mode is True and no proxies are provided.
    """
    global _rotator
    proxies = []
    if proxy_list_str:
        proxies = [p.strip() for p in proxy_list_str.split(",") if p.strip()]
    
    _rotator = ProxyRotator(proxies, strict_mode=strict_mode)
    
    if strict_mode and not proxies:
        # This will raise ValueError from ProxyRotator.__init__
        pass
    elif not proxies:
        logger.warning("ProxyRotator initialized without proxies (strict_mode=False)")

def get_proxy() -> Optional[str]:
    """
    Get a proxy from the global rotator.
    
    Returns:
        The next proxy string or None.
        
    Raises:
        RuntimeError: If strict mode is enabled and no proxies are available.
    """
    if _rotator:
        return _rotator.get_next()
    return None

def has_proxies() -> bool:
    """
    Check if the global rotator has any proxies available.
    
    Returns:
        True if proxies are available, False otherwise.
    """
    if _rotator:
        return _rotator.has_proxies()
    return False
