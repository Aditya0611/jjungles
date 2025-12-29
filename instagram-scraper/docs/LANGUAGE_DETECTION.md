# Language Detection & Localized Filtering

## Overview

The scraper now includes automatic language detection for post captions using `langdetect`, enabling localized filtering for multi-language client accounts.

## Features

### 1. **Automatic Language Detection**
- Detects language from post captions using `langdetect` library
- Provides confidence scores for language detection
- Falls back to default language if detection fails or confidence is too low

### 2. **Language Aggregation**
- Aggregates language data across all posts in a hashtag
- Determines primary language (most common)
- Calculates language distribution percentages
- Tracks detection rate (how many posts had successful detection)

### 3. **Localized Filtering**
- Filter trends by specific languages
- Support for multi-language client accounts
- Configurable language whitelist

## Configuration

### Environment Variables

```bash
# Enable/disable language detection
ENABLE_LANGUAGE_DETECTION=true  # Default: true

# Filter by specific languages (comma-separated ISO 639-1 codes)
FILTER_LANGUAGES="en,es,fr"  # Empty = no filtering (include all)

# Minimum confidence threshold for language detection
MIN_LANGUAGE_CONFIDENCE=0.5  # Default: 0.5 (50% confidence)
```

### Default Values

- **Language Detection**: Enabled
- **Filter Languages**: Empty (no filtering)
- **Min Confidence**: 0.5 (50%)

## How It Works

### Language Detection Process

1. **Caption Extraction**: Extracts caption text from each post
2. **Language Detection**: Uses `langdetect` to detect language
3. **Confidence Check**: Validates detection confidence against threshold
4. **Fallback**: Uses default language if detection fails or confidence too low

### Language Aggregation

For each hashtag, the system:
- Collects language data from all analyzed posts
- Counts occurrences of each language
- Determines primary language (most common)
- Calculates:
  - Primary language percentage
  - Average confidence score
  - Detection rate (successful detections / total posts)
  - Full language distribution

### Language Filtering

If `FILTER_LANGUAGES` is configured:
- Only trends with primary language in the whitelist are saved
- Supports multiple languages (comma-separated)
- Case-insensitive matching

## Data Structure

### Post-Level Language Data

```python
{
    'language': 'en',              # ISO 639-1 language code
    'language_confidence': 0.95,   # Detection confidence (0-1)
    'language_detected': True,     # Whether detection was successful
    'all_languages': [              # All detected languages with scores
        {'lang': 'en', 'prob': 0.95},
        {'lang': 'es', 'prob': 0.05}
    ]
}
```

### Hashtag-Level Language Summary

```python
{
    'primary_language': 'en',                    # Most common language
    'primary_language_percent': 85.0,            # % of posts in primary language
    'primary_language_count': 17,                # Number of posts in primary language
    'avg_confidence': 0.92,                       # Average confidence for primary language
    'detected_count': 18,                        # Posts with successful detection
    'total_analyzed': 20,                        # Total posts analyzed
    'distribution': {                             # Full language distribution
        'en': 17,
        'es': 2,
        'fr': 1
    },
    'detection_rate': 90.0                       # % of posts with successful detection
}
```

## Database Storage

Language data is stored in the `metadata` field:

```json
{
  "metadata": {
    "language_summary": {
      "primary_language": "en",
      "primary_language_percent": 85.0,
      "primary_language_count": 17,
      "avg_confidence": 0.92,
      "detected_count": 18,
      "total_analyzed": 20,
      "distribution": {
        "en": 17,
        "es": 2,
        "fr": 1
      },
      "detection_rate": 90.0
    }
  }
}
```

The `language` field in the main record stores the primary language code.

## Usage Examples

### Filter by English Only

```bash
FILTER_LANGUAGES="en"
ENABLE_LANGUAGE_DETECTION=true
```

### Multi-Language Support (English, Spanish, French)

```bash
FILTER_LANGUAGES="en,es,fr"
ENABLE_LANGUAGE_DETECTION=true
```

### Disable Language Detection

```bash
ENABLE_LANGUAGE_DETECTION=false
```

### Higher Confidence Threshold

```bash
MIN_LANGUAGE_CONFIDENCE=0.8  # Require 80% confidence
```

## Querying by Language

### Query trends by primary language

```sql
SELECT * FROM instagram
WHERE language = 'en'
ORDER BY engagement_score DESC;
```

### Query by language distribution

```sql
SELECT * FROM instagram
WHERE metadata->'language_summary'->>'primary_language' = 'es'
  AND (metadata->'language_summary'->>'primary_language_percent')::float > 80.0
ORDER BY engagement_score DESC;
```

### Multi-language query

```sql
SELECT * FROM instagram
WHERE language IN ('en', 'es', 'fr')
ORDER BY engagement_score DESC;
```

## Supported Languages

`langdetect` supports 55+ languages including:
- English (en)
- Spanish (es)
- French (fr)
- German (de)
- Italian (it)
- Portuguese (pt)
- Russian (ru)
- Chinese (zh)
- Japanese (ja)
- Korean (ko)
- Arabic (ar)
- And many more...

See [langdetect documentation](https://github.com/Mimino666/langdetect) for full list.

## Benefits

1. **Localized Content Discovery**
   - Find trends in specific languages
   - Target regional markets
   - Support multi-language brands

2. **Quality Filtering**
   - Filter out irrelevant languages
   - Focus on target audience
   - Improve trend relevance

3. **Analytics**
   - Track language distribution
   - Monitor multi-language trends
   - Understand global reach

4. **Client Customization**
   - Configure per client account
   - Support regional campaigns
   - Multi-language brand support

## Troubleshooting

### Low Detection Rate

If detection rate is low:
- Check caption quality (may be too short)
- Lower `MIN_LANGUAGE_CONFIDENCE` threshold
- Ensure captions are being extracted correctly

### Incorrect Language Detection

If wrong languages detected:
- Increase `MIN_LANGUAGE_CONFIDENCE` threshold
- Check for mixed-language content
- Verify caption extraction is working

### Language Not Detected

If language not in supported list:
- Check langdetect supported languages
- May need to use default language
- Consider custom language detection

## Installation

Language detection requires `langdetect`:

```bash
pip install langdetect==1.0.9
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

