import { Component, OnInit } from '@angular/core';
import { TerseAppFacade } from '../../core/facades/terse-app.facade';

@Component({
  selector: 'app-word-check',
  templateUrl: './word-check.component.html',
})
export class WordCheckComponent implements OnInit {
  constructor(public vm: TerseAppFacade) {}

  ngOnInit(): void {
    // Daily widgets for this view are loaded once in AppShell initApp.
  }
}
