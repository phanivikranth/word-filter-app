import { Injectable } from '@angular/core';
import { WordService } from '../../services/word.service';
import { NotificationService } from '../../core/services/notification.service';
import { WordStatsService } from '../../core/services/word-stats.service';

type WordleCellStatus = 'empty' | 'correct' | 'present' | 'absent';
type WordleKeyStatus = 'correct' | 'present' | 'absent' | '';

@Injectable({ providedIn: 'root' })
export class GamesService {
  wordleActive = false;
  wordleWord = '';
  wordleGuesses: string[] = [];
  wordleCurrentGuess = '';
  wordleStatus: 'playing' | 'won' | 'lost' = 'playing';
  wordleGrid: { letter: string; status: WordleCellStatus }[][] = [];
  wordleKeyboard: Record<string, WordleKeyStatus> = {};
  wordleError = '';

  anagramActive = false;
  anagramTargetLetters = '';
  anagramUserWords: string[] = [];
  anagramWordInput = '';
  anagramValidSolutions: string[] = [];
  anagramScore = 0;
  anagramError = '';

  constructor(
    private readonly wordService: WordService,
    private readonly notifications: NotificationService,
    private readonly wordStats: WordStatsService
  ) {}

  selectGameMode(mode: 'wordle' | 'anagram'): void {
    this.wordleActive = false;
    this.anagramActive = false;
    this.wordleError = '';
    this.anagramError = '';

    if (mode === 'wordle') {
      this.startWordleGame();
    } else {
      this.startAnagramGame();
    }
  }

  startWordleGame(): void {
    this.wordleActive = true;
    this.anagramActive = false;
    this.wordleGuesses = [];
    this.wordleCurrentGuess = '';
    this.wordleStatus = 'playing';
    this.wordleError = '';
    this.wordleKeyboard = {};

    this.wordleGrid = Array.from({ length: 6 }, () =>
      Array.from({ length: 5 }, () => ({ letter: '', status: 'empty' as WordleCellStatus }))
    );

    const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    for (const char of alphabet) {
      this.wordleKeyboard[char] = '';
    }

    this.wordService.getRandomWord(5).subscribe({
      next: (res) => {
        if (res.success && res.word) {
          this.wordleWord = res.word.toUpperCase();
        } else {
          this.wordleWord = 'HAPPY';
        }
      },
      error: () => {
        this.wordleWord = 'HAPPY';
      },
    });
  }

  onWordleKeyInput(char: string): void {
    if (this.wordleStatus !== 'playing') {
      return;
    }
    this.wordleError = '';

    if (char === 'BACKSPACE') {
      if (this.wordleCurrentGuess.length > 0) {
        this.wordleCurrentGuess = this.wordleCurrentGuess.slice(0, -1);
      }
    } else if (char === 'ENTER') {
      this.submitWordleGuess();
    } else if (/^[A-Z]$/.test(char)) {
      if (this.wordleCurrentGuess.length < 5) {
        this.wordleCurrentGuess += char;
      }
    }

    const activeRowIndex = this.wordleGuesses.length;
    if (activeRowIndex < 6) {
      for (let col = 0; col < 5; col++) {
        if (col < this.wordleCurrentGuess.length) {
          this.wordleGrid[activeRowIndex][col].letter = this.wordleCurrentGuess[col];
        } else {
          this.wordleGrid[activeRowIndex][col].letter = '';
        }
      }
    }
  }

  submitWordleGuess(): void {
    const guess = this.wordleCurrentGuess.toUpperCase();
    if (guess.length !== 5) {
      this.wordleError = 'Guess must be exactly 5 letters long.';
      return;
    }

    this.wordService.searchBasicWord(guess.toLowerCase()).subscribe({
      next: (res) => {
        if (!res.inCollection) {
          this.wordleError = `"${guess}" is not in the dictionary!`;
          return;
        }
        this.processWordleGuess(guess);
      },
      error: () => {
        this.processWordleGuess(guess);
      },
    });
  }

