import { Component, Input, Output, EventEmitter, ChangeDetectionStrategy, inject } from '@angular/core';
import { IconComponent } from '../icon/icon.component';
import { JobState } from '../../models/novel.model';
import { NovelApiService } from '../../services/novel-api.service';

@Component({
  selector: 'app-job-status',
  standalone: true,
  imports: [IconComponent],
  templateUrl: './job-status.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class JobStatusComponent {
  @Input({ required: true }) job!: JobState;
  @Output() readonly reset = new EventEmitter<void>();
  @Output() readonly cancel = new EventEmitter<void>();

  isCancelling = false;

  private readonly apiService = inject(NovelApiService);

  get downloadFullUrl(): string | null {
    if (this.job.filename) {
      return this.apiService.getDownloadUrl(this.job.filename);
    }
    return null;
  }

  onCancel(): void {
    if (this.job.status === 'running' || this.job.status === 'pending') {
      this.isCancelling = true;
      this.cancel.emit();
    }
  }

  onReset(): void {
    this.isCancelling = false;
    this.reset.emit();
  }
}
