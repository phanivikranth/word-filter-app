#!/bin/bash

# Oxford Dictionary Validation and Cleanup Script
# This script helps validate and clean up words using Oxford Dictionary API

# Configuration
APP_URL="${WORD_FILTER_URL:-http://localhost:8001}"
TIMEOUT=30

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
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

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
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

# Function to validate a single word
validate_single_word() {
    local word=$1
    log_info "Validating word with Oxford Dictionary: $word"
    
    response=$(curl -s -X POST "$APP_URL/words/validate" \
        -H "Content-Type: application/json" \
        -d "{\"word\":\"$word\"}" \
        --connect-timeout $TIMEOUT)
    
    if [ $? -eq 0 ]; then
        is_valid=$(echo "$response" | grep -o '"is_valid":[^,]*' | cut -d':' -f2)
        reason=$(echo "$response" | grep -o '"reason":"[^"]*"' | cut -d':' -f2 | tr -d '"')
        
        if [ "$is_valid" = "true" ]; then
            log_success "Valid: $word - $reason"
        else
            log_warning "Invalid: $word - $reason"
        fi
        
        echo "$response" | python -m json.tool
    else
        log_error "Failed to validate word: $word"
    fi
}

# Function to add word with Oxford validation
add_validated_word() {
    local word=$1
    local skip_oxford=${2:-false}
    
    log_info "Adding word with Oxford validation: $word"
    
    response=$(curl -s -w "\n%{http_code}" -X POST "$APP_URL/words/add-validated" \
        -H "Content-Type: application/json" \
        -d "{\"word\":\"$word\", \"skip_oxford\":$skip_oxford}" \
        --connect-timeout $TIMEOUT)
    
    http_code=$(echo "$response" | tail -n1)
    response_body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" -eq 200 ]; then
        was_new=$(echo "$response_body" | grep -o '"was_new":[^,]*' | cut -d':' -f2)
        if [ "$was_new" = "true" ]; then
            log_success "Added validated word: $word"
        else
            log_info "Word already exists: $word"
        fi
    else
        log_error "Failed to add word: $word (HTTP $http_code)"
        echo "$response_body"
    fi
}

# Function to remove a word
remove_word() {
    local word=$1
    log_info "Removing word: $word"
    
    response=$(curl -s -w "\n%{http_code}" -X POST "$APP_URL/words/remove" \
        -H "Content-Type: application/json" \
        -d "{\"word\":\"$word\"}" \
        --connect-timeout $TIMEOUT)
    
    http_code=$(echo "$response" | tail -n1)
    response_body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" -eq 200 ]; then
        log_success "Removed word: $word"
    else
        log_error "Failed to remove word: $word (HTTP $http_code)"
        echo "$response_body"
    fi
}

# Function to validate entire collection
validate_collection() {
    log_info "Starting validation of entire word collection..."
    log_warning "This may take several minutes depending on collection size"
    
    response=$(curl -s -X POST "$APP_URL/words/validate-collection" \
        -H "Content-Type: application/json" \
        --connect-timeout 300)  # Longer timeout for collection validation
    
    if [ $? -eq 0 ]; then
        total_words=$(echo "$response" | grep -o '"total_words":[^,]*' | cut -d':' -f2)
        valid_words=$(echo "$response" | grep -o '"valid_words":[^,]*' | cut -d':' -f2)
        invalid_words=$(echo "$response" | grep -o '"invalid_words":[^,]*' | cut -d':' -f2)
        validity_percentage=$(echo "$response" | grep -o '"validity_percentage":[^,]*' | cut -d':' -f2)
        
        echo ""
        echo "📊 Validation Results:"
        echo "   Total Words: $total_words"
        echo "   Valid Words: $valid_words"
        echo "   Invalid Words: $invalid_words"
        echo "   Validity: $validity_percentage%"
        echo ""
        
        if [ "$invalid_words" -gt 0 ]; then
            log_warning "Found $invalid_words invalid words"
            echo "Invalid words list:"
            echo "$response" | grep -o '"invalid_words":\[[^]]*\]' | sed 's/"invalid_words"://g' | sed 's/\[//g' | sed 's/\]//g' | tr ',' '\n' | sed 's/"//g'
            echo ""
            log_info "Use 'oxford-validation.sh cleanup' to remove invalid words"
        else
            log_success "All words in collection are valid!"
        fi
    else
        log_error "Failed to validate collection"
    fi
}

