import AsyncStorage from '@react-native-async-storage/async-storage';
import { File, Paths } from 'expo-file-system';
import * as Sharing from 'expo-sharing';
import { GenerateRequest, JobState, NovelInspectResponse } from '../types';

const STORAGE_SERVER_KEY = '@novel_tl_server_url';
export const DEFAULT_SERVER_URL = 'http://192.168.100.76:8000';

let cachedServerUrl: string | null = null;

export async function getServerUrl(): Promise<string> {
  if (cachedServerUrl) return cachedServerUrl;
  try {
    const saved = await AsyncStorage.getItem(STORAGE_SERVER_KEY);
    if (saved && saved.trim()) {
      cachedServerUrl = saved.trim().replace(/\/+$/, '');
      return cachedServerUrl;
    }
  } catch (err) {
    console.warn('Error reading server URL from storage:', err);
  }
  cachedServerUrl = DEFAULT_SERVER_URL;
  return cachedServerUrl;
}

export async function setServerUrl(url: string): Promise<void> {
  const cleanUrl = url.trim().replace(/\/+$/, '');
  cachedServerUrl = cleanUrl;
  await AsyncStorage.setItem(STORAGE_SERVER_KEY, cleanUrl);
}

export async function testServerConnection(url: string): Promise<boolean> {
  try {
    const cleanUrl = url.trim().replace(/\/+$/, '');
    const ctrl = new AbortController();
    const timeoutId = setTimeout(() => ctrl.abort(), 3000);
    const resp = await fetch(`${cleanUrl}/api/health`, {
      method: 'GET',
      signal: ctrl.signal,
    });
    clearTimeout(timeoutId);
    return resp.ok;
  } catch (err) {
    return false;
  }
}

export async function inspectNovel(novelUrl: string): Promise<NovelInspectResponse> {
  const base = await getServerUrl();
  const resp = await fetch(`${base}/api/novel/inspect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url: novelUrl }),
  });
  if (!resp.ok) {
    const errData = await resp.json().catch(() => null);
    throw new Error(errData?.detail || `Gagal mengambil novel (HTTP ${resp.status})`);
  }
  return resp.json();
}

export async function generateNovel(request: GenerateRequest): Promise<JobState> {
  const base = await getServerUrl();
  const resp = await fetch(`${base}/api/novel/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!resp.ok) {
    const errData = await resp.json().catch(() => null);
    throw new Error(errData?.detail || `Gagal memulai translasi (HTTP ${resp.status})`);
  }
  return resp.json();
}

export async function getJobStatus(jobId: string): Promise<JobState> {
  const base = await getServerUrl();
  const resp = await fetch(`${base}/api/jobs/${jobId}`);
  if (!resp.ok) {
    throw new Error(`Job status error (HTTP ${resp.status})`);
  }
  return resp.json();
}

export async function cancelJob(jobId: string): Promise<JobState> {
  const base = await getServerUrl();
  const resp = await fetch(`${base}/api/jobs/${jobId}/cancel`, {
    method: 'POST',
  });
  if (!resp.ok) {
    throw new Error(`Gagal membatalkan job (HTTP ${resp.status})`);
  }
  return resp.json();
}

export async function downloadAndShareEpub(filename: string): Promise<void> {
  const base = await getServerUrl();
  const downloadUrl = `${base}/api/download/${encodeURIComponent(filename)}`;
  const destination = new File(Paths.document, filename);

  const downloaded = await File.downloadFileAsync(downloadUrl, destination, {
    idempotent: true,
  });

  // Open native sharing / e-reader app chooser
  const isAvailable = await Sharing.isAvailableAsync();
  if (isAvailable) {
    await Sharing.shareAsync(downloaded.uri, {
      mimeType: 'application/epub+zip',
      dialogTitle: `Buka ${filename}`,
      UTI: 'org.idpf.epub-container',
    });
  } else {
    alert(`File EPUB berhasil diunduh ke:\n${downloaded.uri}`);
  }
}
