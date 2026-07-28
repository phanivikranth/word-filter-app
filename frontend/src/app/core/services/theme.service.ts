import { Injectable } from '@angular/core';
import { NotificationService } from './notification.service';

export interface FontOption {
  id: string;
  name: string;
  cssClass: string;
  preview: string;
}

@Injectable({ providedIn: 'root' })
export class ThemeService {
  isDarkMode = false;
  activeTheme = 'blue';
  activeFont = 'dm-sans';
  isClaymorphic = false;

  readonly fontOptions: FontOption[] = [
    { id: 'dm-sans', name: 'DM Sans', cssClass: '', preview: 'Terse' },
    { id: 'lora', name: 'Lora', cssClass: 'font-lora', preview: 'Terse' },
  ];

  constructor(private readonly notifications: NotificationService) {}

  initAppearance(): void {
    this.isDarkMode = localStorage.getItem('theme') === 'dark';
    document.documentElement.classList.remove('dark');
    if (this.isDarkMode) {
      document.documentElement.classList.add('dark');
    }

    this.isClaymorphic = localStorage.getItem('isClaymorphic') === 'true';
    this.updateDesignClass();

    const savedTheme = localStorage.getItem('activeTheme') || 'blue';
    const savedFont = localStorage.getItem('activeFont') || 'dm-sans';
    this.changeFont(savedFont);
    this.changeTheme(savedTheme);
  }

  toggleTheme(): void {
    this.isDarkMode = !this.isDarkMode;
    document.documentElement.classList.toggle('dark', this.isDarkMode);
    localStorage.setItem('theme', this.isDarkMode ? 'dark' : 'light');
    this.notifications.show(
      `Switched to ${this.isDarkMode ? 'dark' : 'light'} mode`,
      'info'
    );
  }

  changeTheme(theme: string): void {
    this.activeTheme = theme;
    const themesList = ['theme-green', 'theme-indigo', 'theme-amber', 'theme-rose', 'theme-violet', 'theme-slate', 'theme-teal'];
    themesList.forEach(t => document.documentElement.classList.remove(t));

    if (theme !== 'blue') {
      document.documentElement.classList.add(`theme-${theme}`);
    }
    localStorage.setItem('activeTheme', theme);
    this.notifications.show(`Theme changed to ${theme.charAt(0).toUpperCase() + theme.slice(1)}`, 'success');
  }

  changeFont(fontId: string): void {
    this.activeFont = fontId;
    const fontClasses = ['font-lora'];
    fontClasses.forEach(f => document.documentElement.classList.remove(f));

    const selected = this.fontOptions.find(f => f.id === fontId);
    if (selected?.cssClass) {
      document.documentElement.classList.add(selected.cssClass);
    }
    localStorage.setItem('activeFont', fontId);
  }

  toggleClaymorphic(): void {
    this.isClaymorphic = !this.isClaymorphic;
    localStorage.setItem('isClaymorphic', String(this.isClaymorphic));
    this.updateDesignClass();
    this.notifications.show(
      `Switched to ${this.isClaymorphic ? 'Claymorphic' : 'Normal'} style`,
      'success'
    );
  }

  updateDesignClass(): void {
    const root = document.documentElement;
    if (this.isClaymorphic) {
      root.classList.add('design-clay');
    } else {
      root.classList.remove('design-clay');
    }
  }
}
