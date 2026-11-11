import { Component, EventEmitter, Output, Input, ChangeDetectionStrategy } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../icon/icon.component';

@Component({
  selector: 'app-novel-input',
  standalone: true,
  imports: [FormsModule, IconComponent],
  templateUrl: './novel-input.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NovelInputComponent {
  @Input() isLoading = false;
  @Output() readonly inspect = new EventEmitter<string>();

  url = '';

  readonly defaultExampleUrl =
    'https://kakuyomu.jp/works/2912051607243271731/episodes/2912051607330854893';

  setExample(): void {
    this.url = this.defaultExampleUrl;
  }

  onSubmit(): void {
    const trimmed = this.url.trim();
    if (trimmed && !this.isLoading) {
      this.inspect.emit(trimmed);
    }
  }
}
