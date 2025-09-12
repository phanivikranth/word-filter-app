import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { WordFilter, WordStats, WordsByLength } from '../models/word.model';

@Injectable({
  providedIn: 'root'
})
export class WordService {
  private baseUrl = 'http://localhost:8001';

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
}
