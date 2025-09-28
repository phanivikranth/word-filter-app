#!/usr/bin/env python3
"""
Word List Merger and Deduplicator
Combines multiple word lists, removes duplicates, and creates a clean merged collection.
"""

import re
from pathlib import Path
from typing import Set, List

def load_words_from_file(filepath: str) -> Set[str]:
    """Load words from a text file, one word per line."""
    words = set()
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
            for line in file:
                word = line.strip().lower()
                # Only include valid words (letters only, length 1-20)
                if word and re.match(r'^[a-z]{1,20}$', word):
                    words.add(word)
        print(f"[OK] Loaded {len(words):,} valid words from {filepath}")
    except FileNotFoundError:
        print(f"[ERROR] File not found: {filepath}")
    except Exception as e:
        print(f"[ERROR] Error loading {filepath}: {e}")
    
    return words

def save_words_to_file(words: Set[str], filepath: str) -> None:
    """Save words to a text file, sorted alphabetically."""
    sorted_words = sorted(words)
    try:
        with open(filepath, 'w', encoding='utf-8') as file:
            for word in sorted_words:
                file.write(f"{word}\n")
        print(f"[OK] Saved {len(words):,} words to {filepath}")
    except Exception as e:
        print(f"[ERROR] Error saving to {filepath}: {e}")

def main():
    print("Starting word list merge process...\n")
    
    # Define file paths
    current_words_file = "words.txt"
    dwyl_words_file = "english-words-466k.txt"
    google_words_file = "google-10k-common.txt"
    output_file = "words_merged.txt"
    backup_file = "words_backup.txt"
    
    # Create backup of current words
    print("Creating backup of current word list...")
    current_words = load_words_from_file(current_words_file)
    save_words_to_file(current_words, backup_file)
    
    # Load all word collections
    print("Loading word collections...")
    dwyl_words = load_words_from_file(dwyl_words_file)
    google_words = load_words_from_file(google_words_file)
    
    # Merge all collections
    print("\nMerging word collections...")
    merged_words = current_words.union(dwyl_words).union(google_words)
    
    # Statistics
    print(f"""
**Merge Statistics:**
   - Original collection: {len(current_words):,} words
   - dwyl/english-words: {len(dwyl_words):,} words  
   - Google 10k common: {len(google_words):,} words
   - Total unique words: {len(merged_words):,} words
   - New words added: {len(merged_words) - len(current_words):,} words
    """)
    
    # Save merged collection
    print("Saving merged word collection...")
    save_words_to_file(merged_words, output_file)
    
    # Analyze word length distribution
    length_stats = {}
    for word in merged_words:
        length = len(word)
        length_stats[length] = length_stats.get(length, 0) + 1
    
    print(f"""
**Word Length Distribution (Top 10):**""")
    
    for length in sorted(length_stats.keys())[:10]:
        count = length_stats[length]
        percentage = (count / len(merged_words)) * 100
        print(f"   - {length:2d} letters: {count:6,} words ({percentage:5.1f}%)")
    
    print(f"\n[SUCCESS] Word merge completed successfully!")
    print(f"   - Merged file: {output_file}")
    print(f"   - Backup file: {backup_file}")
    print(f"   - Ready to replace words.txt with {output_file}")

if __name__ == "__main__":
    main()
