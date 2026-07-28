import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import {
  DailyScrambleResponse,
  DailySafeExploreResponse,
  DailyWordChallengeResponse,
  WordService,
} from '../../services/word.service';

@Injectable({ providedIn: 'root' })
export class DatamuseDailyApi {
  constructor(private readonly words: WordService) {}

  getDailySafeExplore(): Observable<DailySafeExploreResponse> {
    return this.words.getDailySafeExplore();
  }

  getDailyWordChallenge(): Observable<DailyWordChallengeResponse> {
    return this.words.getDailyWordChallenge();
  }

  getDailySafeWord(): Observable<{ success: boolean; word: string; definition: string }> {
    return this.words.getDailySafeWord();
  }

  getDailyScramble(): Observable<DailyScrambleResponse> {
    return this.words.getDailyScramble();
  }
}
