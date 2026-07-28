import { Injectable } from '@angular/core';
import { WordService } from '../../services/word.service';
import { NotificationService } from '../../core/services/notification.service';
import { ClipboardService } from '../../core/services/clipboard.service';

@Injectable({ providedIn: 'root' })
export class PuzzleSolverService {
  puzzleLength: number | null = 5;

  get interactiveWordLength(): number | null {
    return this.puzzleLength;
  }

  set interactiveWordLength(value: number | null) {
    this.puzzleLength = value;
    this.onPuzzleLengthChange();
  }
  puzzlePattern = '';
  puzzleRegex = '';
  puzzleAnagram = '';
  puzzleAnagramExact = false;
  puzzleMeansLike = '';
  puzzleSoundsLike = '';
  puzzleSpelledLike = '';
  letterBoxes: string[] = [];
  interactiveWords: string[] = [];
  interactiveLoading = false;
  interactiveError = '';

  constructor(
    private readonly wordService: WordService,
    private readonly notifications: NotificationService,
    private readonly clipboard: ClipboardService
  ) {}

  copyWordToClipboard(word: string): void {
    this.clipboard.copyWord(word);
  }

  onPuzzleLengthChange(): void {
    if (this.puzzleLength && this.puzzleLength > 0) {
      this.letterBoxes = new Array(this.puzzleLength).fill('');
      this.interactiveWords = [];
      this.interactiveError = '';
    } else {
      this.letterBoxes = [];
    }
  }

  updateLetter(index: number, event: Event): void {
    const target = event.target as HTMLInputElement;
    const inputValue = target.value;
    let cleanValue = inputValue.replace(/[^a-zA-Z?@#]/g, '').toLowerCase();

    if (cleanValue.length > 1) {
      cleanValue = cleanValue.charAt(cleanValue.length - 1);
    }

    this.letterBoxes[index] = cleanValue;
    target.value = cleanValue.toUpperCase();
  }

  findMatchingWords(): void {
    if (!this.puzzleLength || this.puzzleLength <= 0) {
      this.interactiveError = 'Please enter a word length first.';
      return;
    }

    this.interactiveLoading = true;
    this.interactiveError = '';
    this.interactiveWords = [];

    const patternString = this.letterBoxes.map(letter => letter || '?').join('');
    const useDatamuse = Boolean(
      this.puzzleMeansLike || this.puzzleSoundsLike || this.puzzleSpelledLike
    );
    const datamuseSp = this.puzzleSpelledLike
      || ((!patternString.includes('@') && !patternString.includes('#')) ? patternString : undefined);

    this.wordService.getPuzzleWords({
      pattern: patternString,
      regex: this.puzzleRegex || undefined,
      anagram: this.puzzleAnagram || undefined,
      anagram_exact: this.puzzleAnagram ? this.puzzleAnagramExact : undefined,
      sp: datamuseSp || undefined,
      ml: this.puzzleMeansLike || undefined,
      sl: this.puzzleSoundsLike || undefined,
      include_datamuse: useDatamuse || Boolean(datamuseSp),
      limit: 200,
    }).subscribe({
      next: (words) => {
        this.interactiveWords = words;
        this.interactiveLoading = false;
        if (words.length === 0) {
          this.interactiveError = 'No words found matching your pattern.';
          this.notifications.show('No matching words found.', 'info');
        } else {
          this.notifications.show(`Found ${words.length} matching words!`, 'success');
        }
      },
      error: () => {
        this.interactiveError = 'Failed to find words. Make sure the backend is running.';
        this.interactiveLoading = false;
        this.notifications.show('Error loading matches. Check backend connection.', 'error');
      },
    });
  }

  clearInteractive(): void {
    this.puzzleLength = null;
    this.letterBoxes = [];
    this.interactiveWords = [];
    this.interactiveError = '';
    this.puzzlePattern = '';
    this.puzzleRegex = '';
    this.puzzleAnagram = '';
    this.puzzleAnagramExact = false;
    this.puzzleMeansLike = '';
    this.puzzleSoundsLike = '';
    this.puzzleSpelledLike = '';
    this.interactiveLoading = false;
    this.notifications.show('Puzzle filters cleared', 'info');
  }

  randomizePattern(): void {
    if (!this.puzzleLength || this.puzzleLength <= 0) {
      this.interactiveError = 'Please set a word length first.';
      return;
    }

    const letters = 'abcdefghijklmnopqrstuvwxyz';
    const wildcards = '?@#';
    const fillCount = Math.floor(Math.random() * (this.puzzleLength - 1)) + 1;
    const indices = Array.from({ length: this.puzzleLength }, (_, i) => i);
    for (let i = indices.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [indices[i], indices[j]] = [indices[j], indices[i]];
    }

    const boxContents = new Array(this.puzzleLength).fill('');
    indices.slice(0, fillCount).forEach(idx => {
      const rand = Math.random();
      boxContents[idx] = rand < 0.7
        ? letters[Math.floor(Math.random() * letters.length)]
        : wildcards[Math.floor(Math.random() * wildcards.length)];
    });

    this.letterBoxes = boxContents;
    this.puzzlePattern = boxContents.join('');
    this.interactiveWords = [];
    this.interactiveError = '';
    this.notifications.show('Random pattern generated!', 'info');
  }

  getCurrentPattern(): string {
    return this.letterBoxes.map(l => l || '?').join('').toUpperCase();
  }

  trackByIndex(index: number): number {
    return index;
  }
}
