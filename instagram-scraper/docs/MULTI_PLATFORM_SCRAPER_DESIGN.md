# Multi-Platform Scraper System Design

## Overview

A unified scraping system for TikTok, Instagram, X (Twitter), LinkedIn, and Facebook that collects trending content using Playwright with rotating proxies, while maintaining strict compliance with public-only data collection.

## ⚠️ CRITICAL COMPLIANCE REQUIREMENTS

### Public-Only Scraping Policy

**MUST FOLLOW:**
- ✅ **NO LOGIN REQUIRED** - Only access public pages/content
- ✅ **NO PII COLLECTION** - No personal identifiable information
- ✅ **NO PRIVATE DATA** - Only public posts, hashtags, trending topics
- ✅ **RESPECT robots.txt** - Check and honor robots.txt files
- ✅ **RATE LIMITING** - Implement delays between requests
- ✅ **USER AGENT** - Use appropriate user agents
- ✅ **TERMS OF SERVICE** - Review and comply with each platform's ToS

### Legal Considerations

- **Instagram**: Public posts only, no private accounts
- **TikTok**: Public videos only, no user profiles
- **X (Twitter)**: Public tweets only, no DMs or private accounts
- **LinkedIn**: Public posts only (very limited without auth)
- **Facebook**: Public pages/posts only, no personal profiles

**Note**: Some platforms (LinkedIn, Facebook) have very limited public content without authentication. Consider focusing on platforms with better public API access.

## Architecture Design

### System Components

```
┌─────────────────────────────────────────────────────────┐
│              Multi-Platform Scraper System              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Platform   │  │   Platform   │  │   Platform   │ │
│  │   Adapters   │  │   Adapters   │  │   Adapters   │ │
│  │              │  │              │  │              │ │
│  │ Instagram    │  │   TikTok     │  │      X       │ │
│  │  LinkedIn    │  │  Facebook    │  │              │ │
│  └──────┬───────┘  └──────┬──────┘  └──────┬───────┘ │
│         │                  │                  │         │
│         └──────────────────┼──────────────────┘         │
│                            │                            │
│  ┌─────────────────────────▼─────────────────────────┐ │
│  │         Unified Scraper Interface                  │ │
│  │  - Common data models                              │ │
│  │  - Error handling                                  │ │
│  │  - Retry logic                                     │ │
│  └─────────────────────────┬─────────────────────────┘ │
│                            │                            │
│  ┌─────────────────────────▼─────────────────────────┐ │
│  │         Proxy Pool Manager                         │ │
│  │  - Health checking                                 │ │
│  │  - Rotation logic                                  │ │
│  │  - Failure handling                                │ │
│  └─────────────────────────┬─────────────────────────┘ │
│                            │                            │
│  ┌─────────────────────────▼─────────────────────────┐ │
│  │         Playwright Browser Manager                 │ │
│  │  - Context creation with proxy                     │ │
│  │  - Session management                              │ │
│  └─────────────────────────┬─────────────────────────┘ │
│                            │                            │
│  ┌─────────────────────────▼─────────────────────────┐ │
│  │         Data Storage                               │ │
│  │  - Normalized schema                               │ │
│  │  - Platform-agnostic format                        │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Implementation Strategy

### 1. Platform Adapter Pattern

Each platform gets its own adapter implementing a common interface:

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class PlatformAdapter(ABC):
    """Base class for platform-specific scrapers."""
    
    @abstractmethod
    def get_trending_hashtags(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get trending hashtags/topics."""
        pass
    
    @abstractmethod
    def get_trending_posts(self, hashtag: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get trending posts for a hashtag."""
        pass
    
    @abstractmethod
    def normalize_data(self, raw_data: Dict) -> Dict[str, Any]:
        """Normalize platform-specific data to common format."""
        pass
```

### 2. Unified Data Model

All platforms output to the same schema:

```python
@dataclass
class TrendRecord:
    platform: str  # "instagram", "tiktok", "x", "linkedin", "facebook"
    content_id: str  # Platform-specific ID
    content_type: str  # "post", "video", "tweet", "reel"
    hashtag: str
    url: str
    engagement_score: float
    likes: int
    comments: int
    shares: int
    views: int
    timestamp: datetime
    language: str  # ISO 639-1
    sentiment: Dict[str, Any]
    metadata: Dict[str, Any]  # Platform-specific data
```

