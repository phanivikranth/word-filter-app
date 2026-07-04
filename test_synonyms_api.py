#!/usr/bin/env python3
"""Quick test script to verify synonym APIs are working"""

import requests
import json

def test_synonym_endpoint(word="happy"):
    """Test the /words/validate endpoint with synonyms"""
    url = "http://localhost:8000/words/validate"
    
    print(f"\n{'='*60}")
    print(f"Testing Synonym Integration for word: '{word}'")
    print(f"{'='*60}\n")
    
    try:
        response = requests.post(
            url,
            json={"word": word},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if 'oxford_validation' in data:
                oxford = data['oxford_validation']
                
                print(f"\n✓ Word: {oxford.get('word', 'N/A')}")
                print(f"✓ Valid: {oxford.get('is_valid', False)}")
                print(f"✓ Definitions: {len(oxford.get('definitions', []))}")
                print(f"✓ Examples: {len(oxford.get('examples', []))}")
                
                # Check synonyms
                synonyms = oxford.get('synonyms', [])
                print(f"\n{'='*60}")
                print(f"SYNONYMS ({len(synonyms)} found):")
                print(f"{'='*60}")
                
                if synonyms:
                    for i, syn in enumerate(synonyms, 1):
                        print(f"  {i:2d}. {syn}")
                    
                    # Check sources
                    if 'synonym_sources' in oxford:
                        sources = oxford['synonym_sources']
                        print(f"\n{'='*60}")
                        print("SOURCES:")
                        print(f"{'='*60}")
                        print(f"  DataMuse:        {sources.get('datamuse', 0)} synonyms")
                        print(f"  Merriam-Webster: {sources.get('merriam_webster', 0)} synonyms")
                        print(f"  Oxford:          {sources.get('oxford', 0)} synonyms")
                else:
                    print("  ❌ No synonyms found!")
                
                print(f"\n{'='*60}")
                print(f"Reason: {oxford.get('reason', 'N/A')}")
                print(f"{'='*60}\n")
                
                return True
            else:
                print("❌ No oxford_validation in response")
                print(json.dumps(data, indent=2))
                return False
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(response.text)
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to backend at http://localhost:8000")
        print("   Make sure the backend is running!")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


if __name__ == "__main__":
    # Test multiple words
    test_words = ["happy", "good", "beautiful", "sad"]
    
    for word in test_words:
        success = test_synonym_endpoint(word)
        if not success:
            print(f"\n⚠️  Test failed for '{word}'\n")
            break
        print("\n" + "="*60 + "\n")
    
    print("\n✅ All tests completed!")
