import { Component, EventEmitter, Input, Output, ChangeDetectionStrategy } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../icon/icon.component';
import {
  NovelInspectResponse,
  RangeType,
  TranslationMode,
  TargetLanguage,
  GenerateRequest
} from '../../models/novel.model';

@Component({
  selector: 'app-novel-preview',
  standalone: true,
  imports: [FormsModule, IconComponent],
  templateUrl: './novel-preview.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NovelPreviewComponent {
  @Input({ required: true }) novel!: NovelInspectResponse;
  @Input() isGenerating = false;
  @Output() readonly startGenerate = new EventEmitter<GenerateRequest>();

  rangeType: RangeType = 'current';
  customRange = '1-5';
  mode: TranslationMode = 'translated';
  targetLang: TargetLanguage = 'en';
  forceTranslate = false;

  ngOnInit(): void {
    // If no episode in URL, default to range or all
    if (!this.novel.currentEpisodeId) {
      this.rangeType = 'range';
    }
  }

  setRangeType(type: RangeType): void {
    this.rangeType = type;
  }

  setMode(mode: TranslationMode): void {
    this.mode = mode;
  }

  setTargetLang(lang: TargetLanguage): void {
    this.targetLang = lang;
  }

  onGenerate(): void {
    if (this.isGenerating) {
      return;
    }
    const request: GenerateRequest = {
      url: this.novel.url,
      rangeType: this.rangeType,
      customRange: this.rangeType === 'range' ? this.customRange.trim() : undefined,
      mode: this.mode,
      targetLang: this.targetLang,
      forceTranslate: this.forceTranslate
    };
    this.startGenerate.emit(request);
  }
}
