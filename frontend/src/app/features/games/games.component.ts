import { Component } from '@angular/core';
import { GamesService } from './games.service';

@Component({
  selector: 'app-games',
  templateUrl: './games.component.html',
})
export class GamesComponent {
  constructor(public vm: GamesService) {}
}
