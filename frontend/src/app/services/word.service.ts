import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
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
    return new Observable(observer => {
      // First, check if word exists in our collection
      this.checkWordInCollection(word).subscribe({
        next: (inCollection) => {
          // Then, get Oxford Dictionary details
          this.validateWordWithOxford(word).subscribe({
            next: (oxfordResult) => {
              const result: BasicSearchResult = {
                word: word.toLowerCase(),
                inCollection: inCollection,
                oxford: oxfordResult.oxford_validation
              };
              observer.next(result);
              observer.complete();
            },
            error: (error) => {
              // Even if Oxford fails, we can still show collection status
              const result: BasicSearchResult = {
                word: word.toLowerCase(),
                inCollection: inCollection,
                oxford: null
              };
              observer.next(result);
              observer.complete();
            }
          });
        },
        error: (error) => {
          observer.error(error);
        }
      });
    });
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
