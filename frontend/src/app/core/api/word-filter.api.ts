import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { WordFilter } from '../../models/word.model';
import { AdvancedFilterResponse, WordService } from '../../services/word.service';

@Injectable({ providedIn: 'root' })
export class WordFilterApi {
  constructor(private readonly words: WordService) {}

  getAdvancedFilteredWords(filter: WordFilter): Observable<AdvancedFilterResponse> {
    return this.words.getAdvancedFilteredWords(filter);
  }

  getFilteredWords(filter: WordFilter): Observable<string[]> {
    return this.words.getFilteredWords(filter);
  }
}
