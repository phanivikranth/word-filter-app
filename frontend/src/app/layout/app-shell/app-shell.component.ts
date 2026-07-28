import { Component, OnDestroy, OnInit } from '@angular/core';
import { ThemeService } from '../../core/services/theme.service';
import { DailyContentService } from '../../core/services/daily-content.service';
import { AppInitService } from '../../core/services/app-init.service';

@Component({
  selector: 'app-shell',
  templateUrl: './app-shell.component.html',
})
export class AppShellComponent implements OnInit, OnDestroy {
  constructor(
    public theme: ThemeService,
    public daily: DailyContentService,
    private readonly appInit: AppInitService
  ) {}

  ngOnInit(): void {
    this.appInit.init();
  }

  ngOnDestroy(): void {
    this.appInit.ngOnDestroy();
  }

  navLinkClass(active: boolean): string {
    return active
      ? 'text-primary dark:text-primary-fixed border-b-2 border-primary dark:border-primary-fixed'
      : 'text-on-surface-variant dark:text-on-surface-variant hover:text-primary dark:hover:text-primary-fixed';
  }

  mobileTabClass(active: boolean): string {
    return active ? 'bg-primary text-on-primary' : 'bg-surface-container text-on-surface-variant';
  }
}
