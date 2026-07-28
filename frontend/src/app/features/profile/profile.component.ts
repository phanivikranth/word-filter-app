import { Component } from '@angular/core';
import { ThemeService } from '../../core/services/theme.service';
import { ProfileSettingsService } from '../../core/services/profile-settings.service';

@Component({
  selector: 'app-profile',
  templateUrl: './profile.component.html',
})
export class ProfileComponent {
  constructor(
    public theme: ThemeService,
    public profile: ProfileSettingsService
  ) {}
}
