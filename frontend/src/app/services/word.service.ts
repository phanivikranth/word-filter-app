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
          catchError(() => {
            // Even if Oxford fails, return collection status
            return of({
              word: cleanWord,
              inCollection,
              oxford: null
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
  getPuzzleWords(filters: {pattern?: string, regex?: string, anagram?: string, anagram_exact?: boolean, limit?: number}): Observable<string[]> {
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
}

export interface OxfordValidation {
  word: string;
  is_valid: boolean;
  definitions: string[];
  word_forms: string[];
  pronunciations?: Pronunciation[];
  examples?: string[];
  synonyms?: string[];
  reason: string;
}

export interface Pronunciation {
  prefix: string;  // BrE, NAmE
  ipa: string;     // IPA notation
  url?: string;    // Audio URL
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
