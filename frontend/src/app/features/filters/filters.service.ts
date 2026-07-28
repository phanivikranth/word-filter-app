import { Injectable } from '@angular/core';
import { FormBuilder, FormGroup } from '@angular/forms';
import { WordFilter } from '../../models/word.model';
import { WordService } from '../../services/word.service';
import { ClipboardService } from '../../core/services/clipboard.service';

@Injectable({ providedIn: 'root' })
export class FiltersService {
  filterForm: FormGroup;
  words: string[] = [];
  loading = false;
  error = '';
  advancedFilterSource = '';
  advancedFilterMode: 'browse' | 'filter' = 'browse';

  constructor(
    private readonly fb: FormBuilder,
    private readonly wordService: WordService,
    private readonly clipboard: ClipboardService
  ) {
    this.filterForm = this.fb.group({
      contains: [''],
      starts_with: [''],
      ends_with: [''],
      min_length: [''],
      max_length: [''],
      exact_length: [''],
      limit: [100],
    });
  }

  searchWords(): void {
    this.loading = true;
    this.error = '';
    this.advancedFilterSource = '';

    const filterValues = this.filterForm.value;
    const filter: WordFilter = { limit: filterValues.limit || 100 };

    Object.keys(filterValues).forEach(key => {
      const value = filterValues[key];
      if (value !== null && value !== '' && value !== undefined && key !== 'limit') {
        filter[key as keyof WordFilter] = value;
      }
    });

    this.wordService.getAdvancedFilteredWords(filter).subscribe({
      next: (response) => {
        this.words = response.words || [];
        this.advancedFilterSource = response.source || '';
        this.advancedFilterMode = response.mode === 'filter' ? 'filter' : 'browse';
        this.loading = false;
      },
      error: (error) => {
        this.error = error?.error?.detail || 'Failed to search words. Make sure the backend is running.';
        this.loading = false;
      },
    });
  }

  clearFilters(): void {
    this.filterForm.reset();
    this.filterForm.patchValue({ limit: 100 });
    this.searchWords();
  }

  onFilterChange(): void {
    this.searchWords();
  }

  copyWordToClipboard(word: string): void {
    this.clipboard.copyWord(word);
  }
}
