import { Injectable } from '@angular/core';
import { NotificationService } from './notification.service';

@Injectable({ providedIn: 'root' })
export class ClipboardService {
  constructor(private readonly notifications: NotificationService) {}

  copyWord(word: string): void {
    navigator.clipboard.writeText(word).then(() => {
      this.notifications.show(`"${word}" copied to clipboard!`, 'success');
    }).catch(() => {
      this.notifications.show('Failed to copy to clipboard', 'error');
    });
  }
}
