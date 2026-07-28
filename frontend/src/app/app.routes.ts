import { Routes } from '@angular/router';
import { WordCheckComponent } from './features/word-check/word-check.component';
import { FiltersComponent } from './features/filters/filters.component';
import { PuzzlesComponent } from './features/puzzles/puzzles.component';
import { GamesComponent } from './features/games/games.component';
import { AdminComponent } from './features/admin/admin.component';
import { PerformanceComponent } from './features/performance/performance.component';
import { ProfileComponent } from './features/profile/profile.component';

export const APP_ROUTES: Routes = [
  { path: '', redirectTo: 'word-check', pathMatch: 'full' },
  { path: 'word-check', component: WordCheckComponent },
  { path: 'filters', component: FiltersComponent },
  { path: 'puzzles', component: PuzzlesComponent },
  { path: 'games', component: GamesComponent },
  { path: 'admin', component: AdminComponent },
  { path: 'performance', component: PerformanceComponent },
  { path: 'profile', component: ProfileComponent },
  { path: '**', redirectTo: 'word-check' },
];
