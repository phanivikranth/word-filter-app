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
  activeTab = 'filter';
  
  // Search mode properties
  searchMode = 'basic'; // Default to basic search
  
  // Basic search properties
  basicSearchTerm = '';
  basicSearchResult: BasicSearchResult | null = null;
  isBasicSearching = false;
  basicSearchError = '';

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

  // Tab management
  setActiveTab(tab: string) {
    this.activeTab = tab;
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
    this.letterBoxes = [];
    this.interactiveWords = [];
    this.interactiveError = '';
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
    if (!this.interactiveWordLength || this.letterBoxes.length === 0) {
      this.interactiveError = 'Please set a word length first.';
      return;
    }

    // Create a random pattern with some letters filled
    const alphabet = 'abcdefghijklmnopqrstuvwxyz';
    const fillPositions = Math.min(
      Math.max(1, Math.floor(this.interactiveWordLength / 3)), // Fill 1/3 of positions
      this.interactiveWordLength - 1
    );

    // Clear current pattern
    this.letterBoxes = new Array(this.interactiveWordLength).fill('');

    // Fill random positions
    const positions = new Set<number>();
    while (positions.size < fillPositions) {
      positions.add(Math.floor(Math.random() * this.interactiveWordLength));
    }

    positions.forEach(pos => {
      const randomLetter = alphabet[Math.floor(Math.random() * alphabet.length)];
      this.letterBoxes[pos] = randomLetter;
    });

    // Clear previous results
    this.interactiveWords = [];
    this.interactiveError = '';

    console.log('Generated random pattern:', this.letterBoxes.map(l => l || '?').join(''));
  }

  // Basic Search Methods
  onSearchModeChange() {
    // Clear previous results when switching modes
    this.basicSearchResult = null;
    this.basicSearchError = '';
    this.error = '';
    this.words = [];
  }

  searchBasicWord() {
    if (!this.basicSearchTerm?.trim()) {
      this.basicSearchError = 'Please enter a word to search.';
      return;
    }

    const word = this.basicSearchTerm.trim();
    
    // Basic validation
    if (!word.match(/^[a-zA-Z]+$/)) {
      this.basicSearchError = 'Word must contain only letters.';
      return;
    }

    this.isBasicSearching = true;
    this.basicSearchError = '';
    this.basicSearchResult = null;

    this.wordService.searchBasicWord(word).subscribe({
      next: (result) => {
        this.basicSearchResult = result;
        this.isBasicSearching = false;
        console.log('Basic search result:', result);
      },
      error: (error) => {
        console.error('Error in basic search:', error);
        this.basicSearchError = 'Failed to search word. Please check your connection and try again.';
        this.isBasicSearching = false;
      }
    });
  }

  searchSuggestionWord(word: string) {
    this.basicSearchTerm = word;
    this.searchBasicWord();
  }

  addWordToCollection(word: string) {
    this.wordService.addWordWithValidation(word).subscribe({
      next: (response: AddWordResponse) => {
        if (response.success) {
          // Refresh the search to show updated collection status
          this.searchBasicWord();
          // Refresh stats
          this.loadWordStats();
          console.log('Word added successfully:', response);
        } else {
          this.basicSearchError = response.message || 'Failed to add word';
        }
      },
      error: (error) => {
        console.error('Error adding word:', error);
        this.basicSearchError = 'Failed to add word to collection';
      }
    });
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
    this.basicSearchTerm = word;
    this.searchBasicWord();
  }

  playPronunciation(audioUrl: string) {
    if (audioUrl) {
      const audio = new Audio(audioUrl);
      audio.play().catch(error => {
        console.error('Error playing pronunciation:', error);
      });
    }
  }
}
