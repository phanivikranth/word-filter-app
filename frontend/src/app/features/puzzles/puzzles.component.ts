import { Component, OnInit } from '@angular/core';
import { TerseAppFacade } from '../../core/facades/terse-app.facade';

@Component({
  selector: 'app-puzzles',
  templateUrl: './puzzles.component.html',
})
export class PuzzlesComponent implements OnInit {
  constructor(public vm: TerseAppFacade) {}

  ngOnInit(): void {
    this.vm.onPuzzleLengthChange();
  }
}