### 3. Proxy Pool Manager

```python
class ProxyPool:
    """Manages rotating proxy pool with health checking."""
    
    def __init__(self, proxies: List[Dict[str, str]]):
        self.proxies = proxies
        self.health_scores = {}  # Track proxy health
        self.failure_counts = {}  # Track failures
    
    def get_next_proxy(self) -> Dict[str, str]:
        """Get next healthy proxy based on rotation strategy."""
        # Sort by health score, return best available
        pass
    
    def mark_success(self, proxy: Dict[str, str]):
        """Mark proxy as successful."""
        pass
    
    def mark_failure(self, proxy: Dict[str, str]):
        """Mark proxy as failed, reduce health score."""
        pass
    
    def health_check(self, proxy: Dict[str, str]) -> bool:
        """Check if proxy is healthy."""
        pass
```

## Platform-Specific Implementation

### Instagram (Already Implemented)

**Public Access:**
- ✅ `/explore/` - Trending hashtags
- ✅ `/explore/tags/{hashtag}/` - Posts for hashtag
- ✅ `/p/{post_id}/` - Individual public posts
- ✅ `/reel/{reel_id}/` - Public reels

**No Login Required:**
- Explore page is accessible without login
- Public posts are viewable
- Engagement metrics visible

**Implementation:**
```python
class InstagramAdapter(PlatformAdapter):
    def get_trending_hashtags(self, limit: int = 10):
        # Navigate to /explore/
        # Extract trending hashtags
        # Return normalized data
        pass
```

### TikTok

**Public Access:**
- ✅ `/foryou` - Trending videos (may require some interaction)
- ✅ `/tag/{hashtag}` - Videos with hashtag
- ✅ `/@{username}/video/{id}` - Individual videos

**Challenges:**
- Heavy JavaScript rendering
- Anti-bot measures
- May need to handle CAPTCHAs

**Implementation:**
```python
class TikTokAdapter(PlatformAdapter):
    def get_trending_hashtags(self, limit: int = 10):
        # Navigate to /foryou or trending page
        # Extract trending hashtags from video descriptions
        # Return normalized data
        pass
    
    def get_trending_posts(self, hashtag: str, limit: int = 10):
        # Navigate to /tag/{hashtag}
        # Extract video data
        # Return normalized data
        pass
```

### X (Twitter)

**Public Access:**
- ✅ `/explore` - Trending topics
- ✅ `/hashtag/{hashtag}` - Tweets with hashtag
- ✅ `/i/web/status/{tweet_id}` - Individual tweets

**Challenges:**
- Rate limiting is strict
- Requires careful request spacing
- May show limited content without login

**Implementation:**
```python
class TwitterAdapter(PlatformAdapter):
    def get_trending_hashtags(self, limit: int = 10):
        # Navigate to /explore
        # Extract trending topics
        # Return normalized data
        pass
```

### LinkedIn

**⚠️ LIMITED PUBLIC ACCESS**

**Public Access:**
- ⚠️ Very limited without authentication
- ✅ Public company pages
- ✅ Public posts (if shared publicly)
- ❌ Most content requires login

**Recommendation:**
- Consider skipping LinkedIn or using official API
- Focus on public company page posts only

**Implementation:**
```python
class LinkedInAdapter(PlatformAdapter):
    def get_trending_hashtags(self, limit: int = 10):
        # Limited - only public company posts
        # May need to focus on specific public pages
        pass
```

### Facebook

**⚠️ LIMITED PUBLIC ACCESS**

**Public Access:**
- ✅ Public pages (businesses, brands)
- ✅ Public posts on pages
- ❌ Personal profiles require login
- ❌ Most groups require login

**Recommendation:**
- Focus on public pages only
- Use page-specific URLs
- Avoid personal content

**Implementation:**
```python
class FacebookAdapter(PlatformAdapter):
    def get_trending_hashtags(self, limit: int = 10):
        # Navigate to public pages
        # Extract hashtags from public posts
        # Return normalized data
        pass
```

## Proxy Rotation Strategy

### 1. Round-Robin Rotation

```python
class RoundRobinProxyPool(ProxyPool):
    def __init__(self, proxies: List[Dict[str, str]]):
        super().__init__(proxies)
        self.current_index = 0
    
    def get_next_proxy(self) -> Dict[str, str]:
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy
```

