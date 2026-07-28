import { Component } from '@angular/core';
import { WordCheckService } from './word-check.service';
import { DailyContentService } from '../../core/services/daily-content.service';

@Component({
  selector: 'app-word-check',
  templateUrl: './word-check.component.html',
})
export class WordCheckComponent {
  constructor(
    public vm: WordCheckService,
    public daily: DailyContentService
  ) {}
}
