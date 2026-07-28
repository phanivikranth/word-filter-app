import { Injectable } from '@angular/core';
import { WordService } from '../../services/word.service';
import { NotificationService } from './notification.service';
import { withWordIcons } from '../utils/word-icon.util';

@Injectable({ providedIn: 'root' })
export class DailyContentService {
  quickSuggestions: { word: string; icon: string }[] = [];
  safeExploreLoading = false;
  safeExploreError = '';

  dailySafeWord = '';
  dailySafeWordDefinition = '';
  dailySafeWordLoading = false;
  dailySafeWordError = '';

  puzzleGuess = '';
  puzzleChecked = false;
  puzzleSuccess = false;
  dailyScrambleLetters: string[] = [];
  dailyScrambleHint = '';
  dailyScrambleWord = '';
  dailyScrambleLoading = false;
  dailyScrambleError = '';

  dailyWordChallenge: { word: string; definition: string; icon: string }[] = [];
  dailyWordChallengeLoading = false;
  dailyWordChallengeError = '';

  private readonly safeExploreIcons = [
    'handshake', 'nutrition', 'share', 'support', 'favorite',
    'volunteer_activism', 'park', 'spa', 'psychology', 'shield',
  ];

  private readonly safeExploreFallback = [
    { word: 'friendly', icon: 'handshake' },
    { word: 'apple', icon: 'nutrition' },
    { word: 'share', icon: 'share' },
    { word: 'help', icon: 'support' },
    { word: 'please', icon: 'favorite' },
    { word: 'thanks', icon: 'volunteer_activism' },
    { word: 'nature', icon: 'park' },
    { word: 'gentle', icon: 'spa' },
    { word: 'empathy', icon: 'psychology' },
    { word: 'courage', icon: 'shield' },
  ];

  private readonly dailyWordChallengeFallback = [
    { word: 'terse', definition: 'sparing in the use of words; abrupt.', icon: 'edit_note' },
    { word: 'luminous', definition: 'full of or shedding light; bright or shining.', icon: 'emoji_objects' },
    { word: 'resilient', definition: 'able to withstand or recover quickly from difficult conditions.', icon: 'fitness_center' },
    { word: 'ephemeral', definition: 'lasting for a very short time.', icon: 'hourglass_empty' },
  ];

  constructor(
    private readonly wordService: WordService,
    private readonly notifications: NotificationService
  ) {}

  loadAll(): void {
    this.loadDailySafeWord();
    this.loadDailyScramble();
    this.loadDailySafeExplore();
    this.loadDailyWordChallenge();
  }

  checkPuzzleGuess(): void {
    const guess = (this.puzzleGuess || '').trim().toLowerCase();
    this.puzzleChecked = true;
    const answer = (this.dailyScrambleWord || '').trim().toLowerCase();
    if (!answer) {
      this.puzzleSuccess = false;
      this.notifications.show('Daily puzzle is still loading. Try again in a moment.', 'info');
      return;
    }
    if (guess === answer) {
      this.puzzleSuccess = true;
      const label = answer.charAt(0).toUpperCase() + answer.slice(1);
      this.notifications.show(`Correct! The word of the day is ${label}.`, 'success');
    } else {
      this.puzzleSuccess = false;
      this.notifications.show('Incorrect guess. Try again!', 'error');
    }
  }

  loadDailySafeWord(): void {
    const today = new Date().toISOString().slice(0, 10);
    const cachedDate = localStorage.getItem('dailySafeWordDate');
    const cachedDefinition = localStorage.getItem('dailySafeWordDefinition');
    const cachedWord = localStorage.getItem('dailySafeWord');

    if (cachedDate === today && cachedDefinition && cachedWord) {
      this.dailySafeWord = cachedWord;
      this.dailySafeWordDefinition = cachedDefinition;
      return;
    }

    this.dailySafeWordLoading = true;
    this.dailySafeWordError = '';
    this.wordService.getDailySafeWord().subscribe({
      next: (res) => {
        this.dailySafeWordLoading = false;
        if (res.success && res.definition && res.word) {
          this.dailySafeWord = res.word;
          this.dailySafeWordDefinition = res.definition;
          localStorage.setItem('dailySafeWordDate', today);
          localStorage.setItem('dailySafeWord', res.word);
          localStorage.setItem('dailySafeWordDefinition', res.definition);
        } else {
          this.dailySafeWordError = 'Could not load today\'s word.';
        }
      },
      error: () => {
        this.dailySafeWordLoading = false;
        this.dailySafeWordError =
          'Words API unavailable. Add your RapidAPI key to enable Daily Safe Word.';
      },
    });
  }

