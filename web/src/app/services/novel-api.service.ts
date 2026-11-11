import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  NovelInspectResponse,
  GenerateRequest,
  JobState
} from '../models/novel.model';

@Injectable({
  providedIn: 'root'
})
export class NovelApiService {
  private readonly http = inject(HttpClient);

  // Auto-detect port: if running on port 4200 (ng serve), point to port 8000.
  // Otherwise use relative /api (works on localhost:8000 and mobile LAN).
  private readonly baseUrl =
    typeof window !== 'undefined' && window.location.port === '4200'
      ? 'http://localhost:8000/api'
      : '/api';

  inspect(url: string): Observable<NovelInspectResponse> {
    return this.http.post<NovelInspectResponse>(`${this.baseUrl}/novel/inspect`, { url });
  }

  generate(request: GenerateRequest): Observable<JobState> {
    return this.http.post<JobState>(`${this.baseUrl}/novel/generate`, request);
  }

  getJobStatus(jobId: string): Observable<JobState> {
    return this.http.get<JobState>(`${this.baseUrl}/jobs/${jobId}`);
  }

  cancelJob(jobId: string): Observable<JobState> {
    return this.http.post<JobState>(`${this.baseUrl}/jobs/${jobId}/cancel`, {});
  }

  getDownloadUrl(filename: string): string {
    return `${this.baseUrl}/download/${encodeURIComponent(filename)}`;
  }
}
