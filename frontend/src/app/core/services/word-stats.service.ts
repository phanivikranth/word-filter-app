import { Injectable } from '@angular/core';
import { WordService } from '../../services/word.service';
import { WordStats } from '../../models/word.model';

@Injectable({ providedIn: 'root' })
export class WordStatsService {
  wordStats: WordStats | null = null;
  loadError = '';

  constructor(private readonly wordService: WordService) {}

  load(): void {
    this.wordService.getWordStats().subscribe({
      next: (stats) => {
        this.wordStats = stats;
      },
      error: () => {
        this.loadError = 'Failed to load word statistics';
      },
    });
  }
}
