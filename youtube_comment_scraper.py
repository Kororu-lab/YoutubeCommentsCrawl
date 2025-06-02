#!/usr/bin/env python3
"""
YouTube Comment Scraper - Production Version
Extracts comments and engagement metrics from YouTube videos with infinite scroll support.

Features:
- Smart infinite scroll that stops when comments finish (not related videos)
- Extracts upvotes, downvotes, replies, timestamps, and engagement metrics
- Saves all comments to single CSV with original video metadata
- Handles removed/unavailable videos gracefully
- Progress tracking and error recovery
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import config


class YouTubeCommentScraper:
    """Production YouTube comment scraper with smart infinite scroll"""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.all_comments = []
        self.processed_videos = []
        self.failed_videos = []
        self.setup_logging()
        self.setup_directories()
        
    def setup_logging(self):
        """Configure logging with appropriate level and format"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('scraper.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_directories(self):
        """Create necessary output directories"""
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        
    def setup_chrome_driver(self) -> bool:
        """Setup Chrome WebDriver with optimized settings"""
        try:
            chrome_options = self._get_chrome_options()
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.maximize_window()
            self.wait = WebDriverWait(self.driver, config.DEFAULT_TIMEOUT)
            
            self.logger.info("Chrome WebDriver initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to setup Chrome WebDriver: {e}")
            return False
    
    def _get_chrome_options(self) -> Options:
        """Configure Chrome options for optimal performance"""
        chrome_options = Options()
        
        # Performance optimizations
        performance_args = [
            '--no-sandbox',
            '--disable-dev-shm-usage', 
            '--disable-gpu',
            '--mute-audio'
        ]
        
        for arg in performance_args:
            chrome_options.add_argument(arg)
        
        # Data-saving preferences
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "profile.managed_default_content_settings.images": 2,
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Add headless mode if configured
        if config.HEADLESS_MODE:
            chrome_options.add_argument('--headless')
            
        return chrome_options
    
    def check_video_availability(self, url: str) -> bool:
        """Check if video is available and accessible"""
        try:
            self.logger.info(f"Checking video availability: {self._extract_video_id(url)}")
            self.driver.get(url)
            time.sleep(config.PAGE_LOAD_WAIT)
            
            # Check for video player presence
            try:
                self.wait.until(EC.presence_of_element_located((By.ID, "movie_player")))
                self.logger.info("✅ Video is available")
                return True
            except TimeoutException:
                self.logger.warning("❌ Video player not found - video may be unavailable")
                return False
                
        except Exception as e:
            self.logger.error(f"Error checking video availability: {e}")
            return False
    
    def smart_infinite_scroll(self) -> bool:
        """Intelligent infinite scroll that focuses only on loading comments"""
        try:
            self.logger.info("Starting smart comment-focused scroll...")
            
            # Navigate to comments section
            if not self._scroll_to_comments_section():
                return False
            
            # Perform intelligent scrolling
            comment_count = self._perform_smart_scroll()
            
            self.logger.info(f"🎯 Smart scroll completed: {comment_count} total comments loaded")
            return comment_count > 0
            
        except Exception as e:
            self.logger.error(f"Error during smart infinite scroll: {e}")
            return False
    
    def _scroll_to_comments_section(self) -> bool:
        """Scroll to and locate the comments section"""
        self.logger.info("Scrolling to comments section...")
        
        # Initial scroll to comments area
        for _ in range(config.INITIAL_SCROLL_ATTEMPTS):
            self.driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(1)
        
        # Wait for comments section to load
        try:
            comments_section = self.wait.until(
                EC.presence_of_element_located((By.ID, "comments"))
            )
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                comments_section
            )
            time.sleep(3)
            self.logger.info("✅ Comments section found and focused")
            return True
        except TimeoutException:
            self.logger.warning("❌ Comments section not found")
            return False
    
    def _perform_smart_scroll(self) -> int:
        """Perform intelligent scrolling with YouTube-specific comment loading"""
        last_comment_count = 0
        scroll_attempts = 0
        no_new_comments_count = 0
        
        # Get initial comment count
        current_comments = self._get_current_comments()
        last_comment_count = len(current_comments)
        self.logger.info(f"Initial comment count: {last_comment_count}")
        
        while scroll_attempts < config.MAX_SCROLL_ATTEMPTS:
            scroll_attempts += 1
            
            # YouTube-specific scrolling to trigger comment loading
            success = self._youtube_specific_scroll()
            
            # Use longer delay if we have many comments (YouTube loads slower with more content)
            delay = config.SCROLL_DELAY
            if last_comment_count > 100:
                delay = config.SCROLL_DELAY + 1  # Extra second for videos with many comments
            
            time.sleep(delay)
            
            # Check for new comments
            current_comments = self._get_current_comments()
            current_count = len(current_comments)
            
            self.logger.info(f"📊 Scroll {scroll_attempts}/{config.MAX_SCROLL_ATTEMPTS}: {current_count} comments (was {last_comment_count})")
            
            if self._has_new_comments(current_count, last_comment_count):
                new_comments = current_count - last_comment_count
                self.logger.info(f"✅ SUCCESS! {new_comments} new comments loaded! Total: {current_count}")
                last_comment_count = current_count
                no_new_comments_count = 0
            else:
                no_new_comments_count += 1
                patience_remaining = config.MAX_NO_NEW_COMMENTS - no_new_comments_count
                self.logger.info(f"⏳ No new comments found (attempt {no_new_comments_count}/{config.MAX_NO_NEW_COMMENTS}, {patience_remaining} attempts remaining)")
                
                # Quick extra attempt only if we have very few comments
                if no_new_comments_count >= config.MAX_NO_NEW_COMMENTS // 2 and last_comment_count < 50:  # Only for low comment videos
                    self.logger.info("🔄 Low comment count - trying one extra scroll strategy...")
                    self._extra_patient_scroll()
                
                if self._should_stop_scrolling(no_new_comments_count, last_comment_count):
                    self.logger.info(f"🛑 Stopping scroll: tried {no_new_comments_count} times with no new comments")
                    break
        
        return last_comment_count
    
    def _get_current_comments(self) -> List:
        """Get current comment elements from the page"""
        return self.driver.find_elements(By.CSS_SELECTOR, "ytd-comment-thread-renderer")
    
    def _youtube_specific_scroll(self) -> bool:
        """YouTube-specific scrolling to properly trigger comment loading"""
        try:
            # Method 1: Always focus on the last visible comment first
            comments = self._get_current_comments()
            if comments:
                last_comment = comments[-1]
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
                    last_comment
                )
                time.sleep(1)
                
                # Scroll a bit more past the last comment to trigger loading
                self.driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(1)
            
            # Method 2: Try to find and click continuation items first (most reliable)
            try:
                continuation_buttons = self.driver.find_elements(By.CSS_SELECTOR, 
                    "ytd-continuation-item-renderer, tp-yt-paper-button[aria-label*='Show more']")
                for button in continuation_buttons:
                    if button.is_displayed():
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                        time.sleep(1)
                        self.driver.execute_script("arguments[0].click();", button)
                        self.logger.info("🔄 Clicked continuation button")
                        time.sleep(3)  # Wait longer for loading
                        return True
            except:
                pass
            
            # Method 3: Conservative scroll - don't go too far down
            # Stay near comments area instead of scrolling to absolute bottom
            current_pos = self.driver.execute_script("return window.pageYOffset;")
            self.driver.execute_script("window.scrollBy(0, 1200);")  # Moderate scroll
            time.sleep(1)
            
            # Method 4: Check if we need to scroll back up (if we went too far)
            comments_section = self.driver.find_elements(By.CSS_SELECTOR, "#comments")
            if comments_section:
                comments_rect = self.driver.execute_script(
                    "return arguments[0].getBoundingClientRect();", comments_section[0]
                )
                # If comments section is above viewport, scroll back to it
                if comments_rect['bottom'] < 0:
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        comments_section[0]
                    )
                    time.sleep(1)
            
            return True
            
        except Exception as e:
            self.logger.debug(f"Error in YouTube-specific scroll: {e}")
            # Fallback to simple scroll
            self.driver.execute_script("window.scrollBy(0, 800);")
            return False
    
    def _extra_patient_scroll(self):
        """Extra patient scrolling when we're having trouble loading more comments"""
        self.logger.info("🔄 Trying extra patient scroll strategies...")
        
        try:
            # Strategy 1: Multiple slow scrolls to bottom
            for i in range(2):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)  # Wait longer between scrolls
                self.logger.info(f"  Extra scroll {i+1}/2 to bottom")
            
            # Strategy 2: Scroll up a bit, then back down (sometimes triggers loading)
            self.driver.execute_script("window.scrollBy(0, -500);")
            time.sleep(1)
            self.driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(2)
            
            # Strategy 3: Try to click any continuation elements
            try:
                continuation_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                    "ytd-continuation-item-renderer, .ytd-continuation-item-renderer")
                for element in continuation_elements:
                    if element.is_displayed():
                        self.driver.execute_script("arguments[0].click();", element)
                        self.logger.info("🔄 Clicked continuation element")
                        time.sleep(3)
                        break
            except:
                pass
            
        except Exception as e:
            self.logger.debug(f"Error in extra patient scroll: {e}")
    
    def _has_new_comments(self, current_count: int, last_count: int) -> bool:
        """Check if new comments were loaded"""
        return current_count > last_count
    
    def _should_stop_scrolling(self, no_new_count: int, last_count: int) -> bool:
        """Determine if scrolling should stop based on multiple criteria"""
        # Stop if no new comments for several attempts
        if no_new_count >= config.MAX_NO_NEW_COMMENTS:
            # Try one final aggressive scroll
            if self._try_final_scroll(last_count):
                return False  # Continue if final scroll found more
            return True  # Stop if final scroll found nothing
        
        # Only check for related videos if we've tried many times AND have few comments
        # This prevents premature stopping when there are still comments to load
        if no_new_count >= 15 and last_count < 100:  # Much more conservative
            if self._detect_related_videos_section():
                self.logger.info("📺 Detected related videos section after many attempts - stopping scroll")
                return True
            
        return False
    
    def _try_final_scroll(self, last_count: int) -> bool:
        """Make multiple final aggressive scroll attempts using YouTube-specific methods"""
        self.logger.info("🔄 Final attempts: trying YouTube-specific loading patterns...")
        
        # Try multiple YouTube-specific scroll patterns
        for attempt in range(3):  # Quick final attempts
            self.logger.info(f"  Final scroll attempt {attempt + 1}/3")
            
            # Use the same YouTube-specific scrolling
            self._youtube_specific_scroll()
            time.sleep(4)  # Even longer wait for YouTube's lazy loading
            
            # Check for more comments
            final_comments = self._get_current_comments()
            final_count = len(final_comments)
            
            if final_count > last_count:
                self.logger.info(f"✅ Final attempt found {final_count - last_count} more comments!")
                return True
            
            # Skip extra attempts for efficiency - 920 comments is already great!
        
        self.logger.info("🛑 No more comments found after 3 quick YouTube-specific attempts.")
        return False
    
    def _detect_related_videos_section(self) -> bool:
        """Detect if we've scrolled into the related videos section (very conservative)"""
        try:
            # Much more conservative detection - look for many related videos
            # AND make sure we're not in the comments section
            related_videos = self.driver.find_elements(
                By.CSS_SELECTOR, "ytd-compact-video-renderer"
            )
            
            # Only consider it related videos section if:
            # 1. There are many related videos (15+)
            # 2. AND we can't find any comment loading indicators
            if len(related_videos) > 15:
                # Check if we're still in comments area
                comments_area = self.driver.find_elements(By.CSS_SELECTOR, "#comments")
                continuation_items = self.driver.find_elements(By.CSS_SELECTOR, "ytd-continuation-item-renderer")
                
                # If comments area exists or there are continuation items, we're not done
                if comments_area or continuation_items:
                    return False
                
                return True
            
            return False
        except:
            return False
    
    def extract_comment_data(self, comment_element) -> Optional[Dict]:
        """Extract comprehensive comment data including engagement metrics"""
        try:
            comment_data = {}
            
            # Extract core comment information
            comment_data.update(self._extract_basic_comment_info(comment_element))
            comment_data.update(self._extract_engagement_metrics(comment_element))
            comment_data.update(self._extract_comment_metadata(comment_element))
            
            return comment_data if comment_data.get('comment_text') else None
            
        except Exception as e:
            self.logger.debug(f"Error extracting comment data: {e}")
            return None
    
    def _extract_basic_comment_info(self, comment_element) -> Dict:
        """Extract basic comment text and author information"""
        data = {}
        
        # Comment text
        try:
            text_element = comment_element.find_element(By.CSS_SELECTOR, "#content-text")
            data['comment_text'] = text_element.text.strip()
        except:
            data['comment_text'] = ""
        
        # Author name
        try:
            author_element = comment_element.find_element(By.CSS_SELECTOR, "#author-text")
            data['author_name'] = author_element.text.strip()
        except:
            data['author_name'] = ""
            
        return data
    
    def _extract_engagement_metrics(self, comment_element) -> Dict:
        """Extract engagement metrics (likes, replies, etc.)"""
        data = {}
        
        # Upvotes/Likes
        try:
            like_element = comment_element.find_element(By.CSS_SELECTOR, "#vote-count-middle")
            data['upvotes'] = self._parse_count(like_element.text.strip())
        except:
            data['upvotes'] = 0
        
        # Downvotes (YouTube removed public counts)
        data['downvotes'] = 0
        data['has_dislike_button'] = self._has_dislike_button(comment_element)
        
        # Reply count
        try:
            reply_element = comment_element.find_element(By.CSS_SELECTOR, "#more-replies")
            data['reply_count'] = self._parse_reply_count(reply_element.text.strip())
        except:
            data['reply_count'] = 0
            
        return data
    
    def _extract_comment_metadata(self, comment_element) -> Dict:
        """Extract comment metadata (timestamp, status flags)"""
        data = {}
        
        # Timestamp
        try:
            time_element = comment_element.find_element(By.CSS_SELECTOR, ".published-time-text a")
            data['timestamp'] = time_element.text.strip()
        except:
            data['timestamp'] = ""
        
        # Status flags
        data['is_pinned'] = self._is_comment_pinned(comment_element)
        data['is_hearted'] = self._is_comment_hearted(comment_element)
        
        return data
    
    def _parse_count(self, count_text: str) -> int:
        """Parse count strings (e.g., '1.2K', '500') to integers"""
        if not count_text:
            return 0
        
        count_text = count_text.upper().replace(',', '')
        
        # Handle K (thousands) and M (millions)
        multipliers = {'K': 1000, 'M': 1000000}
        
        for suffix, multiplier in multipliers.items():
            if suffix in count_text:
                try:
                    return int(float(count_text.replace(suffix, '')) * multiplier)
                except:
                    return 0
        
        # Handle regular numbers
        try:
            return int(count_text)
        except:
            return 0
    
    def _parse_reply_count(self, reply_text: str) -> int:
        """Extract reply count from reply button text"""
        import re
        try:
            numbers = re.findall(r'\d+', reply_text)
            return int(numbers[0]) if numbers else 0
        except:
            return 0
    
    def _has_dislike_button(self, comment_element) -> bool:
        """Check if comment has a dislike button"""
        try:
            comment_element.find_element(By.CSS_SELECTOR, "[aria-label*='Dislike']")
            return True
        except:
            return False
    
    def _is_comment_pinned(self, comment_element) -> bool:
        """Check if comment is pinned by creator"""
        try:
            comment_element.find_element(By.CSS_SELECTOR, "[aria-label*='Pinned']")
            return True
        except:
            return False
    
    def _is_comment_hearted(self, comment_element) -> bool:
        """Check if comment is hearted by creator"""
        try:
            comment_element.find_element(By.CSS_SELECTOR, "#creator-heart")
            return True
        except:
            return False
    
    def scrape_video_comments(self, video_url: str, video_data: Dict) -> List[Dict]:
        """Scrape all comments from a single video"""
        video_comments = []
        
        try:
            # Check video availability
            if not self.check_video_availability(video_url):
                self.failed_videos.append({
                    'url': video_url, 
                    'reason': 'Video unavailable',
                    'timestamp': datetime.now().isoformat()
                })
                return video_comments
            
            # Load comments with smart scrolling
            if not self.smart_infinite_scroll():
                self.logger.warning("Could not load comments")
                return video_comments
            
            # Extract all loaded comments
            comment_elements = self._get_current_comments()
            self.logger.info(f"Extracting {len(comment_elements)} comments...")
            
            video_comments = self._process_comment_elements(
                comment_elements, video_data, video_url
            )
            
            self.logger.info(f"Successfully extracted {len(video_comments)} comments")
            return video_comments
            
        except Exception as e:
            self.logger.error(f"Error scraping video {video_url}: {e}")
            self.failed_videos.append({
                'url': video_url,
                'reason': str(e),
                'timestamp': datetime.now().isoformat()
            })
            return video_comments
    
    def _process_comment_elements(self, comment_elements: List, video_data: Dict, video_url: str) -> List[Dict]:
        """Process comment elements and add video metadata"""
        video_comments = []
        
        for i, comment_element in enumerate(comment_elements):
            try:
                # Extract main comment
                main_comment = comment_element.find_element(By.CSS_SELECTOR, "#comment")
                comment_data = self.extract_comment_data(main_comment)
                
                if comment_data:
                    # Add video metadata
                    comment_data.update(self._build_video_metadata(video_data, video_url, i + 1))
                    video_comments.append(comment_data)
                
                # Progress logging
                if (i + 1) % 50 == 0:
                    self.logger.info(f"Processed {i + 1}/{len(comment_elements)} comments")
                    
            except Exception as e:
                self.logger.debug(f"Error processing comment {i}: {e}")
                continue
        
        return video_comments
    
    def _build_video_metadata(self, video_data: Dict, video_url: str, position: int) -> Dict:
        """Build comprehensive video metadata for each comment"""
        return {
            # Original video data from CSV
            'video_no': video_data.get('No.', ''),
            'video_date': video_data.get('날짜', ''),
            'channel_name': video_data.get('채널명', ''),
            'video_title': video_data.get('제목', ''),
            'video_url': video_data.get('URL', video_url),
            'total_comments': video_data.get('댓글 수', 0),
            'total_likes': video_data.get('좋아요 수', 0),
            'total_views': video_data.get('조회수', 0),
            
            # Scraping metadata
            'scraped_at': datetime.now().isoformat(),
            'comment_position': position
        }
    
    def save_results(self) -> str:
        """Save all scraped comments to CSV with comprehensive reporting"""
        if not self.all_comments:
            self.logger.warning("No comments to save")
            return ""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"youtube_comments_{timestamp}.csv"
        filepath = os.path.join(config.OUTPUT_DIR, filename)
        
        # Create DataFrame with ordered columns
        df = pd.DataFrame(self.all_comments)
        df = self._reorder_dataframe_columns(df)
        
        # Save to CSV
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        self.logger.info(f"Saved {len(self.all_comments)} comments to {filepath}")
        
        # Generate and display summary
        self._display_scraping_summary(df, filepath)
        
        return filepath
    
    def _reorder_dataframe_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Reorder DataFrame columns for better readability"""
        column_order = [
            'video_no', 'video_date', 'channel_name', 'video_title', 'video_url',
            'total_comments', 'total_likes', 'total_views',
            'comment_position', 'comment_text', 'author_name', 
            'upvotes', 'downvotes', 'reply_count', 'timestamp',
            'is_pinned', 'is_hearted', 'has_dislike_button', 'scraped_at'
        ]
        
        # Only include columns that exist
        existing_columns = [col for col in column_order if col in df.columns]
        return df[existing_columns]
    
    def _display_scraping_summary(self, df: pd.DataFrame, filepath: str):
        """Display comprehensive scraping summary"""
        print(f"\n📊 YOUTUBE COMMENT SCRAPING SUMMARY:")
        print(f"📁 Output file: {filepath}")
        print(f"💬 Total comments: {len(self.all_comments):,}")
        print(f"🎥 Videos processed: {df['video_url'].nunique()}")
        print(f"✅ Successful videos: {len(self.processed_videos)}")
        print(f"❌ Failed videos: {len(self.failed_videos)}")
        print(f"👥 Unique authors: {df['author_name'].nunique()}")
        print(f"👍 Total upvotes: {df['upvotes'].sum():,}")
        print(f"💭 Comments with replies: {(df['reply_count'] > 0).sum()}")
        
        if len(self.processed_videos) > 0:
            avg_comments = len(self.all_comments) / len(self.processed_videos)
            print(f"📈 Average comments per video: {avg_comments:.1f}")
    
    def save_progress(self):
        """Save progress information for debugging and recovery"""
        progress_data = {
            'processed_videos': self.processed_videos,
            'failed_videos': self.failed_videos,
            'total_comments_scraped': len(self.all_comments),
            'last_updated': datetime.now().isoformat()
        }
        
        with open('progress.json', 'w') as f:
            json.dump(progress_data, f, indent=2)
    
    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL"""
        try:
            return url.split('v=')[1].split('&')[0]
        except:
            return f"unknown_{hash(url) % 10000}"
    
    def apply_video_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply video filtering based on config thresholds"""
        original_count = len(df)
        
        # Convert string numbers to integers for filtering
        df = df.copy()
        
        # Helper function to convert Korean number strings to integers
        def parse_korean_number(value):
            if pd.isna(value) or value == '':
                return 0
            try:
                # Convert to string and remove commas
                str_val = str(value).replace(',', '').replace(' ', '')
                return int(float(str_val))
            except:
                return 0
        
        # Parse numeric columns
        df['댓글수_int'] = df.get('댓글 수', 0).apply(parse_korean_number)
        df['좋아요수_int'] = df.get('좋아요 수', 0).apply(parse_korean_number)
        df['조회수_int'] = df.get('조회수', 0).apply(parse_korean_number)
        
        # Apply filters
        filters_applied = []
        
        # Filter by minimum comments
        if config.MIN_COMMENTS > 0:
            before = len(df)
            df = df[df['댓글수_int'] >= config.MIN_COMMENTS]
            removed = before - len(df)
            if removed > 0:
                filters_applied.append(f"MIN_COMMENTS({config.MIN_COMMENTS}): removed {removed}")
        
        # Filter by minimum likes
        if config.MIN_LIKES > 0:
            before = len(df)
            df = df[df['좋아요수_int'] >= config.MIN_LIKES]
            removed = before - len(df)
            if removed > 0:
                filters_applied.append(f"MIN_LIKES({config.MIN_LIKES}): removed {removed}")
        
        # Filter by minimum views
        if config.MIN_VIEWS > 0:
            before = len(df)
            df = df[df['조회수_int'] >= config.MIN_VIEWS]
            removed = before - len(df)
            if removed > 0:
                filters_applied.append(f"MIN_VIEWS({config.MIN_VIEWS}): removed {removed}")
        
        # Filter by maximum thresholds if set
        if config.MAX_COMMENTS is not None:
            before = len(df)
            df = df[df['댓글수_int'] <= config.MAX_COMMENTS]
            removed = before - len(df)
            if removed > 0:
                filters_applied.append(f"MAX_COMMENTS({config.MAX_COMMENTS}): removed {removed}")
        
        if config.MAX_LIKES is not None:
            before = len(df)
            df = df[df['좋아요수_int'] <= config.MAX_LIKES]
            removed = before - len(df)
            if removed > 0:
                filters_applied.append(f"MAX_LIKES({config.MAX_LIKES}): removed {removed}")
        
        if config.MAX_VIEWS is not None:
            before = len(df)
            df = df[df['조회수_int'] <= config.MAX_VIEWS]
            removed = before - len(df)
            if removed > 0:
                filters_applied.append(f"MAX_VIEWS({config.MAX_VIEWS}): removed {removed}")
        
        # Log filtering results
        total_removed = original_count - len(df)
        if total_removed > 0:
            self.logger.info(f"📊 Video filtering applied:")
            for filter_result in filters_applied:
                self.logger.info(f"  - {filter_result}")
            self.logger.info(f"  Total videos removed: {total_removed}")
        else:
            self.logger.info("📊 No videos filtered out (all videos meet thresholds)")
        
        # Remove helper columns
        df = df.drop(columns=['댓글수_int', '좋아요수_int', '조회수_int'], errors='ignore')
        
        return df
    
    def process_videos(self, csv_file: str):
        """Main processing function - scrape comments from all videos in CSV"""
        try:
            # Load video data
            df = pd.read_csv(csv_file)
            self.logger.info(f"Loaded {len(df)} videos from {csv_file}")
            
            # Apply filtering based on config thresholds
            df_filtered = self.apply_video_filters(df)
            self.logger.info(f"After filtering: {len(df_filtered)} videos (removed {len(df) - len(df_filtered)} videos)")
            
            # Setup WebDriver
            if not self.setup_chrome_driver():
                self.logger.error("Failed to setup WebDriver. Exiting.")
                return
            
            # Process each video
            for index, row in df_filtered.iterrows():
                try:
                    video_url = row['URL']
                    video_id = self._extract_video_id(video_url)
                    
                    self.logger.info(f"Processing video {index + 1}/{len(df)}: {video_id}")
                    
                    # Scrape comments
                    comments = self.scrape_video_comments(video_url, row.to_dict())
                    
                    if comments:
                        self.all_comments.extend(comments)
                        self.processed_videos.append(video_url)
                        self.logger.info(f"Added {len(comments)} comments. Total: {len(self.all_comments)}")
                    
                    # Save progress and add delay
                    self.save_progress()
                    time.sleep(config.VIDEO_DELAY)
                    
                except KeyboardInterrupt:
                    self.logger.info("Interrupted by user. Saving progress...")
                    break
                except Exception as e:
                    self.logger.error(f"Error processing video {index}: {e}")
                    continue
            
            # Save final results
            output_file = self.save_results()
            self.logger.info(f"Scraping completed. Results saved to {output_file}")
            
        finally:
            if self.driver:
                self.driver.quit()
                self.logger.info("WebDriver closed")


def main():
    """Main entry point"""
    if len(sys.argv) != 2:
        print("Usage: python youtube_comment_scraper.py <csv_file>")
        print("Example: python youtube_comment_scraper.py ./data/merged_youtube_data.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    if not os.path.exists(csv_file):
        print(f"❌ File not found: {csv_file}")
        sys.exit(1)
    
    print("🚀 Starting YouTube Comment Scraper...")
    scraper = YouTubeCommentScraper()
    scraper.process_videos(csv_file)


if __name__ == "__main__":
    main() 