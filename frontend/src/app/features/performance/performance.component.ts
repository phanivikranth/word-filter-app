import { Component, OnInit } from '@angular/core';
import { TelemetryService } from './telemetry.service';

@Component({
  selector: 'app-performance',
  templateUrl: './performance.component.html',
})
export class PerformanceComponent implements OnInit {
  constructor(public vm: TelemetryService) {}

  ngOnInit(): void {
    this.vm.loadTelemetryData();
  }
}
