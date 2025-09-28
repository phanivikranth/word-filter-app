import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { WordService, BasicSearchResult, OxfordValidationResponse, AddWordResponse } from './word.service';
import { WordFilter, WordStats, WordsByLength } from '../models/word.model';
import { environment } from '../../environments/environment';

describe('WordService', () => {
  let service: WordService;
  let httpMock: HttpTestingController;

  const mockWordStats: WordStats = {
    total_words: 416309,
    min_length: 2,
    max_length: 28,
    avg_length: 8.5
  };

  const mockWordsByLength: WordsByLength = {
    length: 5,
    count: 12543,
    words: ['apple', 'grape', 'bench', 'chair', 'dance']
  };

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

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [WordService]
    });
    service = TestBed.inject(WordService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('getFilteredWords', () => {
    it('should fetch filtered words with all filter parameters', () => {
      const mockWords = ['apple', 'application', 'apply'];
      const filter: WordFilter = {
        contains: 'app',
        starts_with: 'ap',
        ends_with: 'le',
        min_length: 3,
        max_length: 10,
        exact_length: 5,
        limit: 100
      };

      service.getFilteredWords(filter).subscribe(words => {
        expect(words).toEqual(mockWords);
      });

      const req = httpMock.expectOne(req => {
        return req.url === `${environment.apiUrl}/words` &&
               req.params.get('contains') === 'app' &&
               req.params.get('starts_with') === 'ap' &&
               req.params.get('ends_with') === 'le' &&
               req.params.get('min_length') === '3' &&
               req.params.get('max_length') === '10' &&
               req.params.get('exact_length') === '5' &&
               req.params.get('limit') === '100';
      });

      expect(req.request.method).toBe('GET');
      req.flush(mockWords);
    });

    it('should fetch filtered words with partial filter parameters', () => {
      const mockWords = ['banana', 'bandana'];
      const filter: WordFilter = {
        contains: 'an',
        limit: 50
      };

      service.getFilteredWords(filter).subscribe(words => {
        expect(words).toEqual(mockWords);
      });

      const req = httpMock.expectOne(req => {
        return req.url === `${environment.apiUrl}/words` &&
               req.params.get('contains') === 'an' &&
               req.params.get('limit') === '50' &&
               !req.params.has('starts_with') &&
               !req.params.has('ends_with');
      });

      expect(req.request.method).toBe('GET');
      req.flush(mockWords);
    });

    it('should handle empty filter object', () => {
      const mockWords = ['word1', 'word2', 'word3'];
      const filter: WordFilter = {};

      service.getFilteredWords(filter).subscribe(words => {
        expect(words).toEqual(mockWords);
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/words`);
      expect(req.request.method).toBe('GET');
      expect(req.request.params.keys().length).toBe(0);
      req.flush(mockWords);
    });

    it('should handle HTTP errors', () => {
      const filter: WordFilter = { contains: 'test' };

      service.getFilteredWords(filter).subscribe({
        next: () => fail('Expected error'),
        error: (error) => {
          expect(error.status).toBe(500);
        }
      });

      const req = httpMock.expectOne(req => req.url.includes('/words'));
      req.flush('Server error', { status: 500, statusText: 'Internal Server Error' });
    });
  });

  describe('getWordStats', () => {
    it('should fetch word statistics', () => {
      service.getWordStats().subscribe(stats => {
        expect(stats).toEqual(mockWordStats);
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/words/stats`);
      expect(req.request.method).toBe('GET');
      req.flush(mockWordStats);
    });

    it('should handle stats API error', () => {
      service.getWordStats().subscribe({
        next: () => fail('Expected error'),
        error: (error) => {
          expect(error.status).toBe(404);
        }
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/words/stats`);
      req.flush('Not found', { status: 404, statusText: 'Not Found' });
    });
  });

  describe('getWordsByLength', () => {
    it('should fetch words by specific length', () => {
      const length = 5;

      service.getWordsByLength(length).subscribe(result => {
        expect(result).toEqual(mockWordsByLength);
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/words/by-length/${length}`);
      expect(req.request.method).toBe('GET');
      req.flush(mockWordsByLength);
    });

    it('should handle different lengths', () => {
      const length = 3;
      const mockResult: WordsByLength = {
        length: 3,
        count: 2543,
        words: ['cat', 'dog', 'bat', 'car']
      };

      service.getWordsByLength(length).subscribe(result => {
        expect(result.length).toBe(length);
        expect(result).toEqual(mockResult);
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/words/by-length/${length}`);
      req.flush(mockResult);
    });
  });

  describe('getInteractiveWords', () => {
    it('should fetch interactive words with pattern', () => {
      const length = 5;
      const pattern = 'a??le';
      const mockWords = ['apple', 'angle'];

      service.getInteractiveWords(length, pattern).subscribe(words => {
        expect(words).toEqual(mockWords);
      });

      const req = httpMock.expectOne(req => {
        return req.url === `${environment.apiUrl}/words/interactive` &&
               req.params.get('length') === '5' &&
               req.params.get('pattern') === 'a??le';
      });

      expect(req.request.method).toBe('GET');
      req.flush(mockWords);
    });

    it('should handle empty pattern results', () => {
      const length = 7;
      const pattern = 'x?x?x?x';
      const mockWords: string[] = [];

      service.getInteractiveWords(length, pattern).subscribe(words => {
        expect(words).toEqual(mockWords);
        expect(words.length).toBe(0);
      });

      const req = httpMock.expectOne(req => req.url.includes('/words/interactive'));
      req.flush(mockWords);
    });
  });

  describe('searchBasicWord', () => {
    it('should perform basic word search with Oxford validation', () => {
      const word = 'example';

      service.searchBasicWord(word).subscribe(result => {
        expect(result).toEqual(mockBasicSearchResult);
        expect(result.word).toBe(word);
        expect(result.inCollection).toBe(true);
        expect(result.oxford).toBeTruthy();
      });

      // Expect collection check request
      const collectionReq = httpMock.expectOne(`${environment.apiUrl}/words/check`);
      expect(collectionReq.request.method).toBe('POST');
      expect(collectionReq.request.body).toEqual({ word: word });
      collectionReq.flush({ exists: true });

      // Expect Oxford validation request
      const oxfordReq = httpMock.expectOne(`${environment.apiUrl}/words/validate`);
      expect(oxfordReq.request.method).toBe('POST');
      expect(oxfordReq.request.body).toEqual({ word: word });
      oxfordReq.flush({
        success: true,
        word: word,
        oxford_validation: mockBasicSearchResult.oxford || undefined,
        message: 'Word validated successfully'
      } as OxfordValidationResponse);
    });

    it('should handle word not in collection', () => {
      const word = 'nonexistent';

      service.searchBasicWord(word).subscribe(result => {
        expect(result.word).toBe(word);
        expect(result.inCollection).toBe(false);
        expect(result.oxford).toBeTruthy();
      });

      // Collection check returns false
      const collectionReq = httpMock.expectOne(`${environment.apiUrl}/words/check`);
      collectionReq.flush({ exists: false });

      // Oxford validation still works
      const oxfordReq = httpMock.expectOne(`${environment.apiUrl}/words/validate`);
      oxfordReq.flush({
        success: true,
        word: word,
        oxford_validation: { ...mockBasicSearchResult.oxford, word: word },
        message: 'Word validated successfully'
      } as OxfordValidationResponse);
    });

    it('should handle Oxford validation failure gracefully', () => {
      const word = 'testword';

      service.searchBasicWord(word).subscribe(result => {
        expect(result.word).toBe(word);
        expect(result.inCollection).toBe(true);
        expect(result.oxford).toBe(null);
      });

      // Collection check succeeds
      const collectionReq = httpMock.expectOne(`${environment.apiUrl}/words/check`);
      collectionReq.flush({ exists: true });

      // Oxford validation fails
      const oxfordReq = httpMock.expectOne(`${environment.apiUrl}/words/validate`);
      oxfordReq.flush('Oxford service error', { status: 503, statusText: 'Service Unavailable' });
    });

    it('should fallback to filtered search when check endpoint fails', () => {
      const word = 'fallback';

      service.searchBasicWord(word).subscribe(result => {
        expect(result.word).toBe(word);
        expect(result.inCollection).toBe(true);
      });

      // Collection check endpoint fails
      const collectionReq = httpMock.expectOne(`${environment.apiUrl}/words/check`);
      collectionReq.flush('Endpoint not found', { status: 404, statusText: 'Not Found' });

      // Fallback to filtered words
      const fallbackReq = httpMock.expectOne(req => {
        return req.url === `${environment.apiUrl}/words` &&
               req.params.get('contains') === word.toLowerCase() &&
               req.params.get('limit') === '1';
      });
      fallbackReq.flush([word.toLowerCase()]);

      // Oxford validation
      const oxfordReq = httpMock.expectOne(`${environment.apiUrl}/words/validate`);
      oxfordReq.flush({
        success: true,
        word: word,
        oxford_validation: { ...mockBasicSearchResult.oxford, word: word },
        message: 'Success'
      } as OxfordValidationResponse);
    });
  });

  describe('addWordWithValidation', () => {
    it('should add word with Oxford validation', () => {
      const word = 'newword';
      const mockResponse: AddWordResponse = {
        success: true,
        word: word,
        was_new: true,
        oxford_validation: mockBasicSearchResult.oxford || undefined,
        message: 'Word added successfully',
        total_words: 416310
      };

      service.addWordWithValidation(word).subscribe(response => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/words/add-validated`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ word: word, skip_oxford: false });
      req.flush(mockResponse);
    });

    it('should handle word addition failure', () => {
      const word = 'invalidword';

      service.addWordWithValidation(word).subscribe({
        next: () => fail('Expected error'),
        error: (error) => {
          expect(error.status).toBe(400);
        }
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/words/add-validated`);
      req.flush('Invalid word', { status: 400, statusText: 'Bad Request' });
    });
  });

  describe('addWord', () => {
    it('should add word without Oxford validation', () => {
      const word = 'simpleword';
      const mockResponse: AddWordResponse = {
        success: true,
        word: word,
        was_new: true,
        message: 'Word added successfully',
        total_words: 416310
      };

      service.addWord(word).subscribe(response => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/words/add`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ word: word });
      req.flush(mockResponse);
    });
  });

  describe('Environment Configuration', () => {
    it('should use correct API base URL from environment', () => {
      const filter: WordFilter = { contains: 'test' };

      service.getFilteredWords(filter).subscribe();

      const req = httpMock.expectOne(req => req.url.startsWith(environment.apiUrl));
      expect(req.request.url).toBe(`${environment.apiUrl}/words`);
      req.flush([]);
    });
  });

  describe('Error Handling', () => {
    it('should handle network errors gracefully', () => {
      service.getWordStats().subscribe({
        next: () => fail('Expected error'),
        error: (error) => {
          expect(error.name).toBe('HttpErrorResponse');
        }
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/words/stats`);
      req.error(new ErrorEvent('Network error'));
    });

    it('should handle timeout errors', () => {
      service.getFilteredWords({}).subscribe({
        next: () => fail('Expected error'),
        error: (error) => {
          expect(error.status).toBe(0);
        }
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/words`);
      req.error(new ErrorEvent('Timeout'));
    });
  });
});
