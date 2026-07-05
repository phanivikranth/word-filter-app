import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { map, switchMap, catchError } from 'rxjs/operators';
import { WordFilter, WordStats, WordsByLength } from '../models/word.model';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class WordService {
  private baseUrl = environment.apiUrl;

  constructor(private http: HttpClient) { }

  getFilteredWords(filter: WordFilter): Observable<string[]> {
    let params = new HttpParams();
    
    if (filter.contains) {
      params = params.set('contains', filter.contains);
    }
    if (filter.starts_with) {
      params = params.set('starts_with', filter.starts_with);
    }
    if (filter.ends_with) {
      params = params.set('ends_with', filter.ends_with);
    }
    if (filter.min_length) {
      params = params.set('min_length', filter.min_length.toString());
    }
    if (filter.max_length) {
      params = params.set('max_length', filter.max_length.toString());
    }
    if (filter.exact_length) {
      params = params.set('exact_length', filter.exact_length.toString());
    }
    if (filter.limit) {
      params = params.set('limit', filter.limit.toString());
    }

    return this.http.get<string[]>(`${this.baseUrl}/words`, { params });
  }

  /** Advanced filter via Words API + Word Game DB fallback */
  getAdvancedFilteredWords(filter: WordFilter): Observable<AdvancedFilterResponse> {
    let params = new HttpParams();

    if (filter.contains) {
      params = params.set('contains', filter.contains);
    }
    if (filter.starts_with) {
      params = params.set('starts_with', filter.starts_with);
    }
    if (filter.ends_with) {
      params = params.set('ends_with', filter.ends_with);
    }
    if (filter.min_length) {
      params = params.set('minLength', filter.min_length.toString());
    }
    if (filter.max_length) {
      params = params.set('maxLength', filter.max_length.toString());
    }
    if (filter.exact_length) {
      params = params.set('exactLength', filter.exact_length.toString());
    }
    if (filter.letter_pattern) {
      params = params.set('letterPattern', filter.letter_pattern);
    }
    params = params.set('limit', String(filter.limit || 100));

    return this.http.get<AdvancedFilterResponse>(
      `${this.baseUrl}/words/advanced-filter`,
      { params }
    );
  }

  getWordStats(): Observable<WordStats> {
    return this.http.get<WordStats>(`${this.baseUrl}/words/stats`);
  }

  getWordsByLength(length: number): Observable<WordsByLength> {
    return this.http.get<WordsByLength>(`${this.baseUrl}/words/by-length/${length}`);
  }

  getInteractiveWords(length: number, pattern: string): Observable<string[]> {
    let params = new HttpParams()
      .set('length', length.toString())
      .set('pattern', pattern);
    
    return this.http.get<string[]>(`${this.baseUrl}/words/interactive`, { params });
  }

  // Basic search with Oxford Dictionary integration
  searchBasicWord(word: string): Observable<BasicSearchResult> {
    const cleanWord = word.trim().toLowerCase();
    
    // First check collection
    return this.checkWordInCollection(cleanWord).pipe(
      switchMap(inCollection => {
        // Then validate with Oxford API
        return this.http.post<any>(`${this.baseUrl}/words/validate`, { word: cleanWord }).pipe(
          map(valResponse => {
            return {
              word: cleanWord,
              inCollection,
              oxford: valResponse.oxford_validation
            };
          }),
          catchError((error) => {
            console.error('Dictionary validation failed:', error);
            return of({
              word: cleanWord,
              inCollection,
              oxford: null,
              lookupFailed: true
            });
          })
        );
      })
    );
  }

  // Check if word exists in our collection
  private checkWordInCollection(word: string): Observable<boolean> {
    return new Observable(observer => {
      this.http.post<any>(`${this.baseUrl}/words/check`, { word: word }).subscribe({
        next: (response) => {
          observer.next(response.exists);
          observer.complete();
        },
        error: (error) => {
          // If check endpoint doesn't exist, fall back to search
          this.getFilteredWords({ contains: word.toLowerCase(), limit: 1 }).subscribe({
            next: (words) => {
              observer.next(words.includes(word.toLowerCase()));
              observer.complete();
            },
            error: (fallbackError) => {
              observer.error(fallbackError);
            }
          });
        }
      });
    });
  }

  // Validate word with Oxford Dictionary
  validateWordWithOxford(word: string): Observable<OxfordValidationResponse> {
    return this.http.post<OxfordValidationResponse>(`${this.baseUrl}/words/validate`, { word: word });
  }

  // Add word to collection with validation
  addWordWithValidation(word: string): Observable<AddWordResponse> {
    return this.http.post<AddWordResponse>(`${this.baseUrl}/words/add-validated`, { word: word, skip_oxford: false });
  }

  // Add word to collection without Oxford validation
  addWord(word: string): Observable<AddWordResponse> {
    return this.http.post<AddWordResponse>(`${this.baseUrl}/words/add`, { word: word });
  }

  // Get performance statistics
  getPerformanceStats(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/performance/stats`);
  }

  // Get Oxford cache statistics
  getOxfordCacheStats(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/words/oxford-stats`);
  }

  // Expose advanced puzzle solver endpoint
  getPuzzleWords(filters: {
    pattern?: string;
    regex?: string;
    anagram?: string;
    anagram_exact?: boolean;
    limit?: number;
    sp?: string;
    ml?: string;
    sl?: string;
    rel_syn?: string;
    rel_trg?: string;
    include_datamuse?: boolean;
  }): Observable<string[]> {
    let params = new HttpParams();
    if (filters.pattern) {
      params = params.set('pattern', filters.pattern);
    }
    if (filters.regex) {
      params = params.set('regex', filters.regex);
    }
    if (filters.anagram) {
      params = params.set('anagram', filters.anagram);
    }
    if (filters.anagram_exact !== undefined) {
      params = params.set('anagram_exact', filters.anagram_exact.toString());
    }
    if (filters.limit) {
      params = params.set('limit', filters.limit.toString());
    }
    if (filters.sp) {
      params = params.set('sp', filters.sp);
    }
    if (filters.ml) {
      params = params.set('ml', filters.ml);
    }
    if (filters.sl) {
      params = params.set('sl', filters.sl);
    }
    if (filters.rel_syn) {
      params = params.set('rel_syn', filters.rel_syn);
    }
    if (filters.rel_trg) {
      params = params.set('rel_trg', filters.rel_trg);
    }
    if (filters.include_datamuse !== undefined) {
      params = params.set('include_datamuse', filters.include_datamuse.toString());
    }
    return this.http.get<string[]>(`${this.baseUrl}/words/puzzle`, { params });
  }

  // Get a random word for games
  getRandomWord(length: number = 5, startsWith?: string, endsWith?: string): Observable<any> {
    let params = new HttpParams().set('length', length.toString());
    if (startsWith) {
      params = params.set('starts_with', startsWith);
    }
    if (endsWith) {
      params = params.set('ends_with', endsWith);
    }
    return this.http.get<any>(`${this.baseUrl}/words/random`, { params });
  }

  /** Daily Safe Word — Words API random=true, definition only in UI */
  getDailySafeWord(): Observable<DailySafeWordResponse> {
    return this.http.get<DailySafeWordResponse>(`${this.baseUrl}/words-api/random`);
  }

  /** Word Game DB — categories */
  getWordGameDbCategories(): Observable<{ success: boolean; categories: string[] }> {
    return this.http.get<{ success: boolean; categories: string[] }>(
      `${this.baseUrl}/word-game-db/categories`
    );
  }

  /** Word Game DB — random word */
  getWordGameDbRandom(): Observable<DailySafeWordResponse> {
    return this.http.get<DailySafeWordResponse>(`${this.baseUrl}/word-game-db/random`);
  }

  /** Word Game DB — filtered word list */
  searchWordGameDb(params: {
    minLetters?: number;
    maxLetters?: number;
    minSyllables?: number;
    maxSyllables?: number;
    limit?: number;
    offset?: number;
    category?: string;
  }): Observable<any> {
    let httpParams = new HttpParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        httpParams = httpParams.set(key, String(value));
      }
    });
    return this.http.get<any>(`${this.baseUrl}/word-game-db/words`, { params: httpParams });
  }

  /** DataMuse word-finding query */
  queryDatamuse(params: {
    sp?: string;
    ml?: string;
    sl?: string;
    rel_syn?: string;
    rel_trg?: string;
    max?: number;
    md?: string;
  }): Observable<{ success: boolean; words: any[] }> {
    let httpParams = new HttpParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        httpParams = httpParams.set(key, String(value));
      }
    });
    return this.http.get<{ success: boolean; words: any[] }>(
      `${this.baseUrl}/datamuse/words`,
      { params: httpParams }
    );
  }

  /** DataMuse autocomplete suggestions */
  datamuseSuggest(prefix: string, max = 10): Observable<{ success: boolean; suggestions: any[] }> {
    const params = new HttpParams().set('s', prefix).set('max', String(max));
    return this.http.get<{ success: boolean; suggestions: any[] }>(
      `${this.baseUrl}/datamuse/sug`,
      { params }
    );
  }

  /** Daily scrambled-word puzzle (rotates each calendar day) */
  getDailyScramble(): Observable<DailyScrambleResponse> {
    return this.http.get<DailyScrambleResponse>(`${this.baseUrl}/puzzle/daily-scramble`);
  }

  /** Daily Safe Words to Explore — DataMuse 8-letter words, stable per day */
  getDailySafeExplore(): Observable<DailySafeExploreResponse> {
    return this.http.get<DailySafeExploreResponse>(
      `${this.baseUrl}/datamuse/daily-safe-explore`
    );
  }

  /** Daily Word Challenge — 4 education-topic words with definitions, stable per day */
  getDailyWordChallenge(): Observable<DailyWordChallengeResponse> {
    return this.http.get<DailyWordChallengeResponse>(
      `${this.baseUrl}/datamuse/daily-word-challenge`
    );
  }

  // Get storage connectivity info
  getStorageInfo(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/storage/info`);
  }

  // Trigger reload dictionary from backend storage
  reloadDictionary(): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/words/reload`, {});
  }

  // Trigger database sanitization
  cleanupDictionary(): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/words/cleanup`, { auto_remove: true });
  }

  // Remove a word from collection
  removeWord(word: string): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/words/remove`, { word: word });
  }

  // Add multiple words
  addWordsBatch(words: string[]): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/words/add-batch`, { words: words });
  }

  // Remove multiple words
  removeWordsBatch(words: string[]): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/words/remove-batch`, { words: words });
  }
}