### 2. Health-Based Rotation

```python
class HealthBasedProxyPool(ProxyPool):
    def get_next_proxy(self) -> Dict[str, str]:
        # Sort by health score (highest first)
        sorted_proxies = sorted(
            self.proxies,
            key=lambda p: self.health_scores.get(str(p), 100),
            reverse=True
        )
        return sorted_proxies[0]
```

### 3. Failure-Aware Rotation

```python
class FailureAwareProxyPool(ProxyPool):
    MAX_FAILURES = 3
    
    def get_next_proxy(self) -> Dict[str, str]:
        # Filter out proxies with too many failures
        healthy_proxies = [
            p for p in self.proxies
            if self.failure_counts.get(str(p), 0) < self.MAX_FAILURES
        ]
        
        if not healthy_proxies:
            # Reset failure counts if all proxies failed
            self.failure_counts.clear()
            healthy_proxies = self.proxies
        
        return healthy_proxies[0]
```

## Implementation Steps

### Step 1: Create Base Adapter Interface

```python
# adapters/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class PlatformAdapter(ABC):
    def __init__(self, page, proxy_config: Dict[str, str] = None):
        self.page = page
        self.proxy_config = proxy_config
        self.platform_name = self.__class__.__name__.replace('Adapter', '').lower()
    
    @abstractmethod
    def get_trending_hashtags(self, limit: int = 10) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def get_trending_posts(self, hashtag: str, limit: int = 10) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def normalize_data(self, raw_data: Dict) -> TrendRecord:
        """Convert platform-specific data to TrendRecord."""
        pass
```

### Step 2: Implement Platform Adapters

```python
# adapters/instagram_adapter.py
class InstagramAdapter(PlatformAdapter):
    def get_trending_hashtags(self, limit: int = 10):
        # Use existing Instagram scraping logic
        # But ensure NO LOGIN
        pass

# adapters/tiktok_adapter.py
class TikTokAdapter(PlatformAdapter):
    def get_trending_hashtags(self, limit: int = 10):
        # Navigate to TikTok trending
        # Extract hashtags
        pass

# adapters/twitter_adapter.py
class TwitterAdapter(PlatformAdapter):
    def get_trending_hashtags(self, limit: int = 10):
        # Navigate to Twitter explore
        # Extract trending topics
        pass
```

### Step 3: Create Proxy Pool Manager

```python
# proxy_pool.py
class ProxyPoolManager:
    def __init__(self, proxies: List[Dict[str, str]]):
        self.proxies = proxies
        self.health_scores = {str(p): 100 for p in proxies}
        self.failure_counts = {str(p): 0 for p in proxies}
        self.current_index = 0
    
    def get_next_proxy(self) -> Dict[str, str]:
        """Get next proxy with health-based rotation."""
        # Implementation here
        pass
    
    def mark_success(self, proxy: Dict[str, str]):
        """Increase health score on success."""
        key = str(proxy)
        self.health_scores[key] = min(100, self.health_scores.get(key, 50) + 5)
        self.failure_counts[key] = 0
    
    def mark_failure(self, proxy: Dict[str, str]):
        """Decrease health score on failure."""
        key = str(proxy)
        self.health_scores[key] = max(0, self.health_scores.get(key, 100) - 10)
        self.failure_counts[key] = self.failure_counts.get(key, 0) + 1
```

### Step 4: Unified Scraper Orchestrator

```python
# multi_platform_scraper.py
class MultiPlatformScraper:
    def __init__(self, proxy_pool: ProxyPoolManager):
        self.proxy_pool = proxy_pool
        self.adapters = {
            'instagram': InstagramAdapter,
            'tiktok': TikTokAdapter,
            'twitter': TwitterAdapter,
            # Add more as needed
        }
    
    async def scrape_platform(self, platform: str, limit: int = 10):
        """Scrape a single platform."""
        proxy = self.proxy_pool.get_next_proxy()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                proxy={'server': proxy['server']}
            )
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                adapter = self.adapters[platform](page, proxy)
                trends = adapter.get_trending_hashtags(limit)
                self.proxy_pool.mark_success(proxy)
                return trends
            except Exception as e:
                self.proxy_pool.mark_failure(proxy)
                raise
            finally:
                await browser.close()
    
    async def scrape_all_platforms(self, limit: int = 10):
        """Scrape all platforms in parallel."""
        tasks = [
            self.scrape_platform(platform, limit)
            for platform in self.adapters.keys()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
```

