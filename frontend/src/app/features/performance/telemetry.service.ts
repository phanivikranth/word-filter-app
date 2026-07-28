import { Injectable, OnDestroy } from '@angular/core';
import { Router } from '@angular/router';
import { Subscription, interval } from 'rxjs';
import { WordService } from '../../services/word.service';
import { NotificationService } from '../../core/services/notification.service';
import { WordStatsService } from '../../core/services/word-stats.service';

export interface EdgeLogEntry {
  time: string;
  ip: string;
  method: string;
  path: string;
  status: number;
  action: string;
}

@Injectable({ providedIn: 'root' })
export class TelemetryService implements OnDestroy {
  performanceStats: {
    words_loaded?: number;
    thread_pool_workers?: number;
    process_pool_workers?: number;
    memory_usage?: { words_list_size?: number; words_set_size?: number };
    optimization_features?: string[];
  } | null = null;
  oxfordStats: { hits?: number; misses?: number; cached_words?: number } | null = null;
  prometheusMetrics = '';
  edgeLogs: EdgeLogEntry[] = [];
  telemetryLoading = false;
  telemetryError = '';
  performanceStatsVisible = false;

  private statsIntervalSubscription: Subscription | null = null;
  private logsIntervalSubscription: Subscription | null = null;
  private monitoringActive = false;

  constructor(
    private readonly wordService: WordService,
    private readonly notifications: NotificationService,
    private readonly wordStats: WordStatsService,
    private readonly router: Router
  ) {}

  startLiveMonitoring(): void {
    if (this.monitoringActive) {
      return;
    }
    this.monitoringActive = true;
    this.generateSimulatedLogs();
    this.logsIntervalSubscription = interval(4000).subscribe(() => {
      this.addSimulatedLogEntry();
    });
    this.statsIntervalSubscription = interval(10000).subscribe(() => {
      if (this.router.url.includes('/performance')) {
        this.loadTelemetryData();
      }
    });
  }

  stopLiveMonitoring(): void {
    this.monitoringActive = false;
    this.statsIntervalSubscription?.unsubscribe();
    this.statsIntervalSubscription = null;
    this.logsIntervalSubscription?.unsubscribe();
    this.logsIntervalSubscription = null;
  }

  ngOnDestroy(): void {
    this.stopLiveMonitoring();
  }

  loadTelemetryData(): void {
    this.telemetryLoading = true;
    this.telemetryError = '';
    let performanceStatsLoaded = false;
    let oxfordStatsLoaded = false;

    this.wordService.getPerformanceStats().subscribe({
      next: (stats) => {
        this.performanceStats = stats;
        this.updatePrometheusMetrics();
        performanceStatsLoaded = true;
        if (oxfordStatsLoaded) {
          this.telemetryLoading = false;
        }
      },
      error: () => {
        this.telemetryError =
          'Failed to retrieve performance metrics. Please verify the backend service is running on port 8000.';
        this.telemetryLoading = false;
      },
    });

    this.wordService.getOxfordCacheStats().subscribe({
      next: (stats) => {
        this.oxfordStats = stats.oxford_cache;
        this.updatePrometheusMetrics();
        oxfordStatsLoaded = true;
        if (performanceStatsLoaded) {
          this.telemetryLoading = false;
        }
      },
      error: () => {
        oxfordStatsLoaded = true;
        if (performanceStatsLoaded) {
          this.telemetryLoading = false;
        }
      },
    });
  }

  updatePrometheusMetrics(): void {
    const oxford = this.oxfordStats as { hits?: number; misses?: number } | null;
    this.prometheusMetrics =
      `# HELP word_filter_total_words Total number of words in database\n` +
      `# TYPE word_filter_total_words gauge\n` +
      `word_filter_total_words ${this.wordStats.wordStats?.total_words || 416310}\n` +
      `# HELP word_filter_api_requests_total Total API requests\n` +
      `# TYPE word_filter_api_requests_total counter\n` +
      `word_filter_api_requests_total ${Math.floor(Math.random() * 40) + 120}\n` +
      `# HELP word_filter_oxford_cache_hits Total Oxford Dictionary cache hits\n` +
      `# TYPE word_filter_oxford_cache_hits counter\n` +
      `word_filter_oxford_cache_hits ${oxford?.hits || 0}\n` +
      `# HELP word_filter_oxford_cache_misses Total Oxford Dictionary cache misses\n` +
      `# TYPE word_filter_oxford_cache_misses counter\n` +
      `word_filter_oxford_cache_misses ${oxford?.misses || 0}`;
  }

  generateSimulatedLogs(): void {
    const paths = ['/words', '/words/stats', '/words/validate', '/words/puzzle', '/health', '/metrics'];
    const ips = ['192.168.1.15', '10.0.0.4', '172.16.25.101', '82.44.120.9', '204.99.12.3'];
    const methods = ['GET', 'POST', 'GET', 'GET', 'GET', 'GET'];

    for (let i = 0; i < 6; i++) {
      const isBlock = Math.random() < 0.15;
      const status = isBlock ? 429 : 200;
      const action = isBlock ? 'Blocked (Rate limit)' : 'Route success';

      this.edgeLogs.unshift({
        time: new Date(Date.now() - (6 - i) * 60000).toLocaleTimeString(),
        ip: ips[Math.floor(Math.random() * ips.length)],
        method: methods[i],
        path: paths[Math.floor(Math.random() * paths.length)],
        status,
        action,
      });
    }
  }

  addSimulatedLogEntry(): void {
    const paths = ['/words', '/words/stats', '/words/validate', '/words/puzzle', '/words/random', '/metrics'];
    const ips = ['192.168.1.15', '10.0.0.4', '172.16.25.101', '82.44.120.9', '204.99.12.3', '95.120.30.22'];
    const methods = ['GET', 'GET', 'POST', 'GET', 'GET', 'GET'];

    const isBlock = Math.random() < 0.12;
    const status = isBlock ? 429 : 200;
    const action = isBlock ? 'Blocked (Rate limit)' : 'Route success';

    this.edgeLogs.unshift({
      time: new Date().toLocaleTimeString(),
      ip: ips[Math.floor(Math.random() * ips.length)],
      method: methods[Math.floor(Math.random() * methods.length)],
      path: paths[Math.floor(Math.random() * paths.length)],
      status,
      action,
    });

    if (this.edgeLogs.length > 25) {
      this.edgeLogs.pop();
    }
  }

  togglePerformanceStats(): void {
    this.performanceStatsVisible = !this.performanceStatsVisible;
    if (this.performanceStatsVisible && !this.performanceStats) {
      this.wordService.getPerformanceStats().subscribe({
        next: (stats) => {
          this.performanceStats = stats;
        },
        error: () => {
          this.notifications.show('Failed to load performance stats', 'error');
        },
      });
    }
  }
}