  loadDailyWordChallenge(): void {
    const today = new Date().toISOString().slice(0, 10);
    const cachedDate = localStorage.getItem('dailyWordChallengeDate');
    const cachedItems = localStorage.getItem('dailyWordChallengeItems');

    if (cachedDate === today && cachedItems) {
      try {
        this.dailyWordChallenge = JSON.parse(cachedItems);
        return;
      } catch {
        localStorage.removeItem('dailyWordChallengeItems');
      }
    }

    this.dailyWordChallengeLoading = true;
    this.dailyWordChallengeError = '';
    this.wordService.getDailyWordChallenge().subscribe({
      next: (res) => {
        this.dailyWordChallengeLoading = false;
        if (res.success && res.items?.length) {
          this.dailyWordChallenge = withWordIcons(res.items);
          localStorage.setItem('dailyWordChallengeDate', today);
          localStorage.setItem(
            'dailyWordChallengeItems',
            JSON.stringify(this.dailyWordChallenge)
          );
        } else {
          this.dailyWordChallenge = [...this.dailyWordChallengeFallback];
          this.dailyWordChallengeError = 'Could not load today\'s word challenge.';
        }
      },
      error: () => {
        this.dailyWordChallengeLoading = false;
        this.dailyWordChallenge = [...this.dailyWordChallengeFallback];
        this.dailyWordChallengeError = 'Word challenge unavailable. Using defaults.';
      },
    });
  }

  loadDailySafeExplore(): void {
    const today = new Date().toISOString().slice(0, 10);
    const cachedDate = localStorage.getItem('dailySafeExploreDate');
    const cachedWords = localStorage.getItem('dailySafeExploreWords');

    if (cachedDate === today && cachedWords) {
      try {
        this.quickSuggestions = JSON.parse(cachedWords);
        return;
      } catch {
        localStorage.removeItem('dailySafeExploreWords');
      }
    }

    this.safeExploreLoading = true;
    this.safeExploreError = '';
    this.wordService.getDailySafeExplore().subscribe({
      next: (res) => {
        this.safeExploreLoading = false;
        if (res.success && res.words?.length) {
          this.quickSuggestions = res.words.map((word, index) => ({
            word,
            icon: this.safeExploreIcons[index % this.safeExploreIcons.length],
          }));
          localStorage.setItem('dailySafeExploreDate', today);
          localStorage.setItem(
            'dailySafeExploreWords',
            JSON.stringify(this.quickSuggestions)
          );
        } else {
          this.quickSuggestions = [...this.safeExploreFallback];
          this.safeExploreError = 'Could not load today\'s explore words.';
        }
      },
      error: () => {
        this.safeExploreLoading = false;
        this.quickSuggestions = [...this.safeExploreFallback];
        this.safeExploreError = 'Explore words unavailable. Using defaults.';
      },
    });
  }

  loadDailyScramble(): void {
    const today = new Date().toISOString().slice(0, 10);
    const cachedDate = localStorage.getItem('dailyScrambleDate');
    const cachedWord = localStorage.getItem('dailyScrambleWord');
    const cachedScrambled = localStorage.getItem('dailyScrambleScrambled');
    const cachedHint = localStorage.getItem('dailyScrambleHint');

    if (cachedDate === today && cachedWord && cachedScrambled) {
      this.dailyScrambleWord = cachedWord;
      this.dailyScrambleLetters = cachedScrambled.toUpperCase().split('');
      this.dailyScrambleHint = cachedHint || '';
      return;
    }

    this.dailyScrambleLoading = true;
    this.dailyScrambleError = '';
    this.wordService.getDailyScramble().subscribe({
      next: (res) => {
        this.dailyScrambleLoading = false;
        if (res.success && res.word && res.scrambled) {
          this.dailyScrambleWord = res.word.toLowerCase();
          this.dailyScrambleLetters = res.scrambled.toUpperCase().split('');
          this.dailyScrambleHint = res.hint || '';
          localStorage.setItem('dailyScrambleDate', today);
          localStorage.setItem('dailyScrambleWord', this.dailyScrambleWord);
          localStorage.setItem('dailyScrambleScrambled', res.scrambled);
          localStorage.setItem('dailyScrambleHint', this.dailyScrambleHint);
        } else {
          this.dailyScrambleError = 'Could not load today\'s puzzle.';
        }
      },
      error: (err) => {
        this.dailyScrambleLoading = false;
        const status = err?.status;
        const detail = err?.error?.detail;
        if (status === 404) {
          this.dailyScrambleError =
            'Daily puzzle endpoint not found. Restart the backend to load the latest code.';
        } else if (status === 503 && detail) {
          this.dailyScrambleError = String(detail);
        } else if (status === 0) {
          this.dailyScrambleError =
            'Cannot reach the backend. Start it on port 8000 and refresh.';
        } else {
          this.dailyScrambleError =
            detail || 'Daily puzzle unavailable. Check that the backend is running.';
        }
      },
    });
  }
}
