import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup } from '@angular/forms';
import { WordService, BasicSearchResult, AddWordResponse } from './services/word.service';
import { WordFilter, WordStats } from './models/word.model';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  title = 'Word Filter App';
  
  // Search mode properties
  searchMode: 'basic' | 'advanced' = 'basic'; // Default to basic search
  
  // Basic search properties
  searchWord = '';
  searchResult: BasicSearchResult | null = null;
  isSearching = false;
  searchError = '';

  // Advanced filter properties
  filterForm: FormGroup;
  words: string[] = [];
  wordStats: WordStats | null = null;
  loading = false;
  error = '';

  // Interactive tab properties
  interactiveWordLength: number | null = null;
  letterBoxes: string[] = [];
  interactiveWords: string[] = [];
  interactiveLoading = false;
  interactiveError = '';
  
  // Puzzle solver properties
  puzzleLength: number = 5;
  puzzlePattern: string = '';

  // Stats panel properties
  statsPanelExpanded = false;

  // Search toggle properties
  searchToggleExpanded = false;

  // Puzzle toggle properties
  puzzleToggleExpanded = false;
  puzzlePanelExpanded = false;

  constructor(
    private fb: FormBuilder,
    private wordService: WordService
  ) {
    this.filterForm = this.fb.group({
      contains: [''],
      starts_with: [''],
      ends_with: [''],
      min_length: [''],
      max_length: [''],
      exact_length: [''],
      limit: [100]
    });
  }

  ngOnInit() {
    this.loadWordStats();
    this.searchWords(); // Load initial words
  }

  loadWordStats() {
    this.wordService.getWordStats().subscribe({
      next: (stats) => {
        this.wordStats = stats;
      },
      error: (error) => {
        console.error('Error loading word stats:', error);
        this.error = 'Failed to load word statistics';
      }
    });
  }

  searchWords() {
    this.loading = true;
    this.error = '';
    
    const filterValues = this.filterForm.value;
    const filter: WordFilter = {};

    // Only add non-empty values to the filter
    Object.keys(filterValues).forEach(key => {
      const value = filterValues[key];
      if (value !== null && value !== '' && value !== undefined) {
        filter[key as keyof WordFilter] = value;
      }
    });

    this.wordService.getFilteredWords(filter).subscribe({
      next: (words) => {
        this.words = words;
        this.loading = false;
      },
      error: (error) => {
        console.error('Error searching words:', error);
        this.error = 'Failed to search words. Make sure the backend is running.';
        this.loading = false;
      }
    });
  }

  clearFilters() {
    this.filterForm.reset();
    this.filterForm.patchValue({ limit: 100 });
    this.searchWords();
  }

  onFilterChange() {
    // Auto-search when filters change
    this.searchWords();
  }


  // Interactive tab methods
  onWordLengthChange() {
    if (this.interactiveWordLength && this.interactiveWordLength > 0) {
      this.letterBoxes = new Array(this.interactiveWordLength).fill('');
      this.interactiveWords = [];
      this.interactiveError = '';
    } else {
      this.letterBoxes = [];
    }
  }

  // Puzzle solver methods
  onPuzzleLengthChange() {
    if (this.puzzleLength && this.puzzleLength > 0) {
      this.letterBoxes = new Array(this.puzzleLength).fill('');
      this.interactiveWords = [];
      this.interactiveError = '';
    } else {
      this.letterBoxes = [];
    }
  }

  onPuzzlePatternChange() {
    // Update letter boxes based on pattern
    if (this.puzzlePattern && this.puzzleLength) {
      this.letterBoxes = this.puzzlePattern.split('').slice(0, this.puzzleLength);
      // Pad with empty strings if pattern is shorter than length
      while (this.letterBoxes.length < this.puzzleLength) {
        this.letterBoxes.push('');
      }
    }
  }

  getPatternPlaceholder(): string {
    if (this.puzzleLength && this.puzzleLength > 0) {
      return '?'.repeat(this.puzzleLength);
    }
    return '?????';
  }


  updateLetter(index: number, event: any) {
    const inputValue = event.target.value;
    
    // Clean the input: only letters, single character, lowercase for backend
    let cleanValue = inputValue.replace(/[^a-zA-Z]/g, '').toLowerCase();
    
    // Ensure only one character
    if (cleanValue.length > 1) {
      cleanValue = cleanValue.charAt(0);
    }
    
    // Update the specific index in the array
    this.letterBoxes[index] = cleanValue;
    
    // Force the input to show the correct value immediately
    event.target.value = cleanValue.toUpperCase();
  }

  findMatchingWords() {
    if (!this.interactiveWordLength || this.letterBoxes.length === 0) {
      this.interactiveError = 'Please enter a word length first.';
      return;
    }

    this.interactiveLoading = true;
    this.interactiveError = '';

    // Create pattern for the interactive search
    const pattern = this.letterBoxes.map(letter => letter || '?').join('');
    
    this.wordService.getInteractiveWords(this.interactiveWordLength, pattern).subscribe({
      next: (words) => {
        this.interactiveWords = words;
        this.interactiveLoading = false;
        if (words.length === 0) {
          this.interactiveError = 'No words found matching your pattern.';
        }
      },
      error: (error) => {
        console.error('Error finding interactive words:', error);
        this.interactiveError = 'Failed to find words. Make sure the backend is running.';
        this.interactiveLoading = false;
      }
    });
  }

  clearInteractive() {
    this.interactiveWordLength = null;
    this.puzzleLength = 5;
    this.puzzlePattern = '';
    this.letterBoxes = [];
    this.interactiveWords = [];
    this.interactiveError = '';
    this.interactiveLoading = false;
  }

  trackByIndex(index: number, item: any): number {
    return index;
  }

  // New tracking method for words
  trackByWord(index: number, word: string): string {
    return word;
  }

  // Highlight position functionality for better UX
  highlightPosition(index: number) {
    // Add visual highlighting logic if needed
    console.log(`Highlighting position ${index + 1}`);
  }

  unhighlightPosition(index: number) {
    // Remove visual highlighting logic if needed
    console.log(`Unhighlighting position ${index + 1}`);
  }

  // Random example functionality
  randomizePattern() {
    if (!this.puzzleLength || this.puzzleLength <= 0) {
      this.puzzleLength = 5;
    }

    // Generate a random pattern with some known letters
    const letters = 'abcdefghijklmnopqrstuvwxyz';
    const pattern = Array.from({ length: this.puzzleLength }, (_, i) => {
      // 30% chance of having a known letter, 70% chance of being unknown
      return Math.random() < 0.3 ? letters[Math.floor(Math.random() * letters.length)] : '?';
    }).join('');

    this.puzzlePattern = pattern;
    this.onPuzzlePatternChange();
    this.interactiveError = '';
  }

  copyWordToClipboard(word: string) {
    navigator.clipboard.writeText(word).then(() => {
      console.log('Word copied to clipboard:', word);
      // You could add a toast notification here
    }).catch(() => {
      console.error('Failed to copy word to clipboard');
    });
  }

  exploreWord(word: string) {
    // Switch to basic search mode and search for the word
    this.searchMode = 'basic';
    this.searchWord = word;
    this.searchWordBasic();
  }

  playPronunciation(audioUrl: string) {
    if (audioUrl) {
      const audio = new Audio(audioUrl);
      audio.play().catch(error => {
        console.error('Error playing pronunciation:', error);
      });
    }
  }

  // Stats panel methods
  toggleStatsPanel() {
    this.statsPanelExpanded = !this.statsPanelExpanded;
  }

  expandStatsPanel() {
    this.statsPanelExpanded = true;
  }

  collapseStatsPanel() {
    this.statsPanelExpanded = false;
  }

  // Basic search methods
  onSearchInput() {
    // Clear previous results when user types
    if (this.searchResult) {
      this.searchResult = null;
    }
  }

  searchWordBasic() {
    if (!this.searchWord || this.searchWord.trim() === '') {
      return;
    }

    this.isSearching = true;
    this.searchError = '';
    this.searchResult = null;

    this.wordService.searchBasicWord(this.searchWord.trim()).subscribe({
      next: (result) => {
        this.searchResult = result;
        this.isSearching = false;
      },
      error: (error) => {
        this.searchError = 'Error searching for word: ' + error.message;
        this.isSearching = false;
      }
    });
  }

  addWordToCollection(word: string) {
    if (!word || word.trim() === '') {
      return;
    }

    this.wordService.addWordWithValidation(word.trim()).subscribe({
      next: (response) => {
        if (response.success) {
          // Update the search result to reflect the word is now in collection
          if (this.searchResult) {
            this.searchResult.inCollection = true;
          }
          // Reload word stats to reflect the new word count
          this.loadWordStats();
        } else {
          this.searchError = response.message;
        }
      },
      error: (error) => {
        this.searchError = 'Error adding word to collection: ' + error.message;
      }
    });
  }

  onSearchModeChange() {
    // Clear search results when switching modes
    this.searchResult = null;
    this.searchError = '';
    this.searchWord = '';
  }

  // Search toggle methods
  toggleSearchMode() {
    this.searchMode = this.searchMode === 'basic' ? 'advanced' : 'basic';
    this.onSearchModeChange();
  }

  expandSearchToggle() {
    this.searchToggleExpanded = true;
  }

  collapseSearchToggle() {
    this.searchToggleExpanded = false;
  }

  // Puzzle toggle methods
  togglePuzzlePanel() {
    this.puzzlePanelExpanded = !this.puzzlePanelExpanded;
  }

  expandPuzzleToggle() {
    this.puzzleToggleExpanded = true;
  }

  collapsePuzzleToggle() {
    this.puzzleToggleExpanded = false;
  }
}
