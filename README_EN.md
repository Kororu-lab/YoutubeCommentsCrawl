# YouTube Comment Crawler

A production-ready Python scraper for extracting comments and engagement metrics from YouTube videos with intelligent infinite scroll support.

## ✨ Features

- **Smart Infinite Scroll**: Automatically detects when comments finish loading (doesn't scroll into related videos)
- **Complete Engagement Data**: Extracts upvotes, replies, timestamps, and creator interactions
- **Video Metadata Integration**: Combines comments with original video data from CSV
- **Error Handling**: Gracefully handles removed/unavailable videos
- **Progress Tracking**: Saves progress and provides detailed reporting
- **Production Ready**: Clean, refactored code following best practices

## 🚀 Quick Start

1. **Install Dependencies**:
   ```bash
   pip install selenium pandas webdriver-manager
   ```

2. **Run the Scraper**:
   ```bash
   python youtube_comment_scraper.py your_video_data.csv
   ```

3. **View Results**:
   - Comments are saved to `comments_data/youtube_comments_YYYYMMDD_HHMMSS.csv`
   - Progress is tracked in `progress.json`

## 📊 Data Extracted

### Comment Data
- `comment_text`: The comment content
- `author_name`: Comment author's display name  
- `upvotes`: Number of likes (thumbs up)
- `reply_count`: Number of replies to the comment
- `timestamp`: When the comment was posted
- `is_pinned`: Whether pinned by creator
- `is_hearted`: Whether hearted by creator

### Video Metadata (from CSV)
- `video_no`, `video_date`, `channel_name`, `video_title`
- `total_comments`, `total_likes`, `total_views`
- `comment_position`, `scraped_at`

## 📁 Project Structure

```
YoutubeCrawl/
├── youtube_comment_scraper.py  # Main scraper (production-ready)
├── config.py                   # Configuration settings
├── README.md                   # Documentation
├── process_youtube_data.py     # Data processing utilities
├── read_excel.py              # Excel file reader
├── comments_data/             # Output directory
├── data/                      # Input Excel files
├── url_list/                  # Generated URL lists
├── working_test.csv           # Test dataset (5 working videos)
├── mini_test.csv              # Minimal test dataset (3 videos)
└── top10_test.csv             # Top 10 videos test dataset
```

## ⚙️ Configuration

Edit `config.py` to customize scraping behavior:

```python
# Scraping behavior
MAX_SCROLL_ATTEMPTS = 30        # Maximum scroll attempts
SCROLL_DELAY = 3                # Delay between scrolls (seconds)
VIDEO_DELAY = 3                 # Delay between videos (seconds)

# Browser settings
HEADLESS_MODE = False           # Run browser in background
DEFAULT_TIMEOUT = 15            # Page load timeout (seconds)
```

## 📈 Performance

- **Smart Scrolling**: Stops when comments finish (not related videos)
- **Fast Processing**: ~2-3 minutes for 5 videos with 100+ comments
- **Memory Efficient**: Processes videos sequentially to avoid memory issues
- **Robust Error Handling**: Continues processing even if individual videos fail

## 🔧 Usage Examples

### Basic Usage
```bash
python youtube_comment_scraper.py ./data/merged_youtube_data.csv
```

### Test with Small Dataset
```bash
python youtube_comment_scraper.py working_test.csv
```

### Process Specific Video Set
```bash
python youtube_comment_scraper.py mini_test.csv
```

## 📋 CSV Input Format

Your CSV file should contain these columns:
- `URL`: YouTube video URLs
- `제목`: Video title (Korean)
- `채널명`: Channel name (Korean)
- `날짜`: Upload date (Korean)
- `댓글 수`: Comment count (Korean)
- `좋아요 수`: Like count (Korean)
- `조회수`: View count (Korean)

## 🎯 Smart Scroll Algorithm

The scraper uses an intelligent scrolling algorithm that:

1. **Focuses on Comments**: Tracks actual comment elements, not page height
2. **Detects Completion**: Stops when no new comments load after multiple attempts
3. **Avoids Related Videos**: Detects when scrolling reaches related content
4. **Final Attempt**: Makes one aggressive scroll before stopping
5. **Progress Logging**: Shows real-time comment loading progress

## 📊 Output Example

```
📊 YOUTUBE COMMENT SCRAPING SUMMARY:
📁 Output file: comments_data/youtube_comments_20231215_143022.csv
💬 Total comments: 136
🎥 Videos processed: 5
✅ Successful videos: 5
❌ Failed videos: 0
👥 Unique authors: 121
👍 Total upvotes: 540
💭 Comments with replies: 23
📈 Average comments per video: 27.2
```

## 🛠️ Development

The codebase follows clean code principles:

- **Single Responsibility**: Each method has a clear, focused purpose
- **Error Handling**: Comprehensive exception handling with logging
- **Configuration**: Centralized settings in `config.py`
- **Documentation**: Clear docstrings and comments
- **Validation**: Configuration validation on startup

## 📝 Logging

- All activities are logged to `scraper.log`
- Progress is saved to `progress.json` for recovery
- Failed videos are tracked with detailed error information
- Real-time console output shows scraping progress

## 🔍 Troubleshooting

### Video Not Found
- Check if video URL is correct and accessible
- Some videos may be region-restricted or deleted

### Slow Performance
- Increase `SCROLL_DELAY` in config for better reliability
- Run in headless mode: set `HEADLESS_MODE = True`

### Memory Issues
- Process smaller batches of videos
- Restart scraper periodically for large datasets

## 📜 License

This project is for educational and research purposes. Please respect YouTube's Terms of Service and rate limits. 