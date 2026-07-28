import { Component } from '@angular/core';
import { PuzzleSolverService } from './puzzle-solver.service';

@Component({
  selector: 'app-puzzles',
  templateUrl: './puzzles.component.html',
})
export class PuzzlesComponent {
  constructor(public vm: PuzzleSolverService) {}
}
