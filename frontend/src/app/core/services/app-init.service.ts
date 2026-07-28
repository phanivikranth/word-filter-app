import { Injectable, OnDestroy } from '@angular/core';
import { ThemeService } from './theme.service';
import { ProfileSettingsService } from './profile-settings.service';
import { WordStatsService } from './word-stats.service';
import { DailyContentService } from './daily-content.service';
import { PuzzleSolverService } from '../../features/puzzles/puzzle-solver.service';
import { TelemetryService } from '../../features/performance/telemetry.service';

@Injectable({ providedIn: 'root' })
export class AppInitService implements OnDestroy {
  constructor(
    private readonly theme: ThemeService,
    private readonly profile: ProfileSettingsService,
    private readonly wordStats: WordStatsService,
    private readonly daily: DailyContentService,
    private readonly puzzleSolver: PuzzleSolverService,
    private readonly telemetry: TelemetryService
  ) {}

  init(): void {
    this.theme.initAppearance();
    this.profile.loadFromStorage();
    this.wordStats.load();
    this.puzzleSolver.onPuzzleLengthChange();
    this.daily.loadAll();
    this.telemetry.startLiveMonitoring();
  }

  ngOnDestroy(): void {
    this.telemetry.stopLiveMonitoring();
  }
}
