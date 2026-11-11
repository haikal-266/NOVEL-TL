import React, { useState, useEffect, useRef } from 'react';
import {
  SafeAreaView,
  ScrollView,
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Feather } from '@expo/vector-icons';
import { THEME } from './src/theme';
import {
  NovelInspectResponse,
  GenerateRequest,
  JobState,
} from './src/types';
import {
  getServerUrl,
  testServerConnection,
  inspectNovel,
  generateNovel,
  getJobStatus,
  cancelJob,
} from './src/services/api';
import { Header } from './src/components/Header';
import { ServerConfigModal } from './src/components/ServerConfigModal';
import { NovelInput } from './src/components/NovelInput';
import { NovelPreview } from './src/components/NovelPreview';
import { JobStatusCard } from './src/components/JobStatusCard';

export default function App() {
  const [url, setUrl] = useState('');
  const [novel, setNovel] = useState<NovelInspectResponse | null>(null);
  const [job, setJob] = useState<JobState | null>(null);

  const [isInspecting, setIsInspecting] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [serverConnected, setServerConnected] = useState(false);
  const [settingsModalVisible, setSettingsModalVisible] = useState(false);

  const pollIntervalRef = useRef<any>(null);

  // Check server connectivity on startup
  const checkConnection = async () => {
    const currentUrl = await getServerUrl();
    const ok = await testServerConnection(currentUrl);
    setServerConnected(ok);
  };

  useEffect(() => {
    checkConnection();
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  // Poll active translation job
  const startPolling = (jobId: string) => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);

    pollIntervalRef.current = setInterval(async () => {
      try {
        const updated = await getJobStatus(jobId);
        setJob(updated);

        if (updated.status === 'completed' || updated.status === 'error') {
          setIsGenerating(false);
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
          }
        }
      } catch (err: any) {
        console.warn('Poll error:', err);
      }
    }, 1500);
  };

  const handleInspect = async () => {
    if (!url.trim() || isInspecting) return;
    setErrorMessage(null);
    setIsInspecting(true);

    try {
      const data = await inspectNovel(url.trim());
      setNovel(data);
      setServerConnected(true);
    } catch (err: any) {
      setErrorMessage(err.message || 'Gagal mengambil detail novel.');
      setServerConnected(false);
    } finally {
      setIsInspecting(false);
    }
  };

  const handleStartGenerate = async (req: GenerateRequest) => {
    if (isGenerating) return;
    setErrorMessage(null);
    setIsGenerating(true);

    try {
      const initialJob = await generateNovel(req);
      setJob(initialJob);
      startPolling(initialJob.jobId);
    } catch (err: any) {
      setErrorMessage(err.message || 'Gagal memulai translasi.');
      setIsGenerating(false);
    }
  };

  const handleCancelJob = async () => {
    if (!job || (job.status !== 'running' && job.status !== 'pending')) return;
    try {
      const updated = await cancelJob(job.jobId);
      setJob(updated);
    } catch (err: any) {
      Alert.alert('Gagal Membatalkan', err.message || 'Terjadi kesalahan.');
    }
  };

  const handleReset = () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    setJob(null);
    setNovel(null);
    setIsGenerating(false);
    setErrorMessage(null);
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar style="dark" />

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.container}>
          {/* Header */}
          <Header
            serverConnected={serverConnected}
            onOpenSettings={() => setSettingsModalVisible(true)}
          />

          {/* Error Banner */}
          {errorMessage ? (
            <View style={styles.errorCard}>
              <View style={styles.errorLeft}>
                <Feather name="alert-triangle" size={14} color="#000" />
                <Text style={styles.errorCardText}>{errorMessage}</Text>
              </View>
              <TouchableOpacity onPress={() => setErrorMessage(null)} style={styles.errorDismiss}>
                <Feather name="x" size={14} color="#000" />
              </TouchableOpacity>
            </View>
          ) : null}

          {/* Step 1: Novel URL Input */}
          <NovelInput
            url={url}
            onChangeUrl={setUrl}
            onSubmit={handleInspect}
            isLoading={isInspecting}
          />

          {/* Active Job Progress */}
          {job ? (
            <JobStatusCard
              job={job}
              onCancel={handleCancelJob}
              onReset={handleReset}
            />
          ) : null}

          {/* Step 2: Novel Preview & Chapter Selection */}
          {novel && (!job || job.status === 'completed') ? (
            <NovelPreview
              novel={novel}
              isGenerating={isGenerating}
              onStartGenerate={handleStartGenerate}
            />
          ) : null}

          {/* Footer Branding */}
          <View style={styles.footer}>
            <View style={styles.colorPill}>
              <View style={[styles.colorSlice, { backgroundColor: THEME.colors.espresso }]} />
              <View style={[styles.colorSlice, { backgroundColor: THEME.colors.peach }]} />
              <View style={[styles.colorSlice, { backgroundColor: THEME.colors.pink }]} />
              <View style={[styles.colorSlice, { backgroundColor: THEME.colors.lime }]} />
            </View>
            <Text style={styles.footerText}>Everyone Should Start Reading</Text>
          </View>
        </View>
      </ScrollView>

      {/* Settings Modal */}
      <ServerConfigModal
        visible={settingsModalVisible}
        onClose={() => setSettingsModalVisible(false)}
        onSaved={checkConnection}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: THEME.colors.canvas,
  },
  scrollContent: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    alignItems: 'center',
  },
  container: {
    width: '100%',
    maxWidth: 420,
  },
  errorCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: THEME.colors.pink,
    borderWidth: THEME.border.width,
    borderColor: '#000',
    borderRadius: THEME.border.radiusSm,
    padding: 10,
    marginBottom: 12,
    ...THEME.shadowSm,
  },
  errorLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flex: 1,
  },
  errorCardText: {
    fontSize: 11,
    fontFamily: 'monospace',
    fontWeight: 'bold',
    color: '#000',
    flex: 1,
  },
  errorDismiss: {
    padding: 4,
  },
  footer: {
    alignItems: 'center',
    paddingVertical: 18,
  },
  colorPill: {
    flexDirection: 'row',
    width: 90,
    height: 18,
    borderWidth: 2,
    borderColor: '#000',
    borderRadius: 9,
    overflow: 'hidden',
    marginBottom: 8,
    ...THEME.shadowSm,
  },
  colorSlice: {
    flex: 1,
  },
  footerText: {
    fontSize: 11,
    fontFamily: 'monospace',
    fontWeight: 'bold',
    color: THEME.colors.espresso,
  },
});
