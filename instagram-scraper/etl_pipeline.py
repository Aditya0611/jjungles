"""
ETL Pipeline for Instagram Scraper Data

Transforms raw scraper payloads into validated database records with:
- Data validation and cleaning
- Schema transformation
- Upsert logic with conflict resolution
- Error handling and retry
- Data quality checks
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of data validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    cleaned_data: Optional[Dict[str, Any]] = None


class DataValidator:
    """Validates and cleans scraper payload data."""
    
    # Field constraints
    MIN_HASHTAG_LENGTH = 2
    MAX_HASHTAG_LENGTH = 50
    MIN_ENGAGEMENT = 0
    MAX_ENGAGEMENT = 10_000_000_000  # 10 billion
    MIN_LIKES = 0
    MAX_LIKES = 1_000_000_000  # 1 billion
    MIN_COMMENTS = 0
    MAX_COMMENTS = 100_000_000  # 100 million
    MIN_VIEWS = 0
    MAX_VIEWS = 10_000_000_000  # 10 billion
    MIN_ENGAGEMENT_SCORE = 0.0
    MAX_ENGAGEMENT_SCORE = 1_000_000_000.0
    MIN_LANGUAGE_CONFIDENCE = 0.0
    MAX_LANGUAGE_CONFIDENCE = 1.0
    VALID_LANGUAGE_CODES = {
        'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh', 'ar', 'hi',
        'nl', 'sv', 'pl', 'tr', 'th', 'vi', 'id', 'cs', 'da', 'fi', 'no', 'ro',
        'hu', 'el', 'he', 'uk', 'bg', 'hr', 'sk', 'sl', 'et', 'lv', 'lt', 'mt'
    }
    
    @classmethod
    def validate_hashtag(cls, hashtag: str) -> Tuple[bool, str]:
        """
        Validate a single hashtag for length and character requirements.
        
        Args:
            hashtag: The hashtag string to validate
            
        Returns:
            Tuple[bool, str]: (is_valid, clean_hashtag_or_error_message)
        """
        if not hashtag or not isinstance(hashtag, str):
            return False, "Hashtag must be a non-empty string"
        
        # Remove # if present
        clean_hashtag = hashtag.lstrip('#').strip()
        
        if len(clean_hashtag) < cls.MIN_HASHTAG_LENGTH:
            return False, f"Hashtag too short (min {cls.MIN_HASHTAG_LENGTH} chars)"
        
        if len(clean_hashtag) > cls.MAX_HASHTAG_LENGTH:
            return False, f"Hashtag too long (max {cls.MAX_HASHTAG_LENGTH} chars)"
        
        # Check for valid characters (alphanumeric and underscore)
        if not re.match(r'^[a-zA-Z0-9_]+$', clean_hashtag):
            return False, "Hashtag contains invalid characters"
        
        return True, clean_hashtag.lower()
    
    @classmethod
    def validate_hashtags(cls, hashtags: List[str]) -> Tuple[List[str], List[str]]:
        """
        Validate a list of hashtags and separate valid ones from errors.
        
        Args:
            hashtags: List of hashtag strings
            
        Returns:
            Tuple[List[str], List[str]]: (valid_hashtags, error_messages)
        """
        valid_hashtags = []
        errors = []
        
        for hashtag in hashtags:
            is_valid, result = cls.validate_hashtag(hashtag)
            if is_valid:
                valid_hashtags.append(result)
            else:
                errors.append(f"Invalid hashtag '{hashtag}': {result}")
        
        return valid_hashtags, errors
    
    @classmethod
    def validate_engagement_metric(cls, value: Any, field_name: str, 
                                   min_val: int, max_val: int) -> Tuple[bool, Optional[int]]:
        """Validate engagement metric (likes, comments, views)."""
        if value is None:
            return True, 0  # Allow None, default to 0
        
        try:
            int_value = int(float(value))  # Handle float strings
        except (ValueError, TypeError):
            return False, None
        
        if int_value < min_val:
            return False, None
        
        if int_value > max_val:
            logger.warning(f"{field_name} value {int_value} exceeds max {max_val}, capping")
            return True, max_val
        
        return True, int_value
    
    @classmethod
    def validate_engagement_score(cls, score: Any) -> Tuple[bool, Optional[float]]:
        """Validate engagement score."""
        if score is None:
            return True, 0.0
        
        try:
            float_score = float(score)
        except (ValueError, TypeError):
            return False, None
        
        if float_score < cls.MIN_ENGAGEMENT_SCORE:
            return False, None
        
        if float_score > cls.MAX_ENGAGEMENT_SCORE:
            logger.warning(f"Engagement score {float_score} exceeds max, capping")
            return True, cls.MAX_ENGAGEMENT_SCORE
        
        return True, round(float_score, 2)
    
    @classmethod
    def validate_language(cls, language: str) -> Tuple[bool, Optional[str]]:
        """Validate language code (ISO 639-1)."""
        if not language or not isinstance(language, str):
            return True, None  # Language is optional
        
        lang_code = language.lower().strip()
        
        # Check if it's a valid ISO 639-1 code
        if len(lang_code) == 2 and lang_code in cls.VALID_LANGUAGE_CODES:
            return True, lang_code
        
        # Try to extract 2-letter code from longer strings
        if len(lang_code) >= 2:
            two_letter = lang_code[:2]
            if two_letter in cls.VALID_LANGUAGE_CODES:
                return True, two_letter
        
        logger.warning(f"Invalid language code: {language}, defaulting to None")
        return True, None  # Allow invalid, just log warning
    
    @classmethod
    def validate_url(cls, url: str) -> Tuple[bool, Optional[str]]:
        """Validate URL."""
        if not url or not isinstance(url, str):
            return False, None
        
        url = url.strip()
        
        # Basic URL validation
        if not url.startswith(('http://', 'https://', '/')):
            return False, None
        
        # Check length
        if len(url) > 500:
            return False, None
        
        return True, url
    
    @classmethod
    def validate_timestamp(cls, timestamp: Any) -> Tuple[bool, Optional[datetime]]:
        """Validate timestamp."""
        if timestamp is None:
            return True, datetime.utcnow()
        
        if isinstance(timestamp, datetime):
            return True, timestamp
        
        if isinstance(timestamp, str):
            try:
                # Try ISO format
                return True, datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                pass
        
        return False, None
    
    @classmethod
    def validate_trend_record(cls, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate a complete trend record.
        
        Args:
            data: Raw trend record data
            
        Returns:
            ValidationResult with validation status and cleaned data
        """
        errors = []
        warnings = []
        cleaned_data = {}
        
        # Validate platform
        platform = data.get('platform', 'Instagram')
        if not platform or not isinstance(platform, str):
            errors.append("Platform must be a non-empty string")
        else:
            cleaned_data['platform'] = platform.strip()
        
        # Validate URL
        url = data.get('url', '')
        is_valid_url, valid_url = cls.validate_url(url)
        if not is_valid_url:
            errors.append(f"Invalid URL: {url}")
        else:
            cleaned_data['url'] = valid_url
        
        # Validate hashtags
        hashtags = data.get('hashtags', [])
        if not isinstance(hashtags, list):
            errors.append("Hashtags must be a list")
        else:
            valid_hashtags, hashtag_errors = cls.validate_hashtags(hashtags)
            errors.extend(hashtag_errors)
            if valid_hashtags:
                cleaned_data['hashtags'] = valid_hashtags
            else:
                errors.append("At least one valid hashtag is required")
        
        # Validate engagement metrics
        likes = data.get('likes', 0)
        is_valid_likes, valid_likes = cls.validate_engagement_metric(
            likes, 'likes', cls.MIN_LIKES, cls.MAX_LIKES
        )
        if not is_valid_likes:
            errors.append(f"Invalid likes value: {likes}")
        else:
            cleaned_data['likes'] = valid_likes
        
        comments = data.get('comments', 0)
        is_valid_comments, valid_comments = cls.validate_engagement_metric(
            comments, 'comments', cls.MIN_COMMENTS, cls.MAX_COMMENTS
        )
        if not is_valid_comments:
            errors.append(f"Invalid comments value: {comments}")
        else:
            cleaned_data['comments'] = valid_comments
        
        views = data.get('views', 0)
        is_valid_views, valid_views = cls.validate_engagement_metric(
            views, 'views', cls.MIN_VIEWS, cls.MAX_VIEWS
        )
        if not is_valid_views:
            errors.append(f"Invalid views value: {views}")
        else:
            cleaned_data['views'] = valid_views
        
        # Validate engagement score
        engagement_score = data.get('engagement_score', 0.0)
        is_valid_score, valid_score = cls.validate_engagement_score(engagement_score)
        if not is_valid_score:
            errors.append(f"Invalid engagement_score value: {engagement_score}")
        else:
            cleaned_data['engagement_score'] = valid_score
            
        # Optional engagement metrics (shares, reactions for cross-platform)
        cleaned_data['shares'] = int(data.get('shares', 0))
        cleaned_data['reactions'] = int(data.get('reactions', 0))
        
        # Validate language (optional)
        language = data.get('language', 'en')
        is_valid_lang, valid_lang = cls.validate_language(language)
        if is_valid_lang:
            cleaned_data['language'] = valid_lang or 'en'
        else:
            warnings.append(f"Invalid language code: {language}, using default")
            cleaned_data['language'] = 'en'
        
        # Validate timestamp
        timestamp = data.get('timestamp')
        is_valid_ts, valid_ts = cls.validate_timestamp(timestamp)
        if not is_valid_ts:
            warnings.append(f"Invalid timestamp: {timestamp}, using current time")
            cleaned_data['timestamp'] = datetime.utcnow()
        else:
            cleaned_data['timestamp'] = valid_ts
        
        # Validate version
        version = data.get('version', '')
        if not version or not isinstance(version, str):
            errors.append("Version must be a non-empty string")
        else:
            cleaned_data['version'] = version.strip()
        
        # Validate raw_blob (optional, but should be dict if present)
        raw_blob = data.get('raw_blob', {})
        if raw_blob is not None and not isinstance(raw_blob, dict):
            warnings.append("raw_blob should be a dictionary, converting")
            cleaned_data['raw_blob'] = {}
        else:
            cleaned_data['raw_blob'] = raw_blob or {}
        
        # Add first_seen and last_seen if not present
        if 'first_seen' not in cleaned_data:
            cleaned_data['first_seen'] = cleaned_data['timestamp']
        else:
            is_valid_fs, valid_fs = cls.validate_timestamp(cleaned_data.get('first_seen'))
            if not is_valid_fs:
                cleaned_data['first_seen'] = cleaned_data['timestamp']
        
        if 'last_seen' not in cleaned_data:
            cleaned_data['last_seen'] = cleaned_data['timestamp']
        else:
            is_valid_ls, valid_ls = cls.validate_timestamp(cleaned_data.get('last_seen'))
            if not is_valid_ls:
                cleaned_data['last_seen'] = cleaned_data['timestamp']
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            cleaned_data=cleaned_data if len(errors) == 0 else None
        )


