import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { WordService, BasicSearchResult, OxfordValidation } from '../../services/word.service';
import { NotificationService } from '../../core/services/notification.service';
import { WordStatsService } from '../../core/services/word-stats.service';
import {
  getDictionaryLinks,
  getValidationSourceLabel,
  hasDictionaryContent,
  hasWordOrigin,
  playPronunciation,
  showSummary,
} from '../../core/utils/dictionary-display.util';

@Injectable({ providedIn: 'root' })
export class WordCheckService {
  searchWord = '';
  searchResult: BasicSearchResult | null = null;
  isSearching = false;
  searchError = '';

  readonly getValidationSourceLabel = getValidationSourceLabel;
  readonly hasDictionaryContent = hasDictionaryContent;
  readonly showSummary = showSummary;
  readonly getDictionaryLinks = getDictionaryLinks;
  readonly hasWordOrigin = hasWordOrigin;
  readonly playPronunciation = playPronunciation;

  constructor(
    private readonly wordService: WordService,
    private readonly notifications: NotificationService,
    private readonly wordStats: WordStatsService,
    private readonly router: Router
  ) {}

  onSearchInput(): void {
    if (this.searchResult) {
      this.searchResult = null;
    }
    if (this.searchError) {
      this.searchError = '';
    }
  }

  searchWordBasic(): void {
    const cleanWord = (this.searchWord || '').trim();
    if (!cleanWord) {
      this.searchError = 'Please enter a word to search.';
      return;
    }

    if (!/^[a-zA-Z]+$/.test(cleanWord)) {
      this.searchError = 'Word must contain only letters.';
      return;
    }

    this.isSearching = true;
    this.searchError = '';
    this.searchResult = null;

    this.wordService.searchBasicWord(cleanWord).subscribe({
      next: (result) => {
        this.searchResult = result;
        this.isSearching = false;
        if (result.lookupFailed && !result.oxford) {
          this.searchError =
            'Dictionary lookup failed. The backend could not reach the database — trying live sources may still work after a refresh.';
          this.notifications.show(this.searchError, 'error');
          return;
        }
        if (result.oxford || result.inCollection) {
          this.notifications.show(`Found details for "${result.word}"!`, 'success');
        } else {
          this.searchError = `No dictionary entry found for "${result.word}".`;
          this.notifications.show(this.searchError, 'info');
        }
      },
      error: () => {
        this.searchError = 'Failed to search word. Please check your connection and try again.';
        this.isSearching = false;
        this.notifications.show('Error searching for word. Check backend connection.', 'error');
      },
    });
  }

  exploreWord(word: string): void {
    this.searchWord = word;
    void this.router.navigateByUrl('/word-check').then(() => {
      this.searchWordBasic();
      this.notifications.show(`Searching for "${word}"...`, 'info');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  addWordToCollection(word: string): void {
    this.wordService.addWordWithValidation(word).subscribe({
      next: (response) => {
        if (response.success) {
          this.searchWord = word;
          this.searchWordBasic();
          this.wordStats.load();
        } else {
          this.searchError = response.message || 'Word is invalid';
        }
      },
      error: () => {
        this.searchError = 'Failed to add word to collection';
      },
    });
  }

  checkPuzzleGuess(
    puzzleGuess: string,
    dailyScrambleWord: string,
    onResult: (success: boolean) => void
  ): void {
    const guess = (puzzleGuess || '').trim().toLowerCase();
    const answer = (dailyScrambleWord || '').trim().toLowerCase();
    if (!answer) {
      onResult(false);
      this.notifications.show('Daily puzzle is still loading. Try again in a moment.', 'info');
      return;
    }
    if (guess === answer) {
      onResult(true);
      const label = answer.charAt(0).toUpperCase() + answer.slice(1);
      this.notifications.show(`Correct! The word of the day is ${label}.`, 'success');
    } else {
      onResult(false);
      this.notifications.show('Incorrect guess. Try again!', 'error');
    }
  }
}