  processWordleGuess(guess: string): void {
    const rowIndex = this.wordleGuesses.length;
    this.wordleGuesses.push(guess);
    this.wordleCurrentGuess = '';

    const target = this.wordleWord;
    const targetLettersUsed = new Array(5).fill(false);
    const rowStatus = new Array<'correct' | 'present' | 'absent'>(5).fill('absent');

    for (let i = 0; i < 5; i++) {
      if (guess[i] === target[i]) {
        rowStatus[i] = 'correct';
        targetLettersUsed[i] = true;
      }
    }

    for (let i = 0; i < 5; i++) {
      if (rowStatus[i] !== 'correct') {
        for (let j = 0; j < 5; j++) {
          if (!targetLettersUsed[j] && guess[i] === target[j]) {
            rowStatus[i] = 'present';
            targetLettersUsed[j] = true;
            break;
          }
        }
      }
    }

    for (let i = 0; i < 5; i++) {
      const status = rowStatus[i];
      const char = guess[i];

      this.wordleGrid[rowIndex][i].status = status;

      const currentKeyStatus = this.wordleKeyboard[char];
      if (status === 'correct') {
        this.wordleKeyboard[char] = 'correct';
      } else if (status === 'present' && currentKeyStatus !== 'correct') {
        this.wordleKeyboard[char] = 'present';
      } else if (status === 'absent' && currentKeyStatus === '') {
        this.wordleKeyboard[char] = 'absent';
      }
    }

    if (guess === target) {
      this.wordleStatus = 'won';
      this.notifications.show('🎉 Fantastic! You solved the Wordle!', 'success');
      this.wordStats.load();
    } else if (this.wordleGuesses.length >= 6) {
      this.wordleStatus = 'lost';
      this.notifications.show(`Game Over! The word was: ${this.wordleWord}`, 'error');
    }
  }

  startAnagramGame(): void {
    this.anagramActive = true;
    this.wordleActive = false;
    this.anagramTargetLetters = '';
    this.anagramUserWords = [];
    this.anagramWordInput = '';
    this.anagramScore = 0;
    this.anagramError = '';
    this.anagramValidSolutions = [];

    this.wordService.getRandomWord(7).subscribe({
      next: (res) => {
        if (res.success && res.word) {
          const word = res.word.toLowerCase();
          this.anagramTargetLetters = this.scrambleString(word).toUpperCase();

          this.wordService.getPuzzleWords({ anagram: word, limit: 100 }).subscribe({
            next: (solutions) => {
              this.anagramValidSolutions = solutions
                .map((s) => s.toUpperCase())
                .filter((s) => s.length >= 3);
            },
          });
        }
      },
      error: () => {
        this.anagramTargetLetters = 'TEACHER';
        this.anagramValidSolutions = [
          'TEA', 'EAT', 'ACT', 'CAT', 'HAT', 'ARE', 'ART', 'HER', 'TEACH', 'EACH', 'HATE', 'TEACHER',
        ];
      },
    });
  }

  submitAnagramWord(): void {
    const input = this.anagramWordInput.trim().toUpperCase();
    this.anagramError = '';

    if (input.length < 3) {
      this.anagramError = 'Words must be at least 3 letters long.';
      return;
    }

    if (this.anagramUserWords.includes(input)) {
      this.anagramError = 'You already found this word!';
      return;
    }

    const letters = this.anagramTargetLetters.toLowerCase();
    const word = input.toLowerCase();

    const letterCounts: Record<string, number> = {};
    for (const char of letters) {
      letterCounts[char] = (letterCounts[char] || 0) + 1;
    }

    let isValidCombination = true;
    for (const char of word) {
      if (!letterCounts[char] || letterCounts[char] <= 0) {
        isValidCombination = false;
        break;
      }
      letterCounts[char]--;
    }

    if (!isValidCombination) {
      this.anagramError = 'Can only use letters in the pool!';
      return;
    }

    if (this.anagramValidSolutions.includes(input)) {
      this.anagramUserWords.push(input);
      this.anagramWordInput = '';
      const points =
        input.length === 3 ? 100 : input.length === 4 ? 200 : input.length === 5 ? 400 : 700;
      this.anagramScore += points;
      this.notifications.show(`+${points} points for "${input}"!`, 'success');
      return;
    }

    this.wordService.searchBasicWord(word).subscribe({
      next: (res) => {
        if (res.inCollection || res.oxford?.is_valid) {
          this.anagramUserWords.push(input);
          this.anagramWordInput = '';
          const points = input.length * 100;
          this.anagramScore += points;
          this.notifications.show(`+${points} points for "${input}"!`, 'success');
        } else {
          this.anagramError = `"${input}" is not a recognized word.`;
        }
      },
      error: () => {
        this.anagramError = `"${input}" is not a recognized word.`;
      },
    });
  }

  scrambleString(str: string): string {
    const arr = str.split('');
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr.join('');
  }
}
