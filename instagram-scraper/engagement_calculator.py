"""
Engagement Score Calculator

Computes weighted engagement scores based on platform-specific metrics:
- Likes, Comments, Shares, Views
- Platform-specific weights
- Normalization by audience size
- Time decay factors
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EngagementWeights:
    """Platform-specific engagement weights."""
    likes_weight: float = 1.0
    comments_weight: float = 2.0  # Comments are more valuable
    shares_weight: float = 3.0    # Shares are most valuable
    views_weight: float = 0.1     # Views are less valuable (passive)
    
    def __post_init__(self):
        """
        Validate that all engagement weights are non-negative.
        
        Raises:
            AssertionError: If any weight is less than zero.
        """
        assert self.likes_weight >= 0, "likes_weight must be non-negative"
        assert self.comments_weight >= 0, "comments_weight must be non-negative"
        assert self.shares_weight >= 0, "shares_weight must be non-negative"
        assert self.views_weight >= 0, "views_weight must be non-negative"


# Platform-specific engagement weight configurations
PLATFORM_WEIGHTS = {
    'Instagram': EngagementWeights(
        likes_weight=1.0,
        comments_weight=2.5,  # Comments are highly valued on Instagram
        shares_weight=3.5,    # Shares (saves/reposts) are very valuable
        views_weight=0.05     # Views are less important (stories/reels)
    ),
    'TikTok': EngagementWeights(
        likes_weight=1.0,
        comments_weight=2.0,
        shares_weight=4.0,    # Shares are extremely valuable on TikTok
        views_weight=0.15     # Views are more important on TikTok
    ),
    'Twitter': EngagementWeights(
        likes_weight=1.0,
        comments_weight=3.0,   # Replies are very valuable
        shares_weight=4.0,    # Retweets are most valuable
        views_weight=0.02     # Views are least important
    ),
    'Facebook': EngagementWeights(
        likes_weight=1.0,
        comments_weight=2.0,
        shares_weight=3.0,
        views_weight=0.1
    ),
    'LinkedIn': EngagementWeights(
        likes_weight=1.0,
        comments_weight=3.5,  # Comments are highly valued on LinkedIn
        shares_weight=4.0,    # Shares are very valuable
        views_weight=0.05
    ),
    'YouTube': EngagementWeights(
        likes_weight=1.0,
        comments_weight=2.5,
        shares_weight=3.0,
        views_weight=0.5      # Views are more important on YouTube
    ),
    'default': EngagementWeights()  # Default weights
}


class EngagementCalculator:
    """
    Calculates weighted engagement scores based on platform-specific metrics.
    
    Formula:
    engagement_score = (likes * likes_weight) + 
                       (comments * comments_weight) + 
                       (shares * shares_weight) + 
                       (views * views_weight)
    
    With optional normalization by audience size and time decay.
    """
    
    def __init__(self, platform: str = 'Instagram'):
        """
        Initialize calculator with platform-specific weights.
        
        Args:
            platform: Platform name (Instagram, TikTok, Twitter, etc.)
        """
        self.platform = platform
        self.weights = PLATFORM_WEIGHTS.get(platform, PLATFORM_WEIGHTS['default'])
        logger.debug(f"Initialized EngagementCalculator for {platform} with weights: {self.weights}")
    
    def calculate(
        self,
        likes: int = 0,
        comments: int = 0,
        shares: int = 0,
        views: int = 0,
        audience_size: Optional[int] = None,
        normalize: bool = False,
        apply_time_decay: bool = False,
        post_age_hours: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculate weighted engagement score.
        
        Args:
            likes: Number of likes
            comments: Number of comments
            shares: Number of shares (retweets, reposts, saves)
            views: Number of views
            audience_size: Optional audience/follower count for normalization
            normalize: Whether to normalize by audience size
            apply_time_decay: Whether to apply time decay factor
            post_age_hours: Age of post in hours (for time decay)
            
        Returns:
            Dictionary with engagement score and breakdown
        """
        # Ensure non-negative values
        likes = max(0, int(likes) if likes else 0)
        comments = max(0, int(comments) if comments else 0)
        shares = max(0, int(shares) if shares else 0)
        views = max(0, int(views) if views else 0)
        
        # Calculate weighted components
        likes_score = likes * self.weights.likes_weight
        comments_score = comments * self.weights.comments_weight
        shares_score = shares * self.weights.shares_weight
        views_score = views * self.weights.views_weight
        
        # Calculate raw engagement score
        raw_score = likes_score + comments_score + shares_score + views_score
        
        # Calculate total engagement (unweighted sum)
        total_engagement = likes + comments + shares
        
        # Normalize by audience size if requested
        normalized_score = raw_score
        engagement_rate = None
        if normalize and audience_size and audience_size > 0:
            normalized_score = raw_score / audience_size * 1000  # Per 1000 followers
            engagement_rate = (total_engagement / audience_size * 100) if total_engagement > 0 else 0.0
        
        # Apply time decay if requested
        decay_factor = 1.0
        if apply_time_decay and post_age_hours is not None:
            decay_factor = self._calculate_time_decay(post_age_hours)
            normalized_score = normalized_score * decay_factor
        
        # Calculate final score
        final_score = normalized_score if normalize else raw_score
        
        # Calculate component percentages
        total_weighted = likes_score + comments_score + shares_score + views_score
        if total_weighted > 0:
            likes_percent = (likes_score / total_weighted) * 100
            comments_percent = (comments_score / total_weighted) * 100
            shares_percent = (shares_score / total_weighted) * 100
            views_percent = (views_score / total_weighted) * 100
        else:
            likes_percent = comments_percent = shares_percent = views_percent = 0.0
        
        return {
            'engagement_score': round(final_score, 2),
            'raw_score': round(raw_score, 2),
            'normalized_score': round(normalized_score, 2) if normalize else None,
            'engagement_rate': round(engagement_rate, 4) if engagement_rate is not None else None,
            'total_engagement': total_engagement,
            'components': {
                'likes': {
                    'count': likes,
                    'weight': self.weights.likes_weight,
                    'weighted_score': round(likes_score, 2),
                    'percentage': round(likes_percent, 2)
                },
                'comments': {
                    'count': comments,
                    'weight': self.weights.comments_weight,
                    'weighted_score': round(comments_score, 2),
                    'percentage': round(comments_percent, 2)
                },
                'shares': {
                    'count': shares,
                    'weight': self.weights.shares_weight,
                    'weighted_score': round(shares_score, 2),
                    'percentage': round(shares_percent, 2)
                },
                'views': {
                    'count': views,
                    'weight': self.weights.views_weight,
                    'weighted_score': round(views_score, 2),
                    'percentage': round(views_percent, 2)
                }
            },
            'weights': {
                'likes': self.weights.likes_weight,
                'comments': self.weights.comments_weight,
                'shares': self.weights.shares_weight,
                'views': self.weights.views_weight
            },
            'platform': self.platform,
            'decay_factor': round(decay_factor, 4) if apply_time_decay else None,
            'normalized': normalize
        }
    
    def _calculate_time_decay(self, age_hours: float) -> float:
        """
        Calculate time decay factor.
        
        Formula: decay = 1 / (1 + age_hours / half_life_hours)
        Half-life: 24 hours (score halves after 24 hours)
        
        Args:
            age_hours: Age of post in hours
            
        Returns:
            Decay factor (0.0 to 1.0)
        """
        half_life_hours = 24.0  # Score halves after 24 hours
        decay = 1.0 / (1.0 + age_hours / half_life_hours)
        return max(0.0, min(1.0, decay))  # Clamp between 0 and 1
    
    def calculate_average(
        self,
        posts: list,
        normalize: bool = False,
        apply_time_decay: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate average engagement score across multiple posts.
        
        Args:
            posts: List of post dictionaries with likes, comments, shares, views
            normalize: Whether to normalize by audience size
            apply_time_decay: Whether to apply time decay
            
        Returns:
            Dictionary with average engagement score and breakdown
        """
        if not posts:
            return self.calculate()
        
        total_likes = 0
        total_comments = 0
        total_shares = 0
        total_views = 0
        total_audience = 0
        valid_posts = 0
        
        for post in posts:
            likes = post.get('likes', 0) or 0
            comments = post.get('comments', 0) or 0
            shares = post.get('shares', 0) or post.get('saves', 0) or 0
            views = post.get('views', 0) or 0
            audience = post.get('audience_size', 0) or post.get('followers', 0) or 0
            
            total_likes += likes
            total_comments += comments
            total_shares += shares
            total_views += views
            total_audience += audience
            valid_posts += 1
        
        if valid_posts == 0:
            return self.calculate()
        
        avg_likes = total_likes / valid_posts
        avg_comments = total_comments / valid_posts
        avg_shares = total_shares / valid_posts
        avg_views = total_views / valid_posts
        avg_audience = total_audience / valid_posts if total_audience > 0 else None
        
        return self.calculate(
            likes=avg_likes,
            comments=avg_comments,
            shares=avg_shares,
            views=avg_views,
            audience_size=int(avg_audience) if avg_audience else None,
            normalize=normalize,
            apply_time_decay=apply_time_decay
        )
    
    @staticmethod
    def get_platform_weights(platform: str) -> EngagementWeights:
        """
        Get weight configuration for a specific platform.
        
        Args:
            platform: Platform name
            
        Returns:
            EngagementWeights: The weight configuration object.
        """
        return PLATFORM_WEIGHTS.get(platform, PLATFORM_WEIGHTS['default'])
    
    @staticmethod
    def set_custom_weights(
        platform: str,
        likes_weight: float = 1.0,
        comments_weight: float = 2.0,
        shares_weight: float = 3.0,
        views_weight: float = 0.1
    ):
        """
        Set custom weights for a specific platform.
        
        Args:
            platform: Platform name to configure
            likes_weight: Weight for likes
            comments_weight: Weight for comments
            shares_weight: Weight for shares/saves
            views_weight: Weight for views
        """
        PLATFORM_WEIGHTS[platform] = EngagementWeights(
            likes_weight=likes_weight,
            comments_weight=comments_weight,
            shares_weight=shares_weight,
            views_weight=views_weight
        )
        logger.info(f"Set custom weights for {platform}: {PLATFORM_WEIGHTS[platform]}")


def calculate_engagement_score(
    platform: str,
    likes: int = 0,
    comments: int = 0,
    shares: int = 0,
    views: int = 0,
    normalize: bool = False,
    audience_size: Optional[int] = None
) -> float:
    """
    Convenience function to calculate engagement score.
    
    Args:
        platform: Platform name
        likes: Number of likes
        comments: Number of comments
        shares: Number of shares
        views: Number of views
        normalize: Whether to normalize by audience size
        audience_size: Audience size for normalization
        
    Returns:
        Engagement score (float)
    """
    calculator = EngagementCalculator(platform)
    result = calculator.calculate(
        likes=likes,
        comments=comments,
        shares=shares,
        views=views,
        normalize=normalize,
        audience_size=audience_size
    )
    return result['engagement_score']

