import { Component, OnDestroy, OnInit } from '@angular/core';
import { TerseAppFacade } from '../../core/facades/terse-app.facade';

@Component({
  selector: 'app-shell',
  templateUrl: './app-shell.component.html',
})
export class AppShellComponent implements OnInit, OnDestroy {
  constructor(public vm: TerseAppFacade) {}

  ngOnInit(): void {
    this.vm.initApp();
  }

  ngOnDestroy(): void {
    this.vm.ngOnDestroy();
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
