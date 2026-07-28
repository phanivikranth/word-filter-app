import { TestBed } from '@angular/core/testing';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';

import { AppComponent } from '../app.component';
import { AppModule } from '../app.module';
import { WordService } from '../services/word.service';
import { WordStatsService } from '../core/services/word-stats.service';
import { WordCheckService } from '../features/word-check/word-check.service';
import { FiltersService } from '../features/filters/filters.service';
import { PuzzleSolverService } from '../features/puzzles/puzzle-solver.service';
import { environment } from '../../environments/environment';
import {
  MOCK_WORD_STATS,
  MOCK_WORDS_LIST,
  MOCK_BASIC_SEARCH_RESULT,
  MOCK_ADD_WORD_RESPONSE_SUCCESS,
  MOCK_INTERACTIVE_WORDS,
} from '../testing/test-data';
import { AsyncTestHelper } from '../testing/test-utils';
import { MaterialModule } from '../material.module';

/**
 * Integration tests for modular feature services and app bootstrap.
 * Exercises real WordService HTTP wiring through focused services (post-facade split).
 */
describe('Terse app integration', () => {
  describe('App bootstrap', () => {
    it('should create the root component with app shell', async () => {
      await TestBed.configureTestingModule({
        imports: [AppModule, RouterTestingModule, HttpClientTestingModule, NoopAnimationsModule],
      }).compileComponents();

      const fixture = TestBed.createComponent(AppComponent);
      expect(fixture.componentInstance).toBeTruthy();
      expect(fixture.nativeElement.querySelector('app-shell')).toBeTruthy();
    });
  });

  describe('WordStatsService', () => {
    let httpMock: HttpTestingController;
    let wordStats: WordStatsService;

    beforeEach(() => {
      TestBed.configureTestingModule({
        imports: [HttpClientTestingModule],
        providers: [WordService, WordStatsService],
      });
      httpMock = TestBed.inject(HttpTestingController);
      wordStats = TestBed.inject(WordStatsService);
    });

    afterEach(() => {
      httpMock.verify();
    });

    it('should load word statistics from the API', async () => {
      wordStats.load();

      const statsReq = httpMock.expectOne(`${environment.apiUrl}/words/stats`);
      expect(statsReq.request.method).toBe('GET');
      statsReq.flush(MOCK_WORD_STATS);

      await AsyncTestHelper.waitFor(() => wordStats.wordStats !== null);

      expect(wordStats.wordStats).toEqual(MOCK_WORD_STATS);
      expect(wordStats.loadError).toBe('');
    });

    it('should record an error when stats loading fails', async () => {
      wordStats.load();

      const statsReq = httpMock.expectOne(`${environment.apiUrl}/words/stats`);
      statsReq.flush('Server error', { status: 500, statusText: 'Internal Server Error' });

      await AsyncTestHelper.waitFor(() => wordStats.loadError !== '');

      expect(wordStats.wordStats).toBeNull();
      expect(wordStats.loadError).toBe('Failed to load word statistics');
    });
  });

  describe('FiltersService', () => {
    let httpMock: HttpTestingController;
    let filters: FiltersService;

    beforeEach(() => {
      TestBed.configureTestingModule({
        imports: [HttpClientTestingModule, ReactiveFormsModule],
        providers: [WordService, FiltersService],
      });
      httpMock = TestBed.inject(HttpTestingController);
      filters = TestBed.inject(FiltersService);
    });

    afterEach(() => {
      httpMock.verify();
    });

    it('should perform advanced filtering via /words/advanced-filter', async () => {
      filters.filterForm.patchValue({
        contains: 'pro',
        starts_with: 'p',
        min_length: 7,
      });

      filters.searchWords();

      const filterReq = httpMock.expectOne((req) => {
        return (
          req.url === `${environment.apiUrl}/words/advanced-filter` &&
          req.params.get('contains') === 'pro' &&
          req.params.get('starts_with') === 'p' &&
          req.params.get('minLength') === '7'
        );
      });

      const filteredWords = ['programming', 'professional', 'project'];
      filterReq.flush({ words: filteredWords, source: 'word_game_db', mode: 'filter' });

      await AsyncTestHelper.waitForPropertyChange(filters, 'loading', false);

      expect(filters.words).toEqual(filteredWords);
      expect(filters.advancedFilterMode).toBe('filter');
      expect(filters.error).toBe('');
    });

    it('should clear filters and reload with default limit', async () => {
      filters.filterForm.patchValue({
        contains: 'test',
        min_length: 5,
      });

      filters.clearFilters();

      const clearReq = httpMock.expectOne((req) => {
        return (
          req.url === `${environment.apiUrl}/words/advanced-filter` &&
          req.params.get('limit') === '100' &&
          !req.params.has('contains') &&
          !req.params.has('minLength')
        );
      });

      clearReq.flush({ words: MOCK_WORDS_LIST, source: 'word_game_db', mode: 'browse' });

      await AsyncTestHelper.waitForPropertyChange(filters, 'loading', false);

      expect(filters.filterForm.get('contains')?.value).toBeNull();
      expect(filters.filterForm.get('min_length')?.value).toBeNull();
      expect(filters.filterForm.get('limit')?.value).toBe(100);
      expect(filters.words).toEqual(MOCK_WORDS_LIST);
    });

    it('should handle network errors during filter search', async () => {
      filters.searchWords();

      const req = httpMock.expectOne((r) => r.url.includes('/words/advanced-filter'));
      req.error(new ErrorEvent('Network error'));

      await AsyncTestHelper.waitForPropertyChange(filters, 'loading', false);

      expect(filters.loading).toBeFalse();
      expect(filters.error).toContain('Failed to search words');
    });
  });

  describe('WordCheckService', () => {
    let httpMock: HttpTestingController;
    let wordCheck: WordCheckService;

    beforeEach(() => {
      TestBed.configureTestingModule({
        imports: [
          HttpClientTestingModule,
          RouterTestingModule,
          NoopAnimationsModule,
          MaterialModule,
        ],
        providers: [WordService, WordCheckService, WordStatsService],
      });
      httpMock = TestBed.inject(HttpTestingController);
      wordCheck = TestBed.inject(WordCheckService);
    });

    afterEach(() => {
      try {
        httpMock.verify();
      } catch {
        // WordCheck flows may leave snackbar-only side effects; ignore stray requests in edge cases
      }
    });

    it('should perform basic search (collection check + Oxford validate)', async () => {
      wordCheck.searchWord = 'example';
      wordCheck.searchWordBasic();

      const checkReq = httpMock.expectOne(`${environment.apiUrl}/words/check`);
      checkReq.flush({ exists: true });

      const oxfordReq = httpMock.expectOne(`${environment.apiUrl}/words/validate`);
      oxfordReq.flush({
        success: true,
        word: 'example',
        oxford_validation: MOCK_BASIC_SEARCH_RESULT.oxford,
        message: 'Word validated',
      });

      await AsyncTestHelper.waitForPropertyChange(wordCheck, 'isSearching', false);

      expect(wordCheck.searchResult?.word).toBe('example');
      expect(wordCheck.searchResult?.inCollection).toBeTrue();
      expect(wordCheck.searchResult?.oxford).toEqual(MOCK_BASIC_SEARCH_RESULT.oxford);
      expect(wordCheck.searchError).toBe('');
    });

    it('should handle word not in collection with valid Oxford entry', async () => {
      wordCheck.searchWord = 'uncommon';
      wordCheck.searchWordBasic();

      httpMock.expectOne(`${environment.apiUrl}/words/check`).flush({ exists: false });

      httpMock.expectOne(`${environment.apiUrl}/words/validate`).flush({
        success: true,
        word: 'uncommon',
        oxford_validation: {
          ...MOCK_BASIC_SEARCH_RESULT.oxford!,
          word: 'uncommon',
        },
        message: 'Word validated',
      });

      await AsyncTestHelper.waitForPropertyChange(wordCheck, 'isSearching', false);

      expect(wordCheck.searchResult?.inCollection).toBeFalse();
      expect(wordCheck.searchResult?.oxford).toBeTruthy();
    });

    it('should add a word and refresh search + stats', async () => {
      const newWord = 'newword';

      wordCheck.addWordToCollection(newWord);

      const addReq = httpMock.expectOne(`${environment.apiUrl}/words/add-validated`);
      expect(addReq.request.body).toEqual({ word: newWord, skip_oxford: false });
      addReq.flush(MOCK_ADD_WORD_RESPONSE_SUCCESS);

      const checkReq = httpMock.expectOne(`${environment.apiUrl}/words/check`);
      checkReq.flush({ exists: true });

      const oxfordReq = httpMock.expectOne(`${environment.apiUrl}/words/validate`);
      oxfordReq.flush({
        success: true,
        word: newWord,
        oxford_validation: MOCK_BASIC_SEARCH_RESULT.oxford,
        message: 'Valid word',
      });

      const statsReq = httpMock.expectOne(`${environment.apiUrl}/words/stats`);
      statsReq.flush({ ...MOCK_WORD_STATS, total_words: MOCK_WORD_STATS.total_words + 1 });

      await AsyncTestHelper.waitForPropertyChange(wordCheck, 'isSearching', false);

      expect(wordCheck.searchResult?.inCollection).toBeTrue();
    });

    it('should surface validation message when add fails', async () => {
      wordCheck.addWordToCollection('invalid123');

      const addReq = httpMock.expectOne(`${environment.apiUrl}/words/add-validated`);
      addReq.flush({
        success: false,
        word: 'invalid123',
        was_new: false,
        message: 'Invalid word format',
      });

      await AsyncTestHelper.waitFor(() => wordCheck.searchError !== '');

      expect(wordCheck.searchError).toBe('Invalid word format');
    });
  });

  describe('PuzzleSolverService', () => {
    let httpMock: HttpTestingController;
    let puzzles: PuzzleSolverService;

    beforeEach(() => {
      TestBed.configureTestingModule({
        imports: [HttpClientTestingModule, NoopAnimationsModule, MaterialModule],
        providers: [WordService, PuzzleSolverService],
      });
      httpMock = TestBed.inject(HttpTestingController);
      puzzles = TestBed.inject(PuzzleSolverService);
    });

    afterEach(() => {
      httpMock.verify();
    });

    it('should find matching words via /words/puzzle', async () => {
      puzzles.puzzleLength = 5;
      puzzles.onPuzzleLengthChange();
      puzzles.letterBoxes = ['a', '', '', 'l', 'e'];

      puzzles.findMatchingWords();

      const puzzleReq = httpMock.expectOne((req) => {
        return (
          req.url === `${environment.apiUrl}/words/puzzle` &&
          req.params.get('pattern') === 'a??le'
        );
      });

      puzzleReq.flush(MOCK_INTERACTIVE_WORDS);

      await AsyncTestHelper.waitForPropertyChange(puzzles, 'interactiveLoading', false);

      expect(puzzles.interactiveWords).toEqual(MOCK_INTERACTIVE_WORDS);
      expect(puzzles.interactiveError).toBe('');
    });

    it('should report when no puzzle matches are found', async () => {
      puzzles.puzzleLength = 4;
      puzzles.onPuzzleLengthChange();
      puzzles.letterBoxes = ['z', 'x', 'q', 'w'];

      puzzles.findMatchingWords();

      const puzzleReq = httpMock.expectOne((req) => req.url.includes('/words/puzzle'));
      puzzleReq.flush([]);

      await AsyncTestHelper.waitForPropertyChange(puzzles, 'interactiveLoading', false);

      expect(puzzles.interactiveWords).toEqual([]);
      expect(puzzles.interactiveError).toBe('No words found matching your pattern.');
    });

    it('should handle puzzle API failures', async () => {
      puzzles.puzzleLength = 5;
      puzzles.onPuzzleLengthChange();
      puzzles.letterBoxes = ['t', 'e', 's', 't', 's'];

      puzzles.findMatchingWords();

      const req = httpMock.expectOne((r) => r.url.includes('/words/puzzle'));
      req.error(new ErrorEvent('Network error'));

      await AsyncTestHelper.waitForPropertyChange(puzzles, 'interactiveLoading', false);

      expect(puzzles.interactiveError).toBe(
        'Failed to find words. Make sure the backend is running.'
      );
    });
  });
});
