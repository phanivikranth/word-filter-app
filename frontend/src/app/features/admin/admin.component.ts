import { Component, OnInit } from '@angular/core';
import { TerseAppFacade } from '../../core/facades/terse-app.facade';

@Component({
  selector: 'app-admin',
  templateUrl: './admin.component.html',
})
export class AdminComponent implements OnInit {
  constructor(public vm: TerseAppFacade) {}

  ngOnInit(): void {
    this.vm.loadAdminData();
  }
}
