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

  private readonly apiService = inject(NovelApiService);

  get downloadFullUrl(): string | null {
    if (this.job.filename) {
      return this.apiService.getDownloadUrl(this.job.filename);
    }
    return null;
  }

  onReset(): void {
    this.reset.emit();
  }
}
