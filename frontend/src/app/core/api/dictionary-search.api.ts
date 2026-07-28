import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import {
  WordService,
  BasicSearchResult,
  AddWordResponse,
  OxfordValidationResponse,
} from '../../services/word.service';

/** Dictionary search and validation API surface. */
@Injectable({ providedIn: 'root' })
export class DictionarySearchApi {
  constructor(private readonly words: WordService) {}

  searchBasicWord(word: string): Observable<BasicSearchResult> {
    return this.words.searchBasicWord(word);
  }

  validateWordWithOxford(word: string): Observable<OxfordValidationResponse> {
    return this.words.validateWordWithOxford(word);
  }

  addWord(word: string): Observable<AddWordResponse> {
    return this.words.addWord(word);
  }

  addWordWithValidation(word: string): Observable<AddWordResponse> {
    return this.words.addWordWithValidation(word);
  }

  removeWord(word: string): Observable<unknown> {
    return this.words.removeWord(word);
  }
}
