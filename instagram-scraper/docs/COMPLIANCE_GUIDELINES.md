# Compliance Guidelines for Multi-Platform Scraper

## ⚠️ CRITICAL: Public-Only Scraping Policy

This scraper system **MUST** operate under strict public-only data collection policies to ensure legal compliance and ethical data usage.

## Core Principles

### 1. NO AUTHENTICATION REQUIRED

**Rule**: Never log in to any platform.

**Rationale**: 
- Login creates a user relationship that may have different legal implications
- Private data becomes accessible after login
- Terms of Service may have different restrictions for authenticated users

**Implementation**:
```python
# ✅ CORRECT - No login
page.goto("https://www.instagram.com/explore/")

# ❌ WRONG - Never do this
page.goto("https://www.instagram.com/accounts/login/")
# ... login code ...
```

### 2. NO PERSONAL IDENTIFIABLE INFORMATION (PII)

**Rule**: Do not collect any PII.

**What is PII:**
- Usernames (unless they're part of public content)
- Email addresses
- Phone numbers
- Real names
- Location data (unless it's public content metadata)
- Profile pictures
- Friend/connection lists

**What is OK to collect:**
- Public post content
- Public engagement metrics (likes, shares, views)
- Public hashtags
- Public trending topics
- Aggregated statistics

**Implementation**:
```python
# ✅ CORRECT - Only public content
data = {
    'hashtag': '#trending',
    'likes': 1000,
    'comments': 50,
    'content': 'Public post text'
}

# ❌ WRONG - Contains PII
data = {
    'username': '@user123',  # PII
    'email': 'user@example.com',  # PII
    'real_name': 'John Doe',  # PII
    'location': '123 Main St, City'  # PII
}
```

### 3. PUBLIC CONTENT ONLY

**Rule**: Only access content that is publicly visible without authentication.

**Allowed:**
- Public posts on Instagram
- Public videos on TikTok
- Public tweets on Twitter
- Public pages on Facebook/LinkedIn
- Trending topics/hashtags

**Not Allowed:**
- Private accounts
- Private messages
- Friend-only content
- Group content (unless public)
- Profile information (unless public)

### 4. RESPECT robots.txt

**Rule**: Check and honor robots.txt files for each platform.

**Implementation**:
```python
import urllib.robotparser

def check_robots_txt(url: str, user_agent: str = 'MyBot/1.0') -> bool:
    """Check if URL is allowed by robots.txt."""
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(f"{url}/robots.txt")
    rp.read()
    return rp.can_fetch(user_agent, url)
```

### 5. RATE LIMITING

**Rule**: Implement appropriate delays between requests.

**Platform-Specific Recommendations:**
- Instagram: 2-3 seconds between requests
- TikTok: 3-5 seconds between requests
- Twitter: 5-10 seconds between requests (strict rate limits)
- LinkedIn: 10+ seconds (very conservative)
- Facebook: 5-10 seconds

**Implementation**:
```python
import time
import random

def rate_limit_delay(platform: str):
    """Apply platform-specific rate limiting."""
    delays = {
        'instagram': (2, 3),
        'tiktok': (3, 5),
        'twitter': (5, 10),
        'linkedin': (10, 15),
        'facebook': (5, 10)
    }
    min_delay, max_delay = delays.get(platform, (3, 5))
    time.sleep(random.uniform(min_delay, max_delay))
```

### 6. APPROPRIATE USER AGENT

**Rule**: Use identifiable, appropriate user agents.

**Implementation**:
```python
USER_AGENTS = {
    'instagram': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'tiktok': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'twitter': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
}

context = await browser.new_context(
    user_agent=USER_AGENTS[platform]
)
```

## Platform-Specific Compliance

### Instagram

**Public Access:**
- ✅ `/explore/` - Trending hashtags (no login)
- ✅ `/explore/tags/{hashtag}/` - Public posts (no login)
- ✅ `/p/{post_id}/` - Public posts (no login)
- ✅ `/reel/{reel_id}/` - Public reels (no login)

**Compliance Notes:**
- Do not access private accounts
- Do not collect user profile data
- Only collect public engagement metrics
- Respect rate limits (Instagram is strict)

**Terms of Service:**
- Review Instagram's ToS regularly
- Instagram prohibits automated data collection without permission
- Consider using Instagram Basic Display API for official access

### TikTok

**Public Access:**
- ✅ `/foryou` - Trending videos (may be limited)
- ✅ `/tag/{hashtag}` - Videos with hashtag
- ✅ Individual video pages

**Compliance Notes:**
- Heavy anti-bot measures
- May encounter CAPTCHAs
- Rate limiting is aggressive
- Consider official TikTok API if available

**Terms of Service:**
- TikTok has strict ToS regarding scraping
- Review TikTok's Terms of Service
- Consider official API access

### X (Twitter)

**Public Access:**
- ✅ `/explore` - Trending topics
- ✅ `/hashtag/{hashtag}` - Public tweets
- ✅ Individual tweet pages

**Compliance Notes:**
- Very strict rate limiting
- Requires careful request spacing
- Consider Twitter API v2 for official access
- Public content is limited without authentication

**Terms of Service:**
- Twitter's ToS allows some automated access
- Review Twitter's Developer Terms
- Consider using Twitter API for compliance

### LinkedIn

**⚠️ LIMITED PUBLIC ACCESS**

**Public Access:**
- ⚠️ Very limited without authentication
- ✅ Public company pages
- ✅ Public posts (if shared publicly)

**Compliance Notes:**
- Most content requires login
- LinkedIn strongly discourages scraping
- Consider LinkedIn API for official access
- May want to skip this platform

**Terms of Service:**
- LinkedIn's ToS prohibits scraping
- Strongly recommend using official API
- Or skip this platform entirely

### Facebook

**⚠️ LIMITED PUBLIC ACCESS**

**Public Access:**
- ✅ Public pages (businesses, brands)
- ✅ Public posts on pages
- ❌ Personal profiles require login

**Compliance Notes:**
- Focus only on public pages
- Do not access personal profiles
- Facebook has strict anti-scraping measures
- Consider Facebook Graph API for official access

**Terms of Service:**
- Facebook's ToS prohibits scraping
- Strongly recommend using official API
- Or focus only on public pages with permission

## Data Collection Limits

### ✅ What You CAN Collect

- Public post/video content
- Public engagement metrics (likes, shares, views, comments)
- Public hashtags
- Public trending topics
- Aggregated statistics
- Public metadata (timestamps, content type)

### ❌ What You CANNOT Collect

- User profile information
- Email addresses
- Phone numbers
- Real names
- Private messages
- Friend/connection lists
- Location data (unless it's public content metadata)
- Any data from private accounts

## Legal Considerations

### 1. Terms of Service

**Action Required:**
- Review each platform's Terms of Service
- Document compliance measures
- Update compliance checks regularly

**Key Points:**
- Instagram: Prohibits automated collection
- TikTok: Strict anti-scraping policies
- Twitter: Allows some automated access (check Developer Terms)
- LinkedIn: Prohibits scraping
- Facebook: Prohibits scraping

### 2. Data Protection Regulations

**GDPR (EU):**
- Only collect data you have legal basis for
- Implement data retention policies
- Provide data deletion mechanisms
- Document data processing activities

**CCPA (California):**
- Disclose data collection practices
- Provide opt-out mechanisms
- Honor deletion requests

**Implementation:**
```python
# Data retention policy
DATA_RETENTION_DAYS = 30  # Keep data for 30 days only

# Opt-out mechanism
def delete_user_data(user_id: str):
    """Delete all data for a user (if required)."""
    # Implementation
    pass
```

### 3. Copyright Considerations

**Rule**: Respect content creators' rights.

**Guidelines:**
- Only collect metadata, not full content reproduction
- Attribute content to original creators when possible
- Do not republish content without permission
- Use data for analysis/trending purposes only

## Implementation Checklist

### Pre-Implementation

- [ ] Review each platform's Terms of Service
- [ ] Check robots.txt for each platform
- [ ] Document data collection methods
- [ ] Implement rate limiting
- [ ] Set up appropriate user agents
- [ ] Create compliance monitoring

### During Implementation

- [ ] Never implement login functionality
- [ ] Only access public URLs
- [ ] Filter out any PII
- [ ] Implement rate limiting
- [ ] Add compliance checks
- [ ] Log all data collection activities

### Post-Implementation

- [ ] Regular ToS review
- [ ] Monitor for rate limit errors
- [ ] Audit data collection
- [ ] Update compliance measures
- [ ] Document any changes

## Monitoring and Auditing

### Compliance Monitoring

```python
class ComplianceMonitor:
    def check_public_only(self, url: str) -> bool:
        """Verify URL is public-only."""
        private_indicators = [
            '/accounts/login',
            '/messages',
            '/inbox',
            '/profile',
            '/settings'
        ]
        return not any(indicator in url for indicator in private_indicators)
    
    def check_no_pii(self, data: Dict) -> bool:
        """Verify data contains no PII."""
        pii_fields = ['email', 'phone', 'real_name', 'address']
        return not any(field in data for field in pii_fields)
    
    def audit_collection(self, platform: str, data: Dict):
        """Audit data collection for compliance."""
        if not self.check_public_only(data.get('url', '')):
            raise ComplianceError("Attempted to collect private data")
        if not self.check_no_pii(data):
            raise ComplianceError("Attempted to collect PII")
```

## Recommendations

### 1. Use Official APIs When Available

**Priority Order:**
1. **Twitter API v2** - Good public access, compliant
2. **Instagram Basic Display API** - Official access
3. **TikTok API** - If available
4. **Facebook Graph API** - For public pages
5. **LinkedIn API** - For official access

### 2. Focus on High-Value Platforms

**Recommended Focus:**
1. **Instagram** - Good public access, already implemented
2. **TikTok** - Good public content
3. **Twitter** - Good public access with API
4. **Skip LinkedIn** - Limited public content, ToS issues
5. **Skip Facebook** - Limited public content, ToS issues

### 3. Implement Compliance Checks

- Add compliance checks at every data collection point
- Log all compliance violations
- Alert on potential issues
- Regular compliance audits

## Conclusion

**Key Takeaways:**
1. ✅ **Public-only** - Never log in
2. ✅ **No PII** - Don't collect personal information
3. ✅ **Respect ToS** - Review and comply with Terms of Service
4. ✅ **Rate limiting** - Implement appropriate delays
5. ✅ **Use APIs** - Prefer official APIs when available
6. ✅ **Document** - Document all compliance measures
7. ✅ **Monitor** - Regularly audit compliance

**Remember**: When in doubt, err on the side of caution. It's better to collect less data legally than to risk legal issues.