class DataTransformer:
    """Transforms raw scraper data into database-ready format."""
    
    @staticmethod
    def transform_hashtag_data(hashtag_data: Dict[str, Any], 
                              engagement_data: Dict[str, Any],
                              version_id: str) -> Dict[str, Any]:
        """
        Transform hashtag and engagement data into trend record format.
        
        Args:
            hashtag_data: Raw hashtag data from scraper
            engagement_data: Raw engagement data from scraper
            version_id: Version identifier
            
        Returns:
            Transformed data dictionary
        """
        now = datetime.utcnow()
        
        # Extract primary hashtag
        primary_hashtag = hashtag_data.get('hashtag', '').lstrip('#').lower()
        
        # Build hashtags list
        hashtags = [f"#{primary_hashtag}"]
        
        # Build URL
        url = f"https://www.instagram.com/explore/tags/{primary_hashtag}/"
        
        # Transform engagement data
        transformed = {
            'platform': 'Instagram',
            'url': url,
            'hashtags': hashtags,
            'likes': int(engagement_data.get('avg_likes', 0)),
            'comments': int(engagement_data.get('avg_comments', 0)),
            'views': int(engagement_data.get('avg_views', 0)),
            'language': engagement_data.get('language_summary', {}).get('primary_language', 'en'),
            'timestamp': now,
            'engagement_score': float(engagement_data.get('avg_engagement', 0.0)),
            'shares': int(engagement_data.get('avg_shares', 0)),
            'reactions': int(engagement_data.get('avg_reactions', 0)),
            'version': version_id,
            'raw_blob': {
                'category': hashtag_data.get('category', 'unknown'),
                'frequency': hashtag_data.get('frequency', 0),
                'posts_count': hashtag_data.get('posts_count', 0),
                'sample_posts': hashtag_data.get('sample_posts', []),
                'discovery_method': 'explore_page',
                'avg_likes': engagement_data.get('avg_likes', 0),
                'avg_comments': engagement_data.get('avg_comments', 0),
                'total_engagement': engagement_data.get('total_engagement', 0),
                'total_views': engagement_data.get('total_views', 0),
                'video_count': engagement_data.get('video_count', 0),
                'posts_analyzed': engagement_data.get('posts_analyzed', 0),
                'sentiment_summary': engagement_data.get('sentiment_summary', {}),
                'language_summary': engagement_data.get('language_summary', {}),
                'content_types': engagement_data.get('content_types', {}),
                'primary_format': engagement_data.get('primary_format', 'photo'),
                'discovered_at': now.isoformat()
            },
            'first_seen': now,
            'last_seen': now
        }
        
        return transformed
    
    @staticmethod
    def normalize_hashtag(hashtag: str) -> str:
        """
        Normalize a hashtag by removing leading # and converting to lowercase.
        
        Args:
            hashtag: The hashtag string to normalize
            
        Returns:
            str: The normalized hashtag
        """
        return hashtag.lstrip('#').lower().strip()
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean text data."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove control characters
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        return text.strip()


