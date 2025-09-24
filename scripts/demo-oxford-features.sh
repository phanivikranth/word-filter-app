#!/bin/bash

# Oxford Dictionary Integration Demo Script
# This script demonstrates all the Oxford validation features

# Configuration
APP_URL="${WORD_FILTER_URL:-http://localhost:8001}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo -e "${PURPLE}"
    echo "=================================="
    echo "$1"
    echo "=================================="
    echo -e "${NC}"
}

print_step() {
    echo -e "${CYAN}Step $1:${NC} $2"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

wait_for_user() {
    echo -e "${YELLOW}Press Enter to continue...${NC}"
    read
}

# Demo data
good_words=("amazing" "fantastic" "incredible" "awesome" "brilliant" "wonderful")
bad_words=("xyz123" "aaaaa" "qwerty" "asdfgh" "zzzzz" "abcdef")
questionable_words=("covid" "brexit" "iphone" "facebook" "google")

demo_word_validation() {
    print_header "DEMO 1: Single Word Validation"
    
    print_step "1.1" "Testing valid words"
    for word in "${good_words[@]:0:3}"; do
        print_info "Validating: $word"
        curl -s -X POST "$APP_URL/words/validate" \
             -H "Content-Type: application/json" \
             -d "{\"word\":\"$word\"}" | python -c "
import sys, json
data = json.load(sys.stdin)
validation = data.get('oxford_validation', {})
if validation.get('is_valid'):
    print('✅ VALID: {} - {}'.format(validation['word'], validation.get('reason', 'No reason')))
else:
    print('❌ INVALID: {} - {}'.format(validation['word'], validation.get('reason', 'No reason')))
"
        sleep 1
    done
    
    echo ""
    print_step "1.2" "Testing invalid words"
    for word in "${bad_words[@]:0:3}"; do
        print_info "Validating: $word"
        curl -s -X POST "$APP_URL/words/validate" \
             -H "Content-Type: application/json" \
             -d "{\"word\":\"$word\"}" | python -c "
import sys, json
data = json.load(sys.stdin)
validation = data.get('oxford_validation', {})
if validation.get('is_valid'):
    print('✅ VALID: {} - {}'.format(validation['word'], validation.get('reason', 'No reason')))
else:
    print('❌ INVALID: {} - {}'.format(validation['word'], validation.get('reason', 'No reason')))
"
        sleep 1
    done
    
    wait_for_user
}

demo_validated_addition() {
    print_header "DEMO 2: Adding Words with Validation"
    
    print_step "2.1" "Adding valid words (should succeed)"
    for word in "${good_words[@]:0:2}"; do
        print_info "Adding with validation: $word"
        response=$(curl -s -X POST "$APP_URL/words/add-validated" \
                       -H "Content-Type: application/json" \
                       -d "{\"word\":\"$word\"}")
        
        if echo "$response" | grep -q '"success":true'; then
            print_success "Added: $word"
        else
            print_warning "Failed to add: $word"
            echo "$response" | python -m json.tool | head -3
        fi
        sleep 1
    done
    
    echo ""
    print_step "2.2" "Trying to add invalid words (should fail)"
    for word in "${bad_words[@]:0:2}"; do
        print_info "Adding with validation: $word"
        response=$(curl -s -X POST "$APP_URL/words/add-validated" \
                       -H "Content-Type: application/json" \
                       -d "{\"word\":\"$word\"}")
        
        if echo "$response" | grep -q '"success":true'; then
            print_warning "Unexpected success: $word"
        else
            print_success "Correctly rejected: $word"
            echo "$response" | python -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print('   Reason: {}'.format(data.get('detail', 'Unknown error')))
except:
    print('   Could not parse response')
"
        fi
        sleep 1
    done
    
    echo ""
    print_step "2.3" "Adding words without validation (bypass Oxford)"
    print_info "Adding 'customword' without validation"
    curl -s -X POST "$APP_URL/words/add-validated" \
         -H "Content-Type: application/json" \
         -d '{"word":"customword","skip_oxford":true}' | python -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('success'):
        print('✅ Added without validation: customword')
    else:
        print('❌ Failed to add: customword')
except:
    print('❌ Error parsing response')
"
    
    wait_for_user
}

demo_word_removal() {
    print_header "DEMO 3: Word Removal"
    
    print_step "3.1" "Removing a word"
    print_info "Removing 'customword' that we added earlier"
    response=$(curl -s -X POST "$APP_URL/words/remove" \
                   -H "Content-Type: application/json" \
                   -d '{"word":"customword"}')
    
    if echo "$response" | grep -q '"success":true'; then
        print_success "Removed: customword"
    else
        print_warning "Failed to remove: customword"
    fi
    
    echo ""
    print_step "3.2" "Batch removal"
    print_info "Removing multiple words at once"
    curl -s -X POST "$APP_URL/words/remove-batch" \
         -H "Content-Type: application/json" \
         -d '{"words":["nonexistentword1","nonexistentword2","testword"]}' | python -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print('Removal summary:')
    print('  Submitted: {}'.format(data.get('total_submitted', 0)))
    print('  Removed: {}'.format(data.get('removed_count', 0)))
    print('  Not Found: {}'.format(data.get('not_found_count', 0)))
except:
    print('❌ Error parsing response')
"
    
    wait_for_user
}

demo_collection_validation() {
    print_header "DEMO 4: Full Collection Validation"
    
    print_step "4.1" "Adding some test words (mix of good and bad)"
    print_info "Adding test words to demonstrate collection validation..."
    
    # Add some good words
    for word in "${good_words[@]:3:2}"; do
        curl -s -X POST "$APP_URL/words/add" \
             -H "Content-Type: application/json" \
             -d "{\"word\":\"$word\"}" > /dev/null
    done
    
    # Add some bad words (skip validation)
    for word in "${bad_words[@]:3:2}"; do
        curl -s -X POST "$APP_URL/words/add-validated" \
             -H "Content-Type: application/json" \
             -d "{\"word\":\"$word\",\"skip_oxford\":true}" > /dev/null
    done
    
    print_success "Added test words"
    
    echo ""
    print_step "4.2" "Validating entire collection"
    print_warning "This may take a minute depending on collection size..."
    
    response=$(curl -s -X POST "$APP_URL/words/validate-collection" \
                   -H "Content-Type: application/json")
    
    echo "$response" | python -c "
import sys, json
try:
    data = json.load(sys.stdin)
    summary = data.get('validation_summary', {})
    print('')
    print('📊 Validation Results:')
    print('   Total Words: {}'.format(summary.get('total_words', 0)))
    print('   Valid Words: {}'.format(summary.get('valid_words', 0)))
    print('   Invalid Words: {}'.format(summary.get('invalid_words', 0)))
    print('   Validity: {}%'.format(summary.get('validity_percentage', 0)))
    
    invalid_words = data.get('invalid_words', [])
    if invalid_words:
        print('')
        print('❌ Invalid words found:')
        for word in invalid_words[:10]:  # Show first 10
            print('   - {}'.format(word))
        if len(invalid_words) > 10:
            print('   ... and {} more'.format(len(invalid_words) - 10))
except Exception as e:
    print('❌ Error parsing response: {}'.format(e))
"
    
    wait_for_user
}

demo_cleanup() {
    print_header "DEMO 5: Automatic Cleanup"
    
    print_step "5.1" "Finding invalid words (without removal)"
    response=$(curl -s -X POST "$APP_URL/words/cleanup" \
                   -H "Content-Type: application/json" \
                   -d '{"auto_remove":false}')
    
    echo "$response" | python -c "
import sys, json
try:
    data = json.load(sys.stdin)
    summary = data.get('cleanup_summary', {})
    print('🔍 Cleanup Analysis:')
    print('   Invalid Words Found: {}'.format(summary.get('found_invalid', 0)))
    print('   Action Taken: {}'.format(summary.get('action_taken', 'None')))
    
    invalid_words = data.get('invalid_words', [])
    if invalid_words:
        print('   Words that would be removed:')
        for word in invalid_words[:5]:
            print('     - {}'.format(word))
except:
    print('❌ Error parsing response')
"
    
    echo ""
    print_step "5.2" "Automatic removal of invalid words"
    print_warning "This will actually remove invalid words!"
    print_info "Removing invalid words automatically..."
    
    response=$(curl -s -X POST "$APP_URL/words/cleanup" \
                   -H "Content-Type: application/json" \
                   -d '{"auto_remove":true}')
    
    echo "$response" | python -c "
import sys, json
try:
    data = json.load(sys.stdin)
    summary = data.get('cleanup_summary', {})
    print('🧹 Cleanup Results:')
    print('   Invalid Words Found: {}'.format(summary.get('found_invalid', 0)))
    print('   Words Removed: {}'.format(summary.get('removed_count', 0)))
    print('   Total Words Remaining: {}'.format(data.get('total_words', 0)))
    print('   Action: {}'.format(summary.get('action_taken', 'None')))
except:
    print('❌ Error parsing response')
"
    
    wait_for_user
}

demo_statistics() {
    print_header "DEMO 6: Statistics and Monitoring"
    
    print_step "6.1" "Collection Statistics"
    curl -s "$APP_URL/words/stats" | python -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print('📊 Word Collection Stats:')
    print('   Total Words: {}'.format(data.get('total_words', 0)))
    print('   Average Length: {}'.format(data.get('avg_length', 0)))
    print('   Length Range: {} - {}'.format(data.get('min_length', 0), data.get('max_length', 0)))
    print('   S3 Connected: {}'.format(data.get('s3_connected', False)))
except:
    print('❌ Error parsing response')
"
    
    echo ""
    print_step "6.2" "Oxford Cache Statistics"
    curl -s "$APP_URL/words/oxford-stats" | python -c "
import sys, json
try:
    data = json.load(sys.stdin)
    cache = data.get('oxford_cache', {})
    print('📈 Oxford Cache Stats:')
    print('   Cached Words: {}'.format(cache.get('cached_words', 0)))
    print('   Cache Hit Rate: {}'.format(cache.get('cache_hit_rate', 'Not tracked')))
    print('   Total Requests: {}'.format(cache.get('total_requests', 'Not tracked')))
except:
    print('❌ Error parsing response')
"
    
    echo ""
    print_step "6.3" "Health Check"
    curl -s "$APP_URL/health" | python -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print('🏥 Health Status:')
    print('   Status: {}'.format(data.get('status', 'unknown')))
    print('   Word Count: {}'.format(data.get('word_count', 0)))
    print('   S3 Connected: {}'.format(data.get('s3_connected', False)))
except:
    print('❌ Error parsing response')
"
    
    wait_for_user
}

# Main demo execution
main() {
    print_header "🎓 Oxford Dictionary Integration Demo"
    echo "This demo will show you all the Oxford validation features"
    echo "App URL: $APP_URL"
    echo ""
    
    # Test connection
    if ! curl -s "$APP_URL/health" > /dev/null; then
        echo -e "${RED}❌ Cannot connect to $APP_URL${NC}"
        echo "Make sure your app is running and accessible"
        exit 1
    fi
    
    print_success "Connected to API successfully"
    echo ""
    
    print_info "This demo will:"
    echo "1. Validate individual words"
    echo "2. Add words with validation"
    echo "3. Remove words"
    echo "4. Validate entire collection"
    echo "5. Clean up invalid words"
    echo "6. Show statistics"
    echo ""
    
    wait_for_user
    
    # Run all demos
    demo_word_validation
    demo_validated_addition
    demo_word_removal
    demo_collection_validation
    demo_cleanup
    demo_statistics
    
    print_header "🎉 Demo Complete!"
    print_success "All Oxford Dictionary features demonstrated successfully"
    echo ""
    print_info "Key takeaways:"
    echo "• Oxford validation ensures only dictionary words are added"
    echo "• Invalid words can be automatically detected and removed"
    echo "• The system caches results to improve performance"
    echo "• Detailed statistics help monitor word quality"
    echo ""
    print_info "Next steps:"
    echo "• Use './scripts/oxford-validation.sh' for daily operations"
    echo "• Set up automated cleanup with cron jobs"
    echo "• Monitor collection quality with validation reports"
    echo ""
    print_success "Your Word Filter App now has professional word validation! 🚀"
}

# Run the demo
main "$@"
