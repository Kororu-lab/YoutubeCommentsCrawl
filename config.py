#!/usr/bin/env python3
"""
Configuration settings for YouTube Comment Scraper
Clean, production-ready configuration.
"""

import os

# ==========================================
# GENERAL SETTINGS
# ==========================================
OUTPUT_DIR = "comments_data"
HEADLESS_MODE = True  # Set to True for headless operation

# ==========================================
# SCRAPING BEHAVIOR
# ==========================================
# Timeout settings
DEFAULT_TIMEOUT = 10  # WebDriver wait timeout (seconds)
PAGE_LOAD_WAIT = 3    # Wait time for page to load (seconds)

# Scrolling settings for smart infinite scroll
MAX_SCROLL_ATTEMPTS = 5000         # Maximum scroll attempts (reasonable limit)
SCROLL_DELAY = 2                  # Delay between scroll attempts (seconds) - increased for YouTube's lazy loading
INITIAL_SCROLL_ATTEMPTS = 5       # Initial scrolls to reach comments section
MAX_NO_NEW_COMMENTS = 1        # Stop after N attempts with no new comments - MUCH more patient

# Video processing delays
VIDEO_DELAY = 2  # Delay between processing videos (seconds)

# ==========================================
# FEATURES EXTRACTED
# ==========================================
# The scraper extracts all available comment data fields:
# - comment_text: The comment content
# - author_name: Comment author's display name
# - upvotes: Number of likes (thumbs up)
# - downvotes: Always 0 (YouTube removed public downvote counts)
# - reply_count: Number of replies to the comment
# - timestamp: When the comment was posted (relative time)
# - is_pinned: Whether the comment is pinned by the creator
# - is_hearted: Whether the comment is hearted by the creator
# - has_dislike_button: Whether the dislike button is present
#
# Plus video metadata:
# - video_no, video_date, channel_name, video_title, video_url
# - total_comments, total_likes, total_views
# - comment_position, scraped_at

# ==========================================
# VIDEO FILTERING (Active)
# ==========================================
# These thresholds filter videos before processing
# Set to 0 or None to disable filtering
MIN_COMMENTS = 10      # Minimum comments to process video
MIN_LIKES = 0         # Minimum likes to process video  
MIN_VIEWS = 500         # Minimum views to process video
MAX_COMMENTS = None   # Maximum comments (None for no limit)
MAX_LIKES = None      # Maximum likes (None for no limit)
MAX_VIEWS = None      # Maximum views (None for no limit)

# ==========================================
# VALIDATION
# ==========================================
def validate_config():
    """Validate configuration settings"""
    errors = []
    
    # Check timeout values
    if DEFAULT_TIMEOUT <= 0:
        errors.append("DEFAULT_TIMEOUT must be > 0")
    if PAGE_LOAD_WAIT <= 0:
        errors.append("PAGE_LOAD_WAIT must be > 0")
        
    # Check scroll settings
    if MAX_SCROLL_ATTEMPTS <= 0:
        errors.append("MAX_SCROLL_ATTEMPTS must be > 0")
    if SCROLL_DELAY <= 0:
        errors.append("SCROLL_DELAY must be > 0")
    if MAX_NO_NEW_COMMENTS <= 0:
        errors.append("MAX_NO_NEW_COMMENTS must be > 0")
        
    # Check delay settings
    if VIDEO_DELAY < 0:
        errors.append("VIDEO_DELAY must be >= 0")
        
    # Check filter thresholds
    if MIN_COMMENTS < 0:
        errors.append("MIN_COMMENTS must be >= 0")
    if MIN_LIKES < 0:
        errors.append("MIN_LIKES must be >= 0")
    if MIN_VIEWS < 0:
        errors.append("MIN_VIEWS must be >= 0")
        
    if errors:
        raise ValueError("Configuration errors:\n" + "\n".join(errors))
    
    return True

# Validate config on import
validate_config() 