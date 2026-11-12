export interface EpisodeItem {
  index: number;
  id: string;
  title: string;
  date: string;
}

export interface NovelInspectResponse {
  workId: string;
  currentEpisodeId: string | null;
  currentEpisodeIndex: number | null;
  titleJa: string;
  titleEn: string | null;
  titleId?: string | null;
  authorJa: string;
  authorEn: string | null;
  authorId?: string | null;
  synopsis: string;
  synopsisEn?: string | null;
  url: string;
  totalEpisodes: number;
  episodes: EpisodeItem[];
}

export type RangeType = 'current' | 'range' | 'all';
export type TranslationMode = 'translated' | 'bilingual' | 'raw';
export type TargetLanguage = 'en' | 'en_polished' | 'id';

export interface GenerateRequest {
  url: string;
  rangeType: RangeType;
  customRange?: string;
  mode: TranslationMode;
  targetLang?: TargetLanguage;
  forceTranslate?: boolean;
}

export type JobStatus = 'pending' | 'running' | 'completed' | 'error';

export interface JobState {
  jobId: string;
  status: JobStatus;
  progressPercent: number;
  currentChapter: number;
  totalChapters: number;
  chapterTitle: string;
  paragraphsDone: number;
  paragraphsTotal: number;
  message: string;
  downloadUrl: string | null;
  filename: string | null;
  error: string | null;
  cancelled?: boolean;
}

