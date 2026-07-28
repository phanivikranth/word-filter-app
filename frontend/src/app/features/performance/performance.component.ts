import { Component, OnInit } from '@angular/core';
import { TerseAppFacade } from '../../core/facades/terse-app.facade';

@Component({
  selector: 'app-performance',
  templateUrl: './performance.component.html',
})
export class PerformanceComponent implements OnInit {
  constructor(public vm: TerseAppFacade) {}

  ngOnInit(): void {
    this.vm.loadTelemetryData();
  }
}
