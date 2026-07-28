import { Injectable } from '@angular/core';
import { NotificationService } from './notification.service';

@Injectable({ providedIn: 'root' })
export class ProfileSettingsService {
  profileName = 'User';

  constructor(private readonly notifications: NotificationService) {}

  loadFromStorage(): void {
    const savedName = localStorage.getItem('profileName');
    if (savedName) {
      this.profileName = savedName;
    }
  }

  saveProfileName(name: string): void {
    this.profileName = name.trim() || 'User';
    localStorage.setItem('profileName', this.profileName);
    this.notifications.show('Profile name updated!', 'success');
  }
}
