"""
Puzzle Solver Utilities
Provides advanced wildcard, regex, and anagram matching algorithms.
"""
import re
from typing import List, Dict, Set

VOWELS = set('aeiou')

def match_pattern(word: str, pattern: str) -> bool:
    """
    Check if a word matches a pattern.
    - '?' matches any letter.
    - '@' matches a vowel (a, e, i, o, u).
    - '#' matches a consonant (any letter that is not a, e, i, o, u).
    - Other characters match case-insensitively.
    """
    if len(word) != len(pattern):
        return False
        
    for p_char, w_char in zip(pattern.lower(), word.lower()):
        if p_char == '?':
            continue
        elif p_char == '@':
            if w_char not in VOWELS:
                return False
        elif p_char == '#':
            if w_char in VOWELS or not w_char.isalpha():
                return False
        elif p_char != w_char:
            return False
            
    return True

def match_regex(word: str, regex_pattern: str) -> bool:
    """
    Check if a word matches a regular expression pattern.
    Matches are case-insensitive and match the entire word.
    """
    try:
        # Wrap pattern to match the whole word if not already done
        clean_pattern = regex_pattern
        if not clean_pattern.startswith('^'):
            clean_pattern = '^' + clean_pattern
        if not clean_pattern.endswith('$'):
            clean_pattern = clean_pattern + '$'
            
        pattern = re.compile(clean_pattern, re.IGNORECASE)
        return bool(pattern.match(word))
    except Exception:
        # Return False if regex is invalid
        return False

def match_anagram(word: str, letters: str, exact: bool = False) -> bool:
    """
    Check if a word can be formed from a pool of letters.
    - exact=True: word must use all letters exactly once.
    - exact=False: word can use a subset of letters.
    """
    word_len = len(word)
    letters_len = len(letters)
    
    if exact and word_len != letters_len:
        return False
    if word_len > letters_len:
        return False
        
    # Count occurrences
    letter_pool = {}
    for char in letters.lower():
        if char.isalpha():
            letter_pool[char] = letter_pool.get(char, 0) + 1
        
    for char in word.lower():
        if not char.isalpha():
            return False
        if char not in letter_pool or letter_pool[char] <= 0:
            return False
        letter_pool[char] -= 1
        
    return True