# Function to cleanup invalid words
cleanup_invalid_words() {
    local auto_remove=${1:-false}
    
    if [ "$auto_remove" = "true" ]; then
        log_warning "DANGER: This will automatically remove invalid words!"
        read -p "Are you sure you want to continue? (y/N): " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Cleanup cancelled"
            return
        fi
    fi
    
    log_info "Starting cleanup of invalid words..."
    
    response=$(curl -s -X POST "$APP_URL/words/cleanup" \
        -H "Content-Type: application/json" \
        -d "{\"auto_remove\":$auto_remove}" \
        --connect-timeout 300)
    
    if [ $? -eq 0 ]; then
        found_invalid=$(echo "$response" | grep -o '"found_invalid":[^,]*' | cut -d':' -f2)
        removed_count=$(echo "$response" | grep -o '"removed_count":[^,]*' | cut -d':' -f2)
        action_taken=$(echo "$response" | grep -o '"action_taken":"[^"]*"' | cut -d':' -f2 | tr -d '"')
        
        echo ""
        echo "🧹 Cleanup Results:"
        echo "   Found Invalid: $found_invalid"
        echo "   Removed: $removed_count"
        echo "   Action: $action_taken"
        echo ""
        
        if [ "$found_invalid" -gt 0 ] && [ "$auto_remove" = "false" ]; then
            echo "Invalid words found:"
            echo "$response" | grep -o '"invalid_words":\[[^]]*\]' | sed 's/"invalid_words"://g' | sed 's/\[//g' | sed 's/\]//g' | tr ',' '\n' | sed 's/"//g'
            echo ""
            log_info "Run 'oxford-validation.sh cleanup-auto' to remove these words"
        fi
    else
        log_error "Failed to cleanup invalid words"
    fi
}

# Function to show Oxford cache stats
show_oxford_stats() {
    log_info "Getting Oxford Dictionary cache statistics..."
    
    response=$(curl -s "$APP_URL/words/oxford-stats" --connect-timeout $TIMEOUT)
    
    if [ $? -eq 0 ]; then
        cached_words=$(echo "$response" | grep -o '"cached_words":[^,]*' | cut -d':' -f2)
        
        echo ""
        echo "📈 Oxford Cache Statistics:"
        echo "   Cached Words: $cached_words"
        echo ""
    else
        log_error "Failed to get Oxford statistics"
    fi
}

# Function to show word statistics
show_word_stats() {
    log_info "Getting word collection statistics..."
    
    response=$(curl -s "$APP_URL/words/stats" --connect-timeout $TIMEOUT)
    
    if [ $? -eq 0 ]; then
        total_words=$(echo "$response" | grep -o '"total_words":[^,]*' | cut -d':' -f2)
        avg_length=$(echo "$response" | grep -o '"avg_length":[^,]*' | cut -d':' -f2)
        min_length=$(echo "$response" | grep -o '"min_length":[^,]*' | cut -d':' -f2)
        max_length=$(echo "$response" | grep -o '"max_length":[^,]*' | cut -d':' -f2)
        s3_connected=$(echo "$response" | grep -o '"s3_connected":[^,]*' | cut -d':' -f2)
        
        echo ""
        echo "📊 Word Collection Statistics:"
        echo "   Total Words: $total_words"
        echo "   Length Range: $min_length - $max_length"
        echo "   Average Length: $avg_length"
        echo "   S3 Connected: $s3_connected"
        echo ""
    else
        log_error "Failed to get word statistics"
    fi
}

# Usage function
show_usage() {
    echo "Oxford Dictionary Validation & Cleanup Tool"
    echo ""
    echo "Usage:"
    echo "  $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  validate WORD            Validate a single word with Oxford Dictionary"
    echo "  add WORD                 Add word with Oxford validation"
    echo "  add-skip WORD           Add word without Oxford validation"
    echo "  remove WORD             Remove a word from collection"
    echo "  validate-collection     Validate entire word collection"
    echo "  cleanup                 Find invalid words (don't remove)"
    echo "  cleanup-auto            Find and automatically remove invalid words"
    echo "  stats                   Show word collection statistics"
    echo "  oxford-stats           Show Oxford cache statistics"
    echo "  test                   Test API connection"
    echo ""
    echo "Examples:"
    echo "  $0 validate amazing"
    echo "  $0 add fantastic"
    echo "  $0 validate-collection"
    echo "  $0 cleanup-auto"
    echo ""
    echo "Environment Variables:"
    echo "  WORD_FILTER_URL         API URL (default: http://localhost:8001)"
    echo ""
}

# Main script logic
main() {
    if [ $# -eq 0 ]; then
        show_usage
        exit 0
    fi
    
    # Test connection first for all commands except help
    case "$1" in
        -h|--help|help)
            show_usage
            exit 0
            ;;
        *)
            if ! test_connection; then
                exit 1
            fi
            ;;
    esac
    
    case "$1" in
        validate)
            if [ -z "$2" ]; then
                log_error "Please provide a word to validate"
                exit 1
            fi
            validate_single_word "$2"
            ;;
        add)
            if [ -z "$2" ]; then
                log_error "Please provide a word to add"
                exit 1
            fi
            add_validated_word "$2" false
            ;;
        add-skip)
            if [ -z "$2" ]; then
                log_error "Please provide a word to add"
                exit 1
            fi
            add_validated_word "$2" true
            ;;
        remove)
            if [ -z "$2" ]; then
                log_error "Please provide a word to remove"
                exit 1
            fi
            remove_word "$2"
            ;;
        validate-collection)
            validate_collection
            ;;
        cleanup)
            cleanup_invalid_words false
            ;;
        cleanup-auto)
            cleanup_invalid_words true
            ;;
        stats)
            show_word_stats
            ;;
        oxford-stats)
            show_oxford_stats
            ;;
        test)
            log_success "Connection test completed"
            ;;
        *)
            log_error "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
