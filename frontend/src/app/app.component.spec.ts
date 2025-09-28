import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { of, throwError, from } from 'rxjs';

import { AppComponent } from './app.component';
import { WordService, BasicSearchResult, AddWordResponse } from './services/word.service';
import { WordStats } from './models/word.model';

describe('AppComponent', () => {
  let component: AppComponent;
  let fixture: ComponentFixture<AppComponent>;
  let wordService: jasmine.SpyObj<WordService>;

  const mockWordStats: WordStats = {
    total_words: 416309,
    min_length: 2,
    max_length: 28,
    avg_length: 8.5
  };

  const mockWords = ['apple', 'banana', 'cherry', 'date', 'elderberry'];

  const mockBasicSearchResult: BasicSearchResult = {
    word: 'example',
    inCollection: true,
    oxford: {
      word: 'example',
      is_valid: true,
      definitions: ['A thing characteristic of its kind or illustrating a general rule.'],
      word_forms: ['example', 'examples'],
      pronunciations: [
        {
          prefix: 'BrE',
          ipa: '/ɪɡˈzɑːmpl/',
          url: 'https://audio.oxforddictionaries.com/example.mp3'
        }
      ],
      examples: ['This is a good example of modern architecture.'],
      reason: 'Word found in Oxford Dictionary'
    }
  };

  beforeEach(async () => {
    const wordServiceSpy = jasmine.createSpyObj('WordService', [
      'getWordStats',
      'getFilteredWords',
      'getInteractiveWords',
      'searchBasicWord',
      'addWordWithValidation'
    ]);

    await TestBed.configureTestingModule({
      declarations: [AppComponent],
      imports: [ReactiveFormsModule, FormsModule, HttpClientTestingModule],
      providers: [
        { provide: WordService, useValue: wordServiceSpy }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(AppComponent);
    component = fixture.componentInstance;
    wordService = TestBed.inject(WordService) as jasmine.SpyObj<WordService>;

    // Setup default service returns
    wordService.getWordStats.and.returnValue(of(mockWordStats));
    wordService.getFilteredWords.and.returnValue(of(mockWords));
    wordService.getInteractiveWords.and.returnValue(of(['apple', 'angle']));
    wordService.searchBasicWord.and.returnValue(of(mockBasicSearchResult));
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should have default values', () => {
    expect(component.title).toBe('Word Filter App');
    expect(component.activeTab).toBe('filter');
    expect(component.searchMode).toBe('basic');
    expect(component.basicSearchTerm).toBe('');
    expect(component.basicSearchResult).toBeNull();
    expect(component.isBasicSearching).toBeFalse();
    expect(component.words).toEqual([]);
    expect(component.loading).toBeFalse();
    expect(component.interactiveWords).toEqual([]);
  });

  describe('Form Initialization', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should initialize filter form with default values', () => {
      expect(component.filterForm).toBeTruthy();
      expect(component.filterForm.get('contains')?.value).toBe('');
      expect(component.filterForm.get('starts_with')?.value).toBe('');
      expect(component.filterForm.get('ends_with')?.value).toBe('');
      expect(component.filterForm.get('min_length')?.value).toBe('');
      expect(component.filterForm.get('max_length')?.value).toBe('');
      expect(component.filterForm.get('exact_length')?.value).toBe('');
      expect(component.filterForm.get('limit')?.value).toBe(100);
    });

    it('should create form controls properly', () => {
      const form = component.filterForm;
      expect(form.get('contains')).toBeTruthy();
      expect(form.get('starts_with')).toBeTruthy();
      expect(form.get('ends_with')).toBeTruthy();
      expect(form.get('min_length')).toBeTruthy();
      expect(form.get('max_length')).toBeTruthy();
      expect(form.get('exact_length')).toBeTruthy();
      expect(form.get('limit')).toBeTruthy();
    });
  });

  describe('Component Initialization', () => {
    it('should load word stats on init', () => {
      fixture.detectChanges();
      
      expect(wordService.getWordStats).toHaveBeenCalled();
      expect(component.wordStats).toEqual(mockWordStats);
    });

    it('should load initial words on init', () => {
      fixture.detectChanges();
      
      expect(wordService.getFilteredWords).toHaveBeenCalled();
      expect(component.words).toEqual(mockWords);
    });

    it('should handle word stats loading error', async () => {
      wordService.getWordStats.and.returnValue(throwError(() => new Error('API Error')));
      spyOn(console, 'error');
      
      // Call loadWordStats directly
      component.loadWordStats();
      
      // Wait for the error observable to complete
      await new Promise(resolve => setTimeout(resolve, 100));
      
      expect(console.error).toHaveBeenCalled();
      expect(component.error).toBe('Failed to load word statistics');
    });
  });

  describe('Advanced Filter Functionality', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should search words with filters', () => {
      component.filterForm.patchValue({
        contains: 'app',
        starts_with: 'ap',
        limit: 50
      });

      component.searchWords();

      expect(wordService.getFilteredWords).toHaveBeenCalledWith({
        contains: 'app',
        starts_with: 'ap',
        limit: 50
      });
      expect(component.words).toEqual(mockWords);
      expect(component.loading).toBeFalse();
    });

    it('should handle empty filter values', () => {
      component.filterForm.patchValue({
        contains: '',
        starts_with: 'test',
        min_length: null,
        limit: 100
      });

      component.searchWords();

      expect(wordService.getFilteredWords).toHaveBeenCalledWith({
        starts_with: 'test',
        limit: 100
      });
    });

    it('should set loading state during search', () => {
      // Use a delayed observable instead of promise wrapping
      const delayedWords = new Promise<string[]>(resolve => {
        setTimeout(() => resolve(mockWords), 100);
      });
      wordService.getFilteredWords.and.returnValue(from(delayedWords));

      component.searchWords();

      expect(component.loading).toBeTruthy();
    });

    it('should handle search errors', () => {
      wordService.getFilteredWords.and.returnValue(throwError(() => new Error('Network Error')));
      spyOn(console, 'error');

      component.searchWords();

      expect(console.error).toHaveBeenCalled();
      expect(component.error).toBe('Failed to search words. Make sure the backend is running.');
      expect(component.loading).toBeFalse();
    });

    it('should clear filters', () => {
      component.filterForm.patchValue({
        contains: 'test',
        starts_with: 'te',
        min_length: 5
      });

      component.clearFilters();

      expect(component.filterForm.get('contains')?.value).toBe(null);
      expect(component.filterForm.get('starts_with')?.value).toBe(null);
      expect(component.filterForm.get('min_length')?.value).toBe(null);
      expect(component.filterForm.get('limit')?.value).toBe(100);
      expect(wordService.getFilteredWords).toHaveBeenCalledTimes(2); // Initial + clear
    });

    it('should trigger search on filter change', () => {
      spyOn(component, 'searchWords');
      
      component.onFilterChange();
      
      expect(component.searchWords).toHaveBeenCalled();
    });
  });

  describe('Basic Search Functionality', () => {
    beforeEach(() => {
      fixture.detectChanges();
      component.searchMode = 'basic';
    });

    it('should perform basic word search', () => {
      component.basicSearchTerm = 'example';

      component.searchBasicWord();

      expect(wordService.searchBasicWord).toHaveBeenCalledWith('example');
      expect(component.basicSearchResult).toEqual(mockBasicSearchResult);
      expect(component.isBasicSearching).toBeFalse();
      expect(component.basicSearchError).toBe('');
    });

    it('should validate basic search input', () => {
      component.basicSearchTerm = '';

      component.searchBasicWord();

      expect(component.basicSearchError).toBe('Please enter a word to search.');
      expect(wordService.searchBasicWord).not.toHaveBeenCalled();
    });

    it('should validate word contains only letters', () => {
      component.basicSearchTerm = 'test123';

      component.searchBasicWord();

      expect(component.basicSearchError).toBe('Word must contain only letters.');
      expect(wordService.searchBasicWord).not.toHaveBeenCalled();
    });

    it('should handle basic search errors', () => {
      wordService.searchBasicWord.and.returnValue(throwError(() => new Error('API Error')));
      component.basicSearchTerm = 'valid';

      component.searchBasicWord();

      expect(component.basicSearchError).toBe('Failed to search word. Please check your connection and try again.');
      expect(component.isBasicSearching).toBeFalse();
    });

    it('should set loading state during basic search', () => {
      component.basicSearchTerm = 'test';
      // Use a delayed observable instead of promise wrapping
      const delayedResult = new Promise<BasicSearchResult>(resolve => {
        setTimeout(() => resolve(mockBasicSearchResult), 100);
      });
      wordService.searchBasicWord.and.returnValue(from(delayedResult));

      component.searchBasicWord();

      expect(component.isBasicSearching).toBeTruthy();
    });

    it('should search suggestion word', () => {
      spyOn(component, 'searchBasicWord');
      
      component.searchSuggestionWord('suggested');
      
      expect(component.basicSearchTerm).toBe('suggested');
      expect(component.searchBasicWord).toHaveBeenCalled();
    });
  });

  describe('Interactive Search Functionality', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should set up letter boxes when word length changes', () => {
      component.interactiveWordLength = 5;

      component.onWordLengthChange();

      expect(component.letterBoxes.length).toBe(5);
      expect(component.letterBoxes).toEqual(['', '', '', '', '']);
      expect(component.interactiveWords).toEqual([]);
      expect(component.interactiveError).toBe('');
    });

    it('should clear letter boxes for invalid length', () => {
      component.interactiveWordLength = 0;

      component.onWordLengthChange();

      expect(component.letterBoxes).toEqual([]);
    });

    it('should update letter in specific position', () => {
      component.letterBoxes = ['', '', '', '', ''];
      const mockEvent = {
        target: { value: 'A' }
      };

      component.updateLetter(2, mockEvent);

      expect(component.letterBoxes[2]).toBe('a');
      expect(mockEvent.target.value).toBe('A');
    });

    it('should clean invalid characters from letter input', () => {
      component.letterBoxes = ['', '', '', '', ''];
      const mockEvent = {
        target: { value: 'A1@' }
      };

      component.updateLetter(1, mockEvent);

      expect(component.letterBoxes[1]).toBe('a');
      expect(mockEvent.target.value).toBe('A');
    });

    it('should find matching words with pattern', () => {
      component.interactiveWordLength = 5;
      component.letterBoxes = ['a', '', '', 'l', 'e'];

      component.findMatchingWords();

      expect(wordService.getInteractiveWords).toHaveBeenCalledWith(5, 'a??le');
      expect(component.interactiveWords).toEqual(['apple', 'angle']);
      expect(component.interactiveLoading).toBeFalse();
    });

    it('should validate word length before finding words', () => {
      component.interactiveWordLength = null;

      component.findMatchingWords();

      expect(component.interactiveError).toBe('Please enter a word length first.');
      expect(wordService.getInteractiveWords).not.toHaveBeenCalled();
    });

    it('should handle no matching words', () => {
      wordService.getInteractiveWords.and.returnValue(of([]));
      component.interactiveWordLength = 5;
      component.letterBoxes = ['x', 'x', 'x', 'x', 'x'];

      component.findMatchingWords();

      expect(component.interactiveWords).toEqual([]);
      expect(component.interactiveError).toBe('No words found matching your pattern.');
    });

    it('should handle interactive search errors', () => {
      wordService.getInteractiveWords.and.returnValue(throwError(() => new Error('API Error')));
      component.interactiveWordLength = 5;
      component.letterBoxes = ['a', '', '', '', ''];

      component.findMatchingWords();

      expect(component.interactiveError).toBe('Failed to find words. Make sure the backend is running.');
      expect(component.interactiveLoading).toBeFalse();
    });

    it('should clear interactive search', () => {
      component.interactiveWordLength = 5;
      component.letterBoxes = ['a', 'b', 'c'];
      component.interactiveWords = ['test'];
      component.interactiveError = 'error';

      component.clearInteractive();

      expect(component.interactiveWordLength).toBeNull();
      expect(component.letterBoxes).toEqual([]);
      expect(component.interactiveWords).toEqual([]);
      expect(component.interactiveError).toBe('');
    });

    it('should randomize pattern', () => {
      component.interactiveWordLength = 6;
      component.letterBoxes = new Array(6).fill('');

      component.randomizePattern();

      const filledPositions = component.letterBoxes.filter(letter => letter !== '').length;
      expect(filledPositions).toBeGreaterThan(0);
      expect(filledPositions).toBeLessThan(6);
      expect(component.interactiveWords).toEqual([]);
      expect(component.interactiveError).toBe('');
    });

    it('should validate word length before randomizing', () => {
      component.interactiveWordLength = null;

      component.randomizePattern();

      expect(component.interactiveError).toBe('Please set a word length first.');
    });
  });

  describe('Tab Management', () => {
    it('should set active tab', () => {
      component.setActiveTab('interactive');
      expect(component.activeTab).toBe('interactive');

      component.setActiveTab('basic');
      expect(component.activeTab).toBe('basic');
    });

    it('should start with filter tab active', () => {
      expect(component.activeTab).toBe('filter');
    });
  });

  describe('Search Mode Management', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should clear results when switching search modes', () => {
      component.basicSearchResult = mockBasicSearchResult;
      component.basicSearchError = 'error';
      component.error = 'filter error';
      component.words = mockWords;

      component.onSearchModeChange();

      expect(component.basicSearchResult).toBeNull();
      expect(component.basicSearchError).toBe('');
      expect(component.error).toBe('');
      expect(component.words).toEqual([]);
    });
  });

  describe('Word Addition Functionality', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should add word to collection', () => {
      const mockAddResponse: AddWordResponse = {
        success: true,
        word: 'newword',
        was_new: true,
        message: 'Word added successfully',
        total_words: 416310
      };
      wordService.addWordWithValidation.and.returnValue(of(mockAddResponse));
      spyOn(component, 'searchBasicWord');
      spyOn(component, 'loadWordStats');

      component.addWordToCollection('newword');

      expect(wordService.addWordWithValidation).toHaveBeenCalledWith('newword');
      expect(component.searchBasicWord).toHaveBeenCalled();
      expect(component.loadWordStats).toHaveBeenCalled();
    });

    it('should handle word addition failure', () => {
      const mockAddResponse: AddWordResponse = {
        success: false,
        word: 'invalidword',
        was_new: false,
        message: 'Word is invalid'
      };
      wordService.addWordWithValidation.and.returnValue(of(mockAddResponse));

      component.addWordToCollection('invalidword');

      expect(component.basicSearchError).toBe('Word is invalid');
    });

    it('should handle word addition API error', () => {
      wordService.addWordWithValidation.and.returnValue(throwError(() => new Error('API Error')));
      spyOn(console, 'error');

      component.addWordToCollection('testword');

      expect(console.error).toHaveBeenCalled();
      expect(component.basicSearchError).toBe('Failed to add word to collection');
    });
  });

  describe('Utility Functions', () => {
    it('should copy word to clipboard', async () => {
      const clipboardSpy = spyOn(navigator.clipboard, 'writeText').and.returnValue(Promise.resolve());
      spyOn(console, 'log');

      await component.copyWordToClipboard('test');

      expect(clipboardSpy).toHaveBeenCalledWith('test');
      expect(console.log).toHaveBeenCalledWith('Word copied to clipboard:', 'test');
    });

    it('should handle clipboard copy failure', async () => {
      spyOn(navigator.clipboard, 'writeText').and.returnValue(Promise.reject('Copy failed'));
      spyOn(console, 'error');

      // Call the component method
      component.copyWordToClipboard('test');

      // Wait for the Promise chain to complete
      await new Promise(resolve => setTimeout(resolve, 10));

      expect(console.error).toHaveBeenCalledWith('Failed to copy word to clipboard');
    });

    it('should explore word', () => {
      spyOn(component, 'searchBasicWord');
      
      component.exploreWord('explore');
      
      expect(component.searchMode).toBe('basic');
      expect(component.basicSearchTerm).toBe('explore');
      expect(component.searchBasicWord).toHaveBeenCalled();
    });

    it('should play pronunciation audio', () => {
      const mockAudio = jasmine.createSpyObj('HTMLAudioElement', ['play']);
      mockAudio.play.and.returnValue(Promise.resolve());
      spyOn(window, 'Audio').and.returnValue(mockAudio);

      component.playPronunciation('https://example.com/audio.mp3');

      expect(window.Audio).toHaveBeenCalledWith('https://example.com/audio.mp3');
      expect(mockAudio.play).toHaveBeenCalled();
    });

    it('should handle pronunciation play error', async () => {
      const mockAudio = jasmine.createSpyObj('HTMLAudioElement', ['play']);
      mockAudio.play.and.returnValue(Promise.reject(new Error('Audio error')));
      spyOn(window, 'Audio').and.returnValue(mockAudio);
      spyOn(console, 'error');

      component.playPronunciation('https://example.com/audio.mp3');

      expect(window.Audio).toHaveBeenCalledWith('https://example.com/audio.mp3');
      expect(mockAudio.play).toHaveBeenCalled();
      
      // Wait for the async error handling to complete
      await new Promise(resolve => setTimeout(resolve, 10));
      
      expect(console.error).toHaveBeenCalledWith('Error playing pronunciation:', jasmine.any(Error));
    });

    it('should not play pronunciation without URL', () => {
      spyOn(window, 'Audio');

      component.playPronunciation('');

      expect(window.Audio).not.toHaveBeenCalled();
    });
  });

  describe('Tracking Functions', () => {
    it('should track by index', () => {
      const result = component.trackByIndex(5, 'any');
      expect(result).toBe(5);
    });

    it('should track by word', () => {
      const result = component.trackByWord(3, 'testword');
      expect(result).toBe('testword');
    });
  });

  describe('Highlighting Functions', () => {
    it('should highlight position', () => {
      spyOn(console, 'log');
      
      component.highlightPosition(2);
      
      expect(console.log).toHaveBeenCalledWith('Highlighting position 3');
    });

    it('should unhighlight position', () => {
      spyOn(console, 'log');
      
      component.unhighlightPosition(1);
      
      expect(console.log).toHaveBeenCalledWith('Unhighlighting position 2');
    });
  });

  describe('Edge Cases and Error Handling', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should handle whitespace in basic search', () => {
      component.basicSearchTerm = '  test  ';

      component.searchBasicWord();

      expect(wordService.searchBasicWord).toHaveBeenCalledWith('test');
    });

    it('should handle empty interactive pattern', () => {
      component.interactiveWordLength = 3;
      component.letterBoxes = ['', '', ''];

      component.findMatchingWords();

      expect(wordService.getInteractiveWords).toHaveBeenCalledWith(3, '???');
    });

    it('should handle form reset edge cases', () => {
      component.filterForm.patchValue({
        contains: 'test',
        limit: 200
      });

      component.clearFilters();

      expect(component.filterForm.get('limit')?.value).toBe(100);
    });
  });
});
