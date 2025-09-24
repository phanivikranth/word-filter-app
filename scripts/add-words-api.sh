#!/bin/bash

# Script to add words to the Word Filter App via API
# Usage: ./add-words-api.sh [word1] [word2] [word3]...

# Configuration
APP_URL="${WORD_FILTER_URL:-http://localhost:8001}"  # Change to your app URL
TIMEOUT=10

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to add a single word
add_single_word() {
    local word=$1
    log_info "Adding word: $word"
    
    response=$(curl -s -w "\n%{http_code}" -X POST "$APP_URL/words/add" \
        -H "Content-Type: application/json" \
        -d "{\"word\":\"$word\"}" \
        --connect-timeout $TIMEOUT)
    
    http_code=$(echo "$response" | tail -n1)
    response_body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" -eq 200 ]; then
        was_new=$(echo "$response_body" | grep -o '"was_new":[^,]*' | cut -d':' -f2)
        if [ "$was_new" = "true" ]; then
            log_success "Added new word: $word"
        else
            log_info "Word already exists: $word"
        fi
    else
        log_error "Failed to add word: $word (HTTP $http_code)"
        echo "$response_body"
    fi
}

# Function to add multiple words in batch
add_batch_words() {
    local words=("$@")
    log_info "Adding ${#words[@]} words in batch..."
    
    # Create JSON array
    word_array="["
    for i in "${!words[@]}"; do
        word_array+="\"${words[i]}\""
        if [ $i -lt $((${#words[@]} - 1)) ]; then
            word_array+=","
        fi
    done
    word_array+="]"
    
    response=$(curl -s -w "\n%{http_code}" -X POST "$APP_URL/words/add-batch" \
        -H "Content-Type: application/json" \
        -d "{\"words\":$word_array}" \
        --connect-timeout $TIMEOUT)
    
    http_code=$(echo "$response" | tail -n1)
    response_body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" -eq 200 ]; then
        added_count=$(echo "$response_body" | grep -o '"added_count":[^,]*' | cut -d':' -f2)
        total_submitted=$(echo "$response_body" | grep -o '"total_submitted":[^,]*' | cut -d':' -f2)
        log_success "Added $added_count new words out of $total_submitted submitted"
    else
        log_error "Failed to add words in batch (HTTP $http_code)"
        echo "$response_body"
    fi
}

# Function to check if word exists
check_word() {
    local word=$1
    log_info "Checking if word exists: $word"
    
    response=$(curl -s -X POST "$APP_URL/words/check" \
        -H "Content-Type: application/json" \
        -d "{\"word\":\"$word\"}" \
        --connect-timeout $TIMEOUT)
    
    exists=$(echo "$response" | grep -o '"exists":[^,]*' | cut -d':' -f2)
    if [ "$exists" = "true" ]; then
        log_success "Word exists: $word"
    else
        log_info "Word does not exist: $word"
    fi
}

# Function to show word statistics
show_stats() {
    log_info "Getting word statistics..."
    
    response=$(curl -s "$APP_URL/words/stats" --connect-timeout $TIMEOUT)
    
    if [ $? -eq 0 ]; then
        total_words=$(echo "$response" | grep -o '"total_words":[^,]*' | cut -d':' -f2)
        avg_length=$(echo "$response" | grep -o '"avg_length":[^,]*' | cut -d':' -f2)
        s3_connected=$(echo "$response" | grep -o '"s3_connected":[^,]*' | cut -d':' -f2)
        
        echo "📊 Word Statistics:"
        echo "   Total Words: $total_words"
        echo "   Average Length: $avg_length"
        echo "   S3 Connected: $s3_connected"
    else
        log_error "Failed to get statistics"
    fi
}

# Function to test API connectivity
test_connection() {
    log_info "Testing API connection to $APP_URL"
    
    response=$(curl -s "$APP_URL/health" --connect-timeout $TIMEOUT)
    
    if [ $? -eq 0 ]; then
        status=$(echo "$response" | grep -o '"status":[^,]*' | cut -d':' -f2 | tr -d '"')
        if [ "$status" = "healthy" ]; then
            log_success "API is healthy and accessible"
            return 0
        else
            log_error "API responded but status is: $status"
            return 1
        fi
    else
        log_error "Cannot connect to API at $APP_URL"
        echo "Make sure your app is running and accessible"
        return 1
    fi
}

# Usage function
show_usage() {
    echo "Word Filter App - Add Words Script"
    echo ""
    echo "Usage:"
    echo "  $0 [options] [word1] [word2] [word3]..."
    echo ""
    echo "Options:"
    echo "  -c, --check WORD     Check if word exists"
    echo "  -s, --stats          Show word statistics"
    echo "  -t, --test           Test API connection"
    echo "  -b, --batch          Force batch mode (even for single word)"
    echo "  -h, --help           Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 amazing fantastic incredible     # Add multiple words"
    echo "  $0 --check amazing                  # Check if 'amazing' exists"
    echo "  $0 --stats                          # Show statistics"
    echo "  $0 --batch word1 word2              # Force batch mode"
    echo ""
    echo "Environment Variables:"
    echo "  WORD_FILTER_URL     API URL (default: http://localhost:8001)"
    echo ""
}

# Main script logic
main() {
    if [ $# -eq 0 ]; then
        show_usage
        exit 0
    fi
    
    # Test connection first
    if ! test_connection; then
        exit 1
    fi
    
    case "$1" in
        -h|--help)
            show_usage
            ;;
        -t|--test)
            log_success "Connection test completed"
            ;;
        -s|--stats)
            show_stats
            ;;
        -c|--check)
            if [ -z "$2" ]; then
                log_error "Please provide a word to check"
                exit 1
            fi
            check_word "$2"
            ;;
        -b|--batch)
            shift
            if [ $# -eq 0 ]; then
                log_error "Please provide words to add"
                exit 1
            fi
            add_batch_words "$@"
            ;;
        *)
            # Add words (single or batch)
            if [ $# -eq 1 ]; then
                add_single_word "$1"
            else
                add_batch_words "$@"
            fi
            
            # Show updated stats
            echo ""
            show_stats
            ;;
    esac
}

# Run main function
main "$@"
