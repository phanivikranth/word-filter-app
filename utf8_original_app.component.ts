import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup } from '@angular/forms';
import { MatSnackBar } from '@angular/material/snack-bar';
import { trigger, state, style, transition, animate, query, stagger } from '@angular/animations';
import { WordService, BasicSearchResult } from './services/word.service';
import { WordFilter, WordStats } from './models/word.model';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
  animations: [
    trigger('slideIn', [
      transition(':enter', [
        style({ opacity: 0, transform: 'translateY(-20px)' }),
        animate('300ms ease-out', style({ opacity: 1, transform: 'translateY(0)' }))
      ]),
      transition(':leave', [
        animate('200ms ease-in', style({ opacity: 0, transform: 'translateY(-20px)' }))
      ])
    ]),
    trigger('fadeIn', [
      transition(':enter', [
        style({ opacity: 0 }),
        animate('400ms ease-out', style({ opacity: 1 }))
      ])
    ]),
    trigger('scaleIn', [
      transition(':enter', [
        style({ opacity: 0, transform: 'scale(0.8)' }),
        animate('400ms cubic-bezier(0.34, 1.56, 0.64, 1)', style({ opacity: 1, transform: 'scale(1)' }))
      ])
    ]),
    trigger('listAnimation', [
      transition('* => *', [
        query(':enter', [
          style({ opacity: 0, transform: 'translateY(20px)' }),
          stagger(50, [
            animate('300ms ease-out', style({ opacity: 1, transform: 'translateY(0)' }))
          ])
        ], { optional: true })
      ])
    ]),
    trigger('cardHover', [
      state('default', style({ transform: 'scale(1)' })),
      state('hovered', style({ transform: 'scale(1.02)' })),
      transition('default <=> hovered', animate('200ms ease-out'))
    ])
  ]
})
export class AppComponent implements OnInit {
  title = 'Word Explorer';
  
  // ==========================================
  // STATE PROPERTIES
  // ==========================================
  
  /** Basic search properties */
  searchWord = '';
  searchResult: BasicSearchResult | null = null;
  isSearching = false;
  searchError = '';

  /** Word statistics and performance */
  wordStats: WordStats | null = null;
  performanceStats: any = null;
  performanceStatsVisible = false;

  /** Quick suggestions for standard search */
  quickSuggestions = [
    'butterfly', 'rainbow', 'adventure', 'magic', 'dinosaur', 
    'unicorn', 'treasure', 'mystery', 'friendship', 'courage'
  ];

  /** Advanced filter properties */
  filterForm: FormGroup;
  words: string[] = [];
  loading = false;
  error = '';

  /** Interactive tab properties */
  interactiveWordLength: number | null = null;
  letterBoxes: string[] = [];
  interactiveWords: string[] = [];
  interactiveLoading = false;
  interactiveError = '';
  
  /** Puzzle solver properties */
  puzzleLength = 5;
  puzzlePattern = '';

  /** Browse by length properties */
  browseLength = 5;
  browseWords: string[] = [];
  browseLoading = false;
  browseError = '';

  /** Theme configurations */
  isDarkMode = false;

  /** UI state managers */
  searchMode: 'basic' | 'advanced' | 'puzzle' | 'browse' = 'basic';
  statsPanelExpanded = false;
  searchToggleExpanded = false;
  puzzleToggleExpanded = false;
  puzzlePanelExpanded = false;
  hoveredCard: string | null = null;
  tickerItems: string[] = [];
  currentTickerIndex = 0;