class ETLPipeline:
    """
    ETL Pipeline for transforming and loading scraper data.
    
    Handles:
    - Data extraction from scraper payloads
    - Transformation and validation
    - Upsert operations with conflict resolution
    - Error handling and retry logic
    """
    
    def __init__(self, supabase_client, validator: DataValidator = None, 
                 transformer: DataTransformer = None):
        """
        Initialize ETL pipeline.
        
        Args:
            supabase_client: Supabase client instance
            validator: Data validator instance (optional)
            transformer: Data transformer instance (optional)
        """
        self.supabase = supabase_client
        self.validator = validator or DataValidator()
        self.transformer = transformer or DataTransformer()
        self.logger = logging.getLogger(__name__)
    
    def extract(self, hashtag_data: Dict[str, Any], 
                engagement_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract data from scraper payloads.
        
        Args:
            hashtag_data: Hashtag data from scraper
            engagement_data: Engagement data from scraper
            
        Returns:
            Combined raw data dictionary
        """
        return {
            'hashtag_data': hashtag_data,
            'engagement_data': engagement_data
        }
    
    def transform(self, raw_data: Dict[str, Any], version_id: str) -> ValidationResult:
        """
        Transform raw data into validated database format.
        
        Args:
            raw_data: Raw data from extract step
            version_id: Version identifier
            
        Returns:
            ValidationResult with cleaned data
        """
        # Transform data
        transformed = self.transformer.transform_hashtag_data(
            raw_data['hashtag_data'],
            raw_data['engagement_data'],
            version_id
        )
        
        # Validate transformed data
        validation_result = self.validator.validate_trend_record(transformed)
        
        if validation_result.warnings:
            for warning in validation_result.warnings:
                self.logger.warning(f"Data transformation warning: {warning}")
        
        return validation_result
    
    def load(self, validated_data: Dict[str, Any], 
             conflict_resolution: str = 'update') -> Tuple[bool, Optional[str]]:
        """
        Load validated data into normalized database tables.
        
        Args:
            validated_data: Validated and cleaned data
            conflict_resolution: How to handle conflicts ('update', 'ignore', 'error')
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # 1. Upsert Trend
            trend_payload = {
                'platform': validated_data['platform'],
                'url': validated_data['url'],
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Upsert trend and get ID
            trend_res = self.supabase.table('trends').upsert(
                trend_payload, on_conflict='url'
            ).execute()
            
            if not trend_res.data:
                return False, "Failed to upsert trend"
            
            trend_id = trend_res.data[0]['id']
            
            # 2. Upsert Hashtags and Link
            for hashtag in validated_data['hashtags']:
                # Upsert hashtag
                tag_payload = {'name': hashtag, 'category': validated_data['raw_blob'].get('category')}
                tag_res = self.supabase.table('hashtags').upsert(
                    tag_payload, on_conflict='name'
                ).execute()
                
                if tag_res.data:
                    tag_id = tag_res.data[0]['id']
                    
                    # Link in trend_hashtags
                    link_payload = {
                        'trend_id': trend_id,
                        'hashtag_id': tag_id,
                        'is_primary': hashtag == validated_data['hashtags'][0]
                    }
                    self.supabase.table('trend_hashtags').upsert(
                        link_payload, on_conflict='trend_id,hashtag_id'
                    ).execute()
            
            # 3. Insert Engagement Metrics
            sentiment_summary = validated_data.get('raw_blob', {}).get('sentiment_summary', {})
            metrics_payload = {
                'trend_id': trend_id,
                'recorded_at': validated_data['timestamp'].isoformat() if hasattr(validated_data['timestamp'], 'isoformat') else validated_data['timestamp'],
                'likes': validated_data['likes'],
                'comments': validated_data['comments'],
                'views': validated_data['views'],
                'shares': validated_data.get('shares', 0),
                'reactions': validated_data.get('reactions', 0),
                'engagement_score': validated_data['engagement_score'],
                'version_id': validated_data['version'],
                'language': validated_data.get('language'),
                'sentiment_polarity': sentiment_summary.get('avg_polarity', 0.0),
                'sentiment_label': sentiment_summary.get('overall_label', 'neutral')
            }
            self.supabase.table('engagement_metrics').insert(metrics_payload).execute()
            
            # 4. Insert Snapshot (Audit Trail)
            snapshot_payload = {
                'trend_id': trend_id,
                'recorded_at': validated_data['timestamp'].isoformat(),
                'raw_data': validated_data['raw_blob'],
                'version_id': validated_data['version']
            }
            self.supabase.table('snapshots').insert(snapshot_payload).execute()
            
            return True, None
            
        except Exception as e:
            error_msg = f"Database load failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg

    def _find_existing_record(self, validated_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find existing record by URL.
        """
        try:
            res = self.supabase.table('trends').select('*').eq('url', validated_data['url']).execute()
            if res.data:
                return res.data[0]
            return None
        except Exception as e:
            self.logger.warning(f"Error finding existing record: {e}")
            return None
    
    def process(self, hashtag_data: Dict[str, Any], 
                engagement_data: Dict[str, Any],
                version_id: str,
                conflict_resolution: str = 'update') -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Complete ETL process: Extract, Transform, Load.
        
        Args:
            hashtag_data: Hashtag data from scraper
            engagement_data: Engagement data from scraper
            version_id: Version identifier
            conflict_resolution: How to handle conflicts
            
        Returns:
            Tuple of (success, error_message, validated_data)
        """
        try:
            # Extract
            raw_data = self.extract(hashtag_data, engagement_data)
            
            # Transform and validate
            validation_result = self.transform(raw_data, version_id)
            
            if not validation_result.is_valid:
                error_msg = f"Validation failed: {', '.join(validation_result.errors)}"
                self.logger.error(error_msg)
                return False, error_msg, None
            
            # Load
            success, error_msg = self.load(validation_result.cleaned_data, conflict_resolution)
            
            if success:
                return True, None, validation_result.cleaned_data
            else:
                return False, error_msg, validation_result.cleaned_data
                
        except Exception as e:
            error_msg = f"ETL process failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg, None
    
    def batch_process(self, records: List[Tuple[Dict[str, Any], Dict[str, Any]]],
                     version_id: str,
                     conflict_resolution: str = 'update') -> Dict[str, Any]:
        """
        Process multiple records in batch.
        
        Args:
            records: List of (hashtag_data, engagement_data) tuples
            version_id: Version identifier
            conflict_resolution: How to handle conflicts
            
        Returns:
            Dictionary with success/failure counts and errors
        """
        results = {
            'total': len(records),
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        for hashtag_data, engagement_data in records:
            success, error_msg, validated_data = self.process(
                hashtag_data,
                engagement_data,
                version_id,
                conflict_resolution
            )
            
            if success:
                results['successful'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({
                    'hashtag': hashtag_data.get('hashtag', 'unknown'),
                    'error': error_msg
                })
        
        return results

