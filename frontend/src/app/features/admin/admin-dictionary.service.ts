import { Injectable } from '@angular/core';
import { WordService } from '../../services/word.service';
import { NotificationService } from '../../core/services/notification.service';
import { WordStatsService } from '../../core/services/word-stats.service';

@Injectable({ providedIn: 'root' })
export class AdminDictionaryService {
  storageInfo: {
    provider?: string;
    type?: string;
    region?: string;
    key?: string;
  } | null = null;
  newWordText = '';
  skipOxfordValidation = false;
  wordToRemoveText = '';
  bulkWordsText = '';
  cleanupSummary: {
    found_invalid?: number;
    removed_count?: number;
    action_taken?: string;
  } | null = null;
  isAdminProcessing = false;
  adminError = '';

  constructor(
    private readonly wordService: WordService,
    private readonly notifications: NotificationService,
    private readonly wordStats: WordStatsService
  ) {}

  loadAdminData(): void {
    this.isAdminProcessing = true;
    this.adminError = '';

    this.wordService.getStorageInfo().subscribe({
      next: (info) => {
        this.storageInfo = info;
        this.isAdminProcessing = false;
      },
      error: () => {
        this.adminError = 'Could not load storage connectivity info.';
        this.isAdminProcessing = false;
      },
    });
  }

  addNewWord(): void {
    const word = this.newWordText.trim().toLowerCase();
    if (!word) {
      this.notifications.show('Please enter a word to add.', 'error');
      return;
    }

    this.isAdminProcessing = true;
    this.adminError = '';

    const obs = this.skipOxfordValidation
      ? this.wordService.addWord(word)
      : this.wordService.addWordWithValidation(word);

    obs.subscribe({
      next: (response) => {
        this.isAdminProcessing = false;
        if (response.success) {
          this.newWordText = '';
          const msg = response.was_new
            ? `Successfully added "${word}" to database!`
            : `"${word}" already exists in database.`;
          this.notifications.show(msg, 'success');
          this.wordStats.load();
        } else {
          this.notifications.show(`Failed: ${response.message}`, 'error');
        }
      },
      error: () => {
        this.isAdminProcessing = false;
        this.notifications.show('Failed to add word to database.', 'error');
      },
    });
  }

  deleteWord(): void {
    const word = this.wordToRemoveText.trim().toLowerCase();
    if (!word) {
      this.notifications.show('Please enter a word to remove.', 'error');
      return;
    }

    this.isAdminProcessing = true;

    this.wordService.removeWord(word).subscribe({
      next: (response) => {
        this.isAdminProcessing = false;
        if (response.success) {
          this.wordToRemoveText = '';
          this.notifications.show(`Successfully deleted "${word}" from database!`, 'success');
          this.wordStats.load();
        } else {
          this.notifications.show(`Failed to delete: ${response.message}`, 'error');
        }
      },
      error: () => {
        this.isAdminProcessing = false;
        this.notifications.show('Failed to delete word. Check backend.', 'error');
      },
    });
  }

  uploadBulkWords(): void {
    if (!this.bulkWordsText.trim()) {
      this.notifications.show('Please paste some words first.', 'error');
      return;
    }

    this.isAdminProcessing = true;
    this.adminError = '';

    const words = this.bulkWordsText
      .split(/[\s,\n\r]+/)
      .map(w => w.trim().toLowerCase())
      .filter(w => w.length > 0 && /^[a-z]+$/.test(w));

    if (words.length === 0) {
      this.isAdminProcessing = false;
      this.notifications.show('No valid alphabetic words found to import.', 'error');
      return;
    }

    this.wordService.addWordsBatch(words).subscribe({
      next: (response) => {
        this.isAdminProcessing = false;
        this.bulkWordsText = '';
        this.notifications.show(
          `Import complete! Added ${response.added} new words out of ${response.total} processed.`,
          'success'
        );
        this.wordStats.load();
      },
      error: () => {
        this.isAdminProcessing = false;
        this.notifications.show('Failed to upload batch words.', 'error');
      },
    });
  }

  runSanitizationCleanup(): void {
    this.isAdminProcessing = true;
    this.cleanupSummary = null;

    this.wordService.cleanupDictionary().subscribe({
      next: (response) => {
        this.isAdminProcessing = false;
        this.cleanupSummary = response.cleanup_summary;
        this.notifications.show('Database sanitization completed!', 'success');
        this.wordStats.load();
      },
      error: () => {
        this.isAdminProcessing = false;
        this.notifications.show('Failed to run database cleanup.', 'error');
      },
    });
  }

  syncReloadStorage(): void {
    this.isAdminProcessing = true;

    this.wordService.reloadDictionary().subscribe({
      next: (response) => {
        this.isAdminProcessing = false;
        this.notifications.show(
          `Database reloaded! Loaded ${response.total_words.toLocaleString()} words.`,
          'success'
        );
        this.wordStats.load();
      },
      error: () => {
        this.isAdminProcessing = false;
        this.notifications.show('Failed to reload dictionary from storage.', 'error');
      },
    });
  }
}
