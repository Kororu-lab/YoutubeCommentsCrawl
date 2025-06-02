#!/bin/bash

# YouTube Comment Scraper Runner Script
# Makes it easy to run the scraper with different datasets

echo "🚀 YouTube Comment Scraper Runner"
echo "=================================="

# Color codes for better output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to display usage
show_usage() {
    echo -e "${BLUE}Usage:${NC}"
    echo "  ./run_scraper.sh [option]"
    echo ""
    echo -e "${BLUE}Options:${NC}"
    echo "  mini        - Run with mini test dataset (3 videos)"
    echo "  test        - Run with working test dataset (5 videos)"
    echo "  top10       - Run with top 10 test dataset (10 videos)"
    echo "  full        - Run with full dataset (5,363 videos)"
    echo "  background  - Run full dataset in background with logging"
    echo ""
    echo -e "${BLUE}Examples:${NC}"
    echo "  ./run_scraper.sh mini"
    echo "  ./run_scraper.sh full"
    echo "  ./run_scraper.sh background"
}

# Function to check if file exists
check_file() {
    if [ ! -f "$1" ]; then
        echo -e "${RED}❌ Error: File '$1' not found!${NC}"
        exit 1
    fi
}

# Function to activate virtual environment
activate_venv() {
    # Check for different virtual environment setups
    if [ -d ".venv" ]; then
        echo -e "${BLUE}🔧 Activating .venv virtual environment...${NC}"
        source .venv/bin/activate
        return 0
    elif [ -d "venv" ]; then
        echo -e "${BLUE}🔧 Activating venv virtual environment...${NC}"
        source venv/bin/activate
        return 0
    elif [ -d "env" ]; then
        echo -e "${BLUE}🔧 Activating env virtual environment...${NC}"
        source env/bin/activate
        return 0
    else
        echo -e "${YELLOW}⚠️  No virtual environment found (.venv, venv, or env)${NC}"
        echo -e "${YELLOW}⚠️  Trying to run with current Python environment...${NC}"
        return 1
    fi
}

# Function to run scraper
run_scraper() {
    local dataset="$1"
    local description="$2"
    
    echo -e "${YELLOW}📊 Running scraper with $description${NC}"
    echo -e "${BLUE}Dataset:${NC} $dataset"
    echo -e "${BLUE}Config:${NC} Headless mode enabled, optimized settings"
    echo ""
    
    check_file "$dataset"
    
    # Check if we're in the right directory
    if [ ! -f "youtube_comment_scraper.py" ]; then
        echo -e "${RED}❌ Error: youtube_comment_scraper.py not found in current directory!${NC}"
        exit 1
    fi
    
    # Activate virtual environment
    activate_venv
    
    # Check if selenium is available
    python -c "import selenium" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Error: selenium not found! Please install dependencies:${NC}"
        echo -e "${BLUE}   pip install selenium pandas webdriver-manager${NC}"
        exit 1
    fi
    
    # Run the scraper
    python youtube_comment_scraper.py "$dataset"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Scraping completed successfully!${NC}"
        echo -e "${BLUE}📁 Check the comments_data/ directory for results${NC}"
    else
        echo -e "${RED}❌ Scraping failed!${NC}"
        exit 1
    fi
}

# Function to run in background
run_background() {
    local dataset="$1"
    local logfile="scraping_output_$(date +%Y%m%d_%H%M%S).log"
    
    echo -e "${YELLOW}🔄 Running scraper in background...${NC}"
    echo -e "${BLUE}Dataset:${NC} $dataset"
    echo -e "${BLUE}Log file:${NC} $logfile"
    echo ""
    
    check_file "$dataset"
    
    # Activate virtual environment
    activate_venv
    
    # Check if selenium is available
    python -c "import selenium" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Error: selenium not found! Please install dependencies first.${NC}"
        exit 1
    fi
    
    # Create a wrapper script that activates venv and runs the scraper
    cat > temp_scraper_runner.sh << EOF
#!/bin/bash
cd "$(pwd)"
$(if [ -d ".venv" ]; then echo "source .venv/bin/activate"; elif [ -d "venv" ]; then echo "source venv/bin/activate"; elif [ -d "env" ]; then echo "source env/bin/activate"; fi)
python youtube_comment_scraper.py "$dataset"
EOF
    
    chmod +x temp_scraper_runner.sh
    
    # Run in background with logging
    nohup ./temp_scraper_runner.sh > "$logfile" 2>&1 &
    local pid=$!
    
    # Clean up temp script after a delay
    (sleep 5 && rm -f temp_scraper_runner.sh) &
    
    echo -e "${GREEN}✅ Scraper started in background (PID: $pid)${NC}"
    echo -e "${BLUE}📝 Monitor progress with:${NC} tail -f $logfile"
    echo -e "${BLUE}🔍 Check process with:${NC} ps aux | grep $pid"
    echo -e "${BLUE}⏹️  Stop process with:${NC} kill $pid"
}

# Main script logic
case "$1" in
    "mini")
        run_scraper "mini_test.csv" "mini test dataset (3 videos)"
        ;;
    "test")
        run_scraper "working_test.csv" "working test dataset (5 videos)"
        ;;
    "top10")
        run_scraper "top10_test.csv" "top 10 test dataset (10 videos)"
        ;;
    "full")
        run_scraper "data/merged_youtube_data.csv" "full dataset (5,363 videos)"
        ;;
    "background")
        run_background "data/merged_youtube_data.csv"
        ;;
    "-h"|"--help"|"help")
        show_usage
        ;;
    "")
        echo -e "${RED}❌ Error: No option provided!${NC}"
        echo ""
        show_usage
        exit 1
        ;;
    *)
        echo -e "${RED}❌ Error: Unknown option '$1'${NC}"
        echo ""
        show_usage
        exit 1
        ;;
esac 