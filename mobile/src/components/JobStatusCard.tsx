import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { Feather, Ionicons } from '@expo/vector-icons';
import { THEME } from '../theme';
import { JobState } from '../types';
import { downloadAndShareEpub } from '../services/api';

interface JobStatusCardProps {
  job: JobState;
  onCancel: () => void;
  onReset: () => void;
}

export const JobStatusCard: React.FC<JobStatusCardProps> = ({
  job,
  onCancel,
  onReset,
}) => {
  const [downloading, setDownloading] = useState(false);
  const [downloadPercent, setDownloadPercent] = useState(0);

  const isRunning = job.status === 'running' || job.status === 'pending';
  const isCompleted = job.status === 'completed';
  const isError = job.status === 'error';

  const handleDownloadAndOpen = async () => {
    if (!job.filename) return;
    try {
      setDownloading(true);
      await downloadAndShareEpub(job.filename);
    } catch (err: any) {
      Alert.alert('Gagal Membuka File', err.message || 'Terjadi kesalahan saat mengunduh file.');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <View style={styles.card}>
      {/* Top Status Indicator */}
      <View style={styles.headerRow}>
        <View style={styles.statusLeft}>
          {isRunning && (
            <>
              <View style={styles.pulsingDot} />
              <Text style={styles.statusText}>MEMPROSES AI TRANSLASI...</Text>
            </>
          )}
          {isCompleted && (
            <>
              <View style={styles.iconCircleGreen}>
                <Feather name="check" size={12} color="#000" />
              </View>
              <Text style={styles.statusText}>EPUB BERHASIL DIBUAT!</Text>
            </>
          )}
          {isError && (
            <>
              <View style={styles.iconCircleRed}>
                <Feather name="alert-triangle" size={12} color="#FFF" />
              </View>
              <Text style={[styles.statusText, { color: '#991B1B' }]}>
                TERJADI KESALAHAN
              </Text>
            </>
          )}
        </View>

        <View style={styles.badgeWhite}>
          <Text style={styles.badgeWhiteText}>{job.progressPercent}%</Text>
        </View>
      </View>

      {/* Progress Bar Container */}
      <View style={styles.progressTrack}>
        <View
          style={[styles.progressBar, { width: `${Math.min(100, Math.max(0, job.progressPercent))}%` }]}
        />
      </View>

      {/* Status Info Box */}
      <View style={styles.infoBox}>
        <Text style={styles.messageText}>{job.message}</Text>

        {job.chapterTitle ? (
          <View style={styles.chapterInfoRow}>
            <Text style={styles.chapterTitleText} numberOfLines={1}>
              Bab {job.currentChapter}/{job.totalChapters}: {job.chapterTitle}
            </Text>
            {job.paragraphsTotal > 0 && (
              <View style={styles.parasBadge}>
                <Text style={styles.parasBadgeText}>
                  {job.paragraphsDone}/{job.paragraphsTotal} par.
                </Text>
              </View>
            )}
          </View>
        ) : null}
      </View>

      {/* Running State: Cancel Button */}
      {isRunning && (
        <View style={styles.cancelBox}>
          <TouchableOpacity
            style={[styles.cancelBtn, job.cancelled && styles.cancelBtnDisabled]}
            onPress={onCancel}
            disabled={job.cancelled}
            activeOpacity={0.8}
          >
            <Feather name="x-circle" size={14} color="#000" />
            <Text style={styles.cancelBtnText}>
              {job.cancelled
                ? 'Membatalkan... Merakit Bab Selesai'
                : 'Batalkan & Ambil Bab Selesai'}
            </Text>
          </TouchableOpacity>
          <Text style={styles.cancelNotice}>
            Jika dibatalkan, bab yang telah selesai akan otomatis dirakit menjadi EPUB.
          </Text>
        </View>
      )}

      {/* Completed State: Download & Open CTA */}
      {isCompleted && (
        <View style={styles.completedBox}>
          <TouchableOpacity
            style={styles.downloadBtn}
            onPress={handleDownloadAndOpen}
            disabled={downloading}
            activeOpacity={0.85}
          >
            {downloading ? (
              <View style={styles.btnRow}>
                <ActivityIndicator size="small" color="#000" />
                <Text style={styles.downloadBtnText}>
                  Mengunduh ({downloadPercent}%)...
                </Text>
              </View>
            ) : (
              <View style={styles.btnRow}>
                <Feather name="book-open" size={18} color="#000" />
                <Text style={styles.downloadBtnText}>BUKA / SIMPAN EPUB</Text>
                <Feather name="share" size={16} color="#000" />
              </View>
            )}
          </TouchableOpacity>

          {job.filename ? (
            <View style={styles.filenameRow}>
              <Feather name="file-text" size={12} color="#6B7280" />
              <Text style={styles.filenameText} numberOfLines={1}>
                {job.filename}
              </Text>
            </View>
          ) : null}

          <TouchableOpacity style={styles.resetBtn} onPress={onReset}>
            <Feather name="refresh-cw" size={14} color={THEME.colors.espresso} />
            <Text style={styles.resetBtnText}>Buat EPUB untuk Novel Lainnya</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Error State */}
      {isError && (
        <View style={styles.errorBox}>
          <View style={styles.errorBanner}>
            <Feather name="alert-circle" size={14} color="#B91C1C" />
            <Text style={styles.errorText}>
              {job.error || 'Gagal memproses translasi novel.'}
            </Text>
          </View>

          <TouchableOpacity style={styles.resetBtn} onPress={onReset}>
            <Feather name="refresh-cw" size={14} color="#000" />
            <Text style={styles.resetBtnText}>Coba Lagi</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: THEME.colors.pink,
    borderWidth: THEME.border.width,
    borderColor: THEME.border.color,
    borderRadius: THEME.border.radius,
    padding: 14,
    marginBottom: 16,
    ...THEME.shadow,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  statusLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flex: 1,
  },
  pulsingDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: THEME.colors.lime,
    borderWidth: 1.5,
    borderColor: '#000',
  },
  iconCircleGreen: {
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: THEME.colors.lime,
    borderWidth: 1.5,
    borderColor: '#000',
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconCircleRed: {
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: THEME.colors.danger,
    borderWidth: 1.5,
    borderColor: '#000',
    alignItems: 'center',
    justifyContent: 'center',
  },
  statusText: {
    fontSize: 11,
    fontWeight: '900',
    color: THEME.colors.espresso,
    letterSpacing: 0.3,
  },
  badgeWhite: {
    backgroundColor: THEME.colors.white,
    borderWidth: 1.5,
    borderColor: '#000',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
  },
  badgeWhiteText: {
    fontSize: 11,
    fontFamily: 'monospace',
    fontWeight: '900',
    color: '#000',
  },
  progressTrack: {
    width: '100%',
    height: 22,
    backgroundColor: THEME.colors.espresso,
    borderWidth: 2,
    borderColor: '#000',
    borderRadius: 11,
    padding: 2,
    marginBottom: 10,
    overflow: 'hidden',
  },
  progressBar: {
    height: '100%',
    backgroundColor: THEME.colors.lime,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#000',
  },
  infoBox: {
    backgroundColor: THEME.colors.white,
    borderWidth: 1.5,
    borderColor: '#000',
    borderRadius: 8,
    padding: 10,
    marginBottom: 10,
  },
  messageText: {
    fontSize: 11,
    fontFamily: 'monospace',
    fontWeight: 'bold',
    color: '#1A1A1A',
    marginBottom: 6,
  },
  chapterInfoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 6,
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
    gap: 8,
  },
  chapterTitleText: {
    flex: 1,
    fontSize: 10,
    fontWeight: 'bold',
    color: '#1F2937',
  },
  parasBadge: {
    backgroundColor: THEME.colors.canvas,
    borderWidth: 1,
    borderColor: '#000',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
  },
  parasBadgeText: {
    fontSize: 9,
    fontFamily: 'monospace',
    fontWeight: 'bold',
    color: '#000',
  },
  cancelBox: {
    marginTop: 2,
  },
  cancelBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    backgroundColor: THEME.colors.peach,
    borderWidth: 2,
    borderColor: '#000',
    borderRadius: 8,
    paddingVertical: 9,
    ...THEME.shadowSm,
  },
  cancelBtnDisabled: {
    opacity: 0.6,
  },
  cancelBtnText: {
    fontSize: 11,
    fontWeight: '900',
    color: '#000',
    letterSpacing: 0.3,
  },
  cancelNotice: {
    fontSize: 9,
    fontFamily: 'monospace',
    fontWeight: 'bold',
    color: '#4B5563',
    textAlign: 'center',
    marginTop: 6,
  },
  completedBox: {
    gap: 8,
    marginTop: 2,
  },
  downloadBtn: {
    backgroundColor: THEME.colors.lime,
    borderWidth: 2,
    borderColor: '#000',
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: 'center',
    justifyContent: 'center',
    ...THEME.shadowSm,
  },
  btnRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  downloadBtnText: {
    fontSize: 13,
    fontWeight: '900',
    color: '#000',
    letterSpacing: 0.5,
  },
  filenameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    backgroundColor: '#FFF',
    borderWidth: 1,
    borderColor: '#000',
    borderRadius: 6,
    padding: 6,
  },
  filenameText: {
    fontSize: 10,
    fontFamily: 'monospace',
    fontWeight: 'bold',
    color: '#374151',
  },
  resetBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    backgroundColor: '#FFF',
    borderWidth: 1.5,
    borderColor: '#000',
    borderRadius: 8,
    paddingVertical: 8,
  },
  resetBtnText: {
    fontSize: 11,
    fontWeight: 'bold',
    color: THEME.colors.espresso,
  },
  errorBox: {
    gap: 8,
    marginTop: 2,
  },
  errorBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#FEE2E2',
    borderWidth: 1.5,
    borderColor: '#B91C1C',
    borderRadius: 8,
    padding: 8,
  },
  errorText: {
    flex: 1,
    fontSize: 11,
    fontWeight: 'bold',
    color: '#991B1B',
  },
});
