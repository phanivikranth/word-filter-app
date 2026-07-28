import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { RouterModule } from '@angular/router';

import { AppComponent } from './app.component';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { MaterialModule } from './material.module';
import { APP_ROUTES } from './app.routes';
import { AppShellComponent } from './layout/app-shell/app-shell.component';
import { WordCheckComponent } from './features/word-check/word-check.component';
import { FiltersComponent } from './features/filters/filters.component';
import { PuzzlesComponent } from './features/puzzles/puzzles.component';
import { GamesComponent } from './features/games/games.component';
import { AdminComponent } from './features/admin/admin.component';
import { PerformanceComponent } from './features/performance/performance.component';
import { ProfileComponent } from './features/profile/profile.component';

@NgModule({
  declarations: [
    AppComponent,
    AppShellComponent,
    WordCheckComponent,
    FiltersComponent,
    PuzzlesComponent,
    GamesComponent,
    AdminComponent,
    PerformanceComponent,
    ProfileComponent,
  ],
  imports: [
    BrowserModule,
    ReactiveFormsModule,
    FormsModule,
    HttpClientModule,
    MaterialModule,
    RouterModule.forRoot(APP_ROUTES),
  ],
  providers: [provideAnimationsAsync()],
  bootstrap: [AppComponent],
})
export class AppModule {}
