import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup } from '@angular/forms';
import { WordService } from './services/word.service';
import { WordFilter, WordStats } from './models/word.model';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  title = 'Word Filter App';
  activeTab = 'filter';
  
  // Filter tab properties
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
}