  constructor(
    private fb: FormBuilder,
    private wordService: WordService,
    private snackBar: MatSnackBar
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

  // ==========================================
  // LIFECYCLE HOOKS
  // ==========================================

  ngOnInit() {
    // Default to light mode; only apply dark when explicitly saved
    this.isDarkMode = localStorage.getItem('theme') === 'dark';
    document.body.classList.remove('dark-mode');
    if (this.isDarkMode) {
      document.body.classList.add('dark-mode');
    }

    this.loadWordStats();
    this.searchWords(); 
    this.onPuzzleLengthChange(); 
  }

  // ==========================================
  // CORE SEARCH LOGIC
  // ==========================================

  /**
   * Sets the active search mode tabs.
   * @param mode Selected search mode
   */
  setSearchMode(mode: 'basic' | 'advanced' | 'puzzle' | 'browse') {
    this.searchMode = mode;
    this.showNotification(`Switched to ${mode} mode`, 'info');
  }

  /**
   * Clears state values when the search query input changes.
   */
  onSearchInput() {
    if (this.searchResult) {
      this.searchResult = null;
    }
    if (this.searchError) {
      this.searchError = '';
    }
  }

  /**
   * Executes a basic word search query with Oxford Dictionary lookup.
   */
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
        if (result.oxford || result.inCollection) {
          this.showNotification(`Found details for "${result.word}"!`, 'success');
        } else {
          this.showNotification(`No Oxford details found for "${result.word}".`, 'info');
        }
      },
      error: (error) => {
        this.searchError = 'Error searching for word: ' + error.message;
        this.isSearching = false;
        this.showNotification('Error searching for word. Check backend connection.', 'error');
      }
    });
  }

  /**
   * Executes an advanced search filtering query.
   */
  searchWords() {
    this.loading = true;
    this.error = '';
    
    const filterValues = this.filterForm.value;
    const filter: WordFilter = {};

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

  /**
   * Adds the specified word to the database collection.
   * @param word Word string to add
   */
  addWordToCollection(word: string) {
    if (!word || word.trim() === '') {
      return;
    }

    this.wordService.addWordWithValidation(word.trim()).subscribe({
      next: (response) => {
        if (response.success) {
          if (this.searchResult) {
            this.searchResult.inCollection = true;
          }
          
          if (response.was_new) {
            this.showNotification(`"${word}" added to your collection! (New word)`, 'success');
          } else {
            this.showNotification(`"${word}" was already in your collection.`, 'info');
          }
          this.loadWordStats();
        } else {
          this.searchError = response.message;
          this.showNotification(response.message, 'error');
        }
      },
      error: (error) => {
        console.error('Error adding word:', error);
        this.searchError = 'Error adding word to collection: ' + error.message;
        this.showNotification('Error adding word to collection', 'error');
      }
    });
  }

  /**
   * Clears advanced search form filters.
   */
  clearFilters() {
    this.filterForm.reset();
    this.filterForm.patchValue({ limit: 100 });
    this.searchWords();
  }

  /**
   * Auto-searches when inputs in the advanced filter form change.
   */
  onFilterChange() {
    this.searchWords();
  }

  // ==========================================
  // INTERACTIVE PUZZLE SOLVER
  // ==========================================

  /**
   * Handles interactive word length transitions.
   */
  onWordLengthChange() {
    if (this.interactiveWordLength && this.interactiveWordLength > 0) {
      this.letterBoxes = new Array(this.interactiveWordLength).fill('');
      this.interactiveWords = [];
      this.interactiveError = '';
    } else {
      this.letterBoxes = [];
    }
  }

  /**
   * Reinitializes letter input blocks based on active puzzle length.
   */
  onPuzzleLengthChange() {
    if (this.puzzleLength && this.puzzleLength > 0) {
      this.letterBoxes = new Array(this.puzzleLength).fill('');
      this.interactiveWords = [];
      this.interactiveError = '';
    } else {
      this.letterBoxes = [];
    }
  }

  /**
   * Tracks characters dynamically based on pattern input.
   */
  onPuzzlePatternChange() {
    if (this.puzzlePattern && this.puzzleLength) {
      this.letterBoxes = this.puzzlePattern.split('').slice(0, this.puzzleLength);
      while (this.letterBoxes.length < this.puzzleLength) {
        this.letterBoxes.push('');
      }
    } else {
      this.onPuzzleLengthChange();
    }
  }

  getPatternPlaceholder(): string {
    if (this.puzzleLength && this.puzzleLength > 0) {
      return '?'.repeat(this.puzzleLength);
    }
    return '?????';
  }

  /**
   * Updates letter inputs for specific puzzle boxes.
   */
  updateLetter(index: number, event: any) {
    const inputValue = event.target.value;
    let cleanValue = inputValue.replace(/[^a-zA-Z]/g, '').toLowerCase();
    
    if (cleanValue.length > 1) {
      cleanValue = cleanValue.charAt(0);
    }
    
    this.letterBoxes[index] = cleanValue;
    event.target.value = cleanValue.toUpperCase();
  }

  /**
   * Runs the pattern solver lookup in the backend.
   */
  findMatchingWords() {
    const wordLength = this.puzzleLength || this.interactiveWordLength;
    
    if (!wordLength || this.letterBoxes.length === 0) {
      this.interactiveError = 'Please enter a word length first.';
      this.showNotification('Please enter a word length first.', 'error');
      return;
    }

    this.interactiveLoading = true;
    this.interactiveError = '';

    const pattern = this.letterBoxes.map(letter => letter || '?').join('');
    
    this.wordService.getInteractiveWords(wordLength, pattern).subscribe({
      next: (words) => {
        this.interactiveWords = words;
        this.interactiveLoading = false;
        if (words.length === 0) {
          this.interactiveError = 'No words found matching your pattern.';
          this.showNotification('No words found matching your pattern.', 'info');
        } else {
          this.showNotification(`Found ${words.length} matching word${words.length === 1 ? '' : 's'}!`, 'success');
        }
      },
      error: (error) => {
        console.error('Error finding interactive words:', error);
        this.interactiveError = 'Failed to find words. Check backend.';
        this.interactiveLoading = false;
        this.showNotification('Failed to find words. Check backend connection.', 'error');
      }
    });
  }

  /**
   * Clears state values from the interactive puzzle solver panel.
   */
  clearInteractive() {
    this.interactiveWordLength = null;
    this.puzzleLength = 5;
    this.puzzlePattern = '';
    this.letterBoxes = [];
    this.interactiveWords = [];
    this.interactiveError = '';
    this.interactiveLoading = false;
    this.showNotification('Puzzle solver cleared', 'info');
  }

  /**
   * Randomizes the query character array inside the puzzle grid.
   */
  randomizePattern() {
    if (!this.puzzleLength || this.puzzleLength <= 0) {
      this.puzzleLength = 5;
    }

    const letters = 'abcdefghijklmnopqrstuvwxyz';
    const pattern = Array.from({ length: this.puzzleLength }, () => {
      return Math.random() < 0.3 ? letters[Math.floor(Math.random() * letters.length)] : '?';
    }).join('');

    this.puzzlePattern = pattern;
    this.onPuzzlePatternChange();
    this.interactiveError = '';
    this.showNotification('Random pattern generated!', 'info');
  }

  getCurrentPattern(): string {
    return this.letterBoxes.map(l => l || '?').join('').toUpperCase();
  }

  highlightPosition(index: number) {
    // Optional visual highlight log
  }

  unhighlightPosition(index: number) {
    // Optional visual highlight log
  }

  // ==========================================
  // BROWSE BY LENGTH LOGIC
  // ==========================================

  onBrowseLengthChange() {
    if (this.browseLength && this.browseLength > 0) {
      this.browseWords = [];
      this.browseError = '';
    }
  }

  /**
   * Loads words of a specific exact length.
   */
  loadWordsByLength() {
    if (!this.browseLength || this.browseLength <= 0) {
      this.browseError = 'Please enter a valid word length.';
      this.showNotification('Please enter a valid word length.', 'error');
      return;
    }

    this.browseLoading = true;
    this.browseError = '';

    this.wordService.getWordsByLength(this.browseLength).subscribe({
      next: (response) => {
        this.browseWords = response.words;
        this.browseLoading = false;
        this.showNotification(`Found ${response.words.length} words of length ${this.browseLength}!`, 'success');
      },
      error: (error) => {
        console.error('Error loading words by length:', error);
        this.browseError = 'Failed to load words. Check backend.';
        this.browseLoading = false;
        this.showNotification('Failed to load words. Check backend connection.', 'error');
      }
    });
  }

  clearBrowse() {
    this.browseLength = 5;
    this.browseWords = [];
    this.browseError = '';
    this.browseLoading = false;
    this.showNotification('Browse cleared', 'info');
  }

  // ==========================================
  // SYSTEM STATISTICS & THEMES
  // ==========================================

  /**
   * Loads backend dictionary parameters.
   */
  loadWordStats() {
    this.wordService.getWordStats().subscribe({
      next: (stats) => {
        this.wordStats = stats;
        this.updateTickerItems();
      },
      error: (error) => {
        console.error('Error loading word stats:', error);
        this.error = 'Failed to load word statistics';
        this.showNotification('Failed to load word statistics', 'error');
      }
    });
  }

  /**
   * Prepares tickers for dashboard display.
   */
  updateTickerItems() {
    if (this.wordStats) {
      this.tickerItems = [
        `≡ƒôÜ ${this.wordStats.total_words.toLocaleString()} Total Words`,
        `≡ƒôÅ Length Range: ${this.wordStats.min_length}-${this.wordStats.max_length} letters`,
        `≡ƒôè Average Length: ${this.wordStats.avg_length} letters`,
        `≡ƒÄ» Database Status: Active`,
        `Γ£¿ Oxford Dictionary: Integrated`,
        `≡ƒöì Search Modes: Basic & Advanced & Puzzle`,
        `≡ƒº⌐ Puzzle Solver: Available`,
        `≡ƒÆí Live Updates: Enabled`,
        `ΓÜí Real-time Search`,
        `≡ƒîƒ Material Design UI`
      ];
    }
  }

  toggleTheme() {
    this.isDarkMode = !this.isDarkMode;
    document.body.classList.toggle('dark-mode', this.isDarkMode);
    localStorage.setItem('theme', this.isDarkMode ? 'dark' : 'light');
    this.showNotification(
      `Switched to ${this.isDarkMode ? 'dark' : 'light'} mode`,
      'info'
    );
  }

  togglePerformanceStats() {
    this.performanceStatsVisible = !this.performanceStatsVisible;
    if (this.performanceStatsVisible && !this.performanceStats) {
      this.loadPerformanceStats();
    }
  }

  loadPerformanceStats() {
    this.wordService.getPerformanceStats().subscribe({
      next: (stats) => {
        this.performanceStats = stats;
      },
      error: (error) => {
        console.error('Error loading performance stats:', error);
        this.showNotification('Failed to load performance stats', 'error');
      }
    });
  }

  // ==========================================
  // UI INTERACTION HELPERS
  // ==========================================

  /**
   * Shows a visual SnackBar notification message.
   * @param message Text string
   * @param type Notification visual type
   */
  showNotification(message: string, type: 'success' | 'error' | 'info' = 'info') {
    this.snackBar.open(message, 'Close', {
      duration: 3000,
      horizontalPosition: 'end',
      verticalPosition: 'top',
      panelClass: [`snackbar-${type}`]
    });
  }

  /**
   * Copies the specified string to the clipboard.
   * @param word text content
   */
  copyWordToClipboard(word: string) {
    navigator.clipboard.writeText(word).then(() => {
      this.showNotification(`"${word}" copied to clipboard!`, 'success');
    }).catch(() => {
      this.showNotification('Failed to copy to clipboard', 'error');
    });
  }

  /**
   * Focuses and runs search basic details on click suggestion chips.
   * @param word target query
   */
  exploreWord(word: string) {
    this.searchMode = 'basic';
    this.searchWord = word;
    this.searchWordBasic();
    this.showNotification(`Searching for "${word}"...`, 'info');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  /**
   * Plays the audio pronunciation files from URLs.
   * @param audioUrl link
   */
  playPronunciation(audioUrl: string) {
    if (audioUrl) {
      const audio = new Audio(audioUrl);
      audio.play().catch(error => {
        console.error('Error playing pronunciation:', error);
      });
    }
  }

  // Trivial index tracking trackers
  trackByIndex(index: number, item: any): number { return index; }
  trackByWord(index: number, word: string): string { return word; }

  // Legacy layout togglers
  toggleStatsPanel() { this.statsPanelExpanded = !this.statsPanelExpanded; }
  expandStatsPanel() { this.statsPanelExpanded = true; this.loadWordStats(); }
  collapseStatsPanel() { this.statsPanelExpanded = false; }
  onSearchModeChange() {
    this.searchResult = null;
    this.searchError = '';
    this.searchWord = '';
    this.showNotification(`Switched to ${this.searchMode === 'basic' ? 'Basic' : this.searchMode === 'advanced' ? 'Advanced' : 'Puzzle'} mode.`, 'info');
  }
  toggleSearchMode() {
    this.searchMode = this.searchMode === 'basic' ? 'advanced' : 'basic';
    this.onSearchModeChange();
  }
  expandSearchToggle() { this.searchToggleExpanded = true; }
  collapseSearchToggle() { this.searchToggleExpanded = false; }
  togglePuzzlePanel() {
    this.searchMode = this.searchMode === 'puzzle' ? 'basic' : 'puzzle';
    this.onSearchModeChange();
  }
  expandPuzzleToggle() { this.puzzleToggleExpanded = true; }
  collapsePuzzleToggle() { this.puzzleToggleExpanded = false; }
  setHoveredCard(cardId: string | null) { this.hoveredCard = cardId; }
  getCardState(cardId: string): string { return this.hoveredCard === cardId ? 'hovered' : 'default'; }
}
