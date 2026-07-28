import { Component, OnInit } from '@angular/core';
import { AdminDictionaryService } from './admin-dictionary.service';

@Component({
  selector: 'app-admin',
  templateUrl: './admin.component.html',
})
export class AdminComponent implements OnInit {
  constructor(public vm: AdminDictionaryService) {}

  ngOnInit(): void {
    this.vm.loadAdminData();
  }
}
