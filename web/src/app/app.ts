import { Component, signal, inject, OnDestroy } from '@angular/core';
import { Subscription, interval } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';

import {
  NovelInspectResponse,
  GenerateRequest,
  JobState
} from './models/novel.model';
import { NovelApiService } from './services/novel-api.service';
import { HeaderComponent } from './components/header/header.component';
import { NovelInputComponent } from './components/novel-input/novel-input.component';
import { NovelPreviewComponent } from './components/novel-preview/novel-preview.component';
import { JobStatusComponent } from './components/job-status/job-status.component';
import { IconComponent } from './components/icon/icon.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    HeaderComponent,
    NovelInputComponent,
    NovelPreviewComponent,
    JobStatusComponent,
    IconComponent
  ],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App implements OnDestroy {
  private readonly apiService = inject(NovelApiService);

  readonly novel = signal<NovelInspectResponse | null>(null);
  readonly job = signal<JobState | null>(null);
  readonly isInspecting = signal<boolean>(false);
  readonly isGenerating = signal<boolean>(false);
  readonly errorMessage = signal<string | null>(null);

  private pollSubscription?: Subscription;

  clearError(): void {
    this.errorMessage.set(null);
  }

  onInspect(url: string): void {
    this.clearError();
    this.isInspecting.set(true);

    this.apiService.inspect(url).subscribe({
      next: (response: NovelInspectResponse) => {
        this.novel.set(response);
        this.isInspecting.set(false);
      },
      error: (err: { error?: { detail?: string }; message?: string }) => {
        const detail = err.error?.detail || err.message || 'Gagal mengambil detail novel.';
        this.errorMessage.set(detail);
        this.isInspecting.set(false);
      }
    });
  }

  onStartGenerate(request: GenerateRequest): void {
    this.clearError();
    this.isGenerating.set(true);

    this.apiService.generate(request).subscribe({
      next: (initialJob: JobState) => {
        this.job.set(initialJob);
        this.startPolling(initialJob.jobId);
      },
      error: (err: { error?: { detail?: string }; message?: string }) => {
        const detail = err.error?.detail || err.message || 'Gagal memulai proses translasi.';
        this.errorMessage.set(detail);
        this.isGenerating.set(false);
      }
    });
  }

  private startPolling(jobId: string): void {
    this.pollSubscription?.unsubscribe();

    this.pollSubscription = interval(1500)
      .pipe(
        switchMap(() => this.apiService.getJobStatus(jobId)),
        takeWhile(
          (job: JobState) => job.status === 'pending' || job.status === 'running',
          true
        )
      )
      .subscribe({
        next: (job: JobState) => {
          this.job.set(job);
          if (job.status === 'completed' || job.status === 'error') {
            this.isGenerating.set(false);
          }
        },
        error: (err: { message?: string }) => {
          this.errorMessage.set(err.message || 'Gagal memantau progress translasi.');
          this.isGenerating.set(false);
        }
      });
  }

  onCancelJob(): void {
    const currentJob = this.job();
    if (currentJob && (currentJob.status === 'running' || currentJob.status === 'pending')) {
      this.apiService.cancelJob(currentJob.jobId).subscribe({
        next: (updated: JobState) => {
          this.job.set(updated);
        },
        error: (err: { message?: string }) => {
          console.warn('Failed to cancel job:', err);
        }
      });
    }
  }

  onReset(): void {
    this.pollSubscription?.unsubscribe();
    this.job.set(null);
    this.novel.set(null);
    this.isGenerating.set(false);
    this.clearError();
  }

  ngOnDestroy(): void {
    this.pollSubscription?.unsubscribe();
  }
}
