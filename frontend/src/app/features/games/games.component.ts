import { Component, OnInit } from '@angular/core';
import { TerseAppFacade } from '../../core/facades/terse-app.facade';

@Component({
  selector: 'app-games',
  templateUrl: './games.component.html',
})
export class GamesComponent implements OnInit {
  constructor(public vm: TerseAppFacade) {}

  ngOnInit(): void {
    if (!this.vm.wordleActive && !this.vm.anagramActive) {
      this.vm.startWordleGame();
    }
  }
}