// Interfaces for Oxford integration
export interface BasicSearchResult {
  word: string;
  inCollection: boolean;
  oxford: OxfordValidation | null;
  lookupFailed?: boolean;
}

export interface OxfordValidation {
  word: string;
  is_valid: boolean;
  definitions: string[];
  word_forms: string[];
  pronunciations?: Pronunciation[];
  examples?: string[];
  synonyms?: string[];
  etymology?: string;
  origin_language?: string;
  first_known_use?: string;
  summary?: string;
  validation_source?: string;
  links?: Record<string, string>;
  dictionary_url?: string;
  encyclopedia_url?: string;
  rhymes?: string[];
  antonyms?: string[];
  frequency?: number | null;
  frequency_details?: Record<string, unknown>;
  words_api_details?: Record<string, unknown>;
  word_game_db?: {
    category?: string;
    hint?: string;
    numLetters?: number;
    numSyllables?: number;
    _id?: string;
  };
  reason: string;
}

export interface Pronunciation {
  prefix: string;  // BrE, NAmE
  ipa: string;     // IPA notation
  url?: string;    // Audio URL
}

export interface DailySafeWordResponse {
  success: boolean;
  word: string;
  definition: string;
}

export interface DailyScrambleResponse {
  success: boolean;
  date: string;
  word: string;
  scrambled: string;
  hint: string;
  source?: string;
  cached?: boolean;
}

export interface DailySafeExploreResponse {
  success: boolean;
  date: string;
  words: string[];
  source?: string;
  cached?: boolean;
}

export interface DailyWordChallengeItem {
  word: string;
  definition: string;
}

export interface DailyWordChallengeResponse {
  success: boolean;
  date: string;
  items: DailyWordChallengeItem[];
  source?: string;
  cached?: boolean;
}

export interface AdvancedFilterResponse {
  success: boolean;
  words: string[];
  count: number;
  source?: string;
  mode?: 'browse' | 'filter';
  letterPattern?: string;
  fallback?: boolean;
  error?: string;
}

export interface OxfordValidationResponse {
  success: boolean;
  word: string;
  oxford_validation: OxfordValidation;
  message: string;
}

export interface AddWordResponse {
  success: boolean;
  word: string;
  was_new: boolean;
  oxford_validation?: OxfordValidation;
  message: string;
  total_words?: number;
}