## Compliance Checklist

### ✅ Public-Only Requirements

- [ ] **No authentication** - Never log in to any platform
- [ ] **No private data** - Only access public pages/posts
- [ ] **No PII collection** - Don't collect usernames, emails, phone numbers
- [ ] **Respect robots.txt** - Check and honor robots.txt
- [ ] **Rate limiting** - Implement delays between requests
- [ ] **User agent** - Use appropriate, identifiable user agents
- [ ] **Terms of Service** - Review and comply with each platform's ToS

### ✅ Data Collection Limits

- [ ] Only collect publicly visible content
- [ ] No user profile data
- [ ] No private messages
- [ ] No friend/connection lists
- [ ] Only aggregate engagement metrics (likes, shares, views)

### ✅ Legal Considerations

- [ ] Review each platform's Terms of Service
- [ ] Check data protection regulations (GDPR, CCPA)
- [ ] Implement data retention policies
- [ ] Provide opt-out mechanisms if required
- [ ] Document data sources and collection methods

## Recommended Implementation Order

1. **Phase 1: Instagram** (Already done - refactor to adapter pattern)
   - ✅ Public explore page
   - ✅ Public posts
   - ✅ No login required

2. **Phase 2: TikTok**
   - Public trending page
   - Public videos
   - Hashtag pages

3. **Phase 3: X (Twitter)**
   - Public explore page
   - Public tweets
   - Rate limiting

4. **Phase 4: Proxy Rotation**
   - Implement proxy pool
   - Health checking
   - Rotation logic

5. **Phase 5: LinkedIn/Facebook** (Optional - limited value)
   - Only if public content is sufficient
   - Consider official APIs instead

## Code Structure

```
multi_platform_scraper/
├── adapters/
│   ├── __init__.py
│   ├── base.py              # Base adapter interface
│   ├── instagram_adapter.py
│   ├── tiktok_adapter.py
│   ├── twitter_adapter.py
│   ├── linkedin_adapter.py
│   └── facebook_adapter.py
├── proxy_pool.py            # Proxy rotation manager
├── models.py                # Unified data models
├── multi_platform_scraper.py  # Main orchestrator
├── compliance.py            # Compliance checks
└── config.py                # Configuration
```

## Configuration Example

```python
# config.py
PLATFORMS = {
    'instagram': {
        'enabled': True,
        'base_url': 'https://www.instagram.com',
        'trending_url': '/explore/',
        'rate_limit_delay': 2.0
    },
    'tiktok': {
        'enabled': True,
        'base_url': 'https://www.tiktok.com',
        'trending_url': '/foryou',
        'rate_limit_delay': 3.0
    },
    'twitter': {
        'enabled': True,
        'base_url': 'https://twitter.com',
        'trending_url': '/explore',
        'rate_limit_delay': 5.0  # More conservative
    }
}

PROXIES = [
    {'server': 'http://proxy1.example.com:8080'},
    {'server': 'http://proxy2.example.com:8080'},
    # Add more proxies
]

COMPLIANCE = {
    'public_only': True,
    'no_login': True,
    'no_pii': True,
    'respect_robots_txt': True,
    'rate_limiting': True
}
```

## Next Steps

1. **Refactor existing Instagram scraper** to adapter pattern
2. **Implement proxy pool manager** with health checking
3. **Create base adapter interface** for consistency
4. **Implement TikTok adapter** (highest value after Instagram)
5. **Implement Twitter adapter** (good public access)
6. **Add compliance checks** at each step
7. **Test with multiple proxies** to ensure rotation works
8. **Document compliance** for each platform

## Important Notes

⚠️ **LinkedIn and Facebook have very limited public content without authentication. Consider:**
- Using official APIs where available
- Focusing on platforms with better public access (Instagram, TikTok, Twitter)
- Skipping platforms that require login for meaningful data

⚠️ **Rate Limiting:**
- Each platform has different rate limits
- Implement platform-specific delays
- Monitor for rate limit errors
- Implement exponential backoff

⚠️ **Legal Compliance:**
- Review Terms of Service for each platform
- Check data protection regulations
- Consider consulting legal counsel
- Document all data collection methods

