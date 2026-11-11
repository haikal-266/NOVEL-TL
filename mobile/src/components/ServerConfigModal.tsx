import React, { useState, useEffect } from 'react';
import {
  Modal,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { Ionicons, Feather } from '@expo/vector-icons';
import { THEME } from '../theme';
import { getServerUrl, setServerUrl, testServerConnection, DEFAULT_SERVER_URL } from '../services/api';

interface ServerConfigModalProps {
  visible: boolean;
  onClose: () => void;
  onSaved: () => void;
}

export const ServerConfigModal: React.FC<ServerConfigModalProps> = ({
  visible,
  onClose,
  onSaved,
}) => {
  const [url, setUrl] = useState('');
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<boolean | null>(null);

  useEffect(() => {
    if (visible) {
      getServerUrl().then((current) => {
        setUrl(current);
        setTestResult(null);
      });
    }
  }, [visible]);

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    const ok = await testServerConnection(url);
    setTestResult(ok);
    setTesting(false);
  };

  const handleSave = async () => {
    if (url.trim()) {
      await setServerUrl(url);
      onSaved();
      onClose();
    }
  };

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.overlay}>
        <View style={styles.card}>
          {/* Header */}
          <View style={styles.headerRow}>
            <View style={styles.titleGroup}>
              <View style={styles.badgeLime}>
                <Ionicons name="server" size={14} color="#000" />
              </View>
              <Text style={styles.title}>Koneksi Backend AI</Text>
            </View>
            <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
              <Feather name="x" size={18} color="#000" />
            </TouchableOpacity>
          </View>

          <Text style={styles.desc}>
            Masukkan alamat IP laptop/PC kamu yang menjalankan FastAPI backend (port 8000) atau link Cloudflare Tunnel.
          </Text>

          {/* Input Box */}
          <View style={styles.inputBox}>
            <TextInput
              style={styles.input}
              value={url}
              onChangeText={(t) => {
                setUrl(t);
                setTestResult(null);
              }}
              placeholder="http://192.168.100.76:8000"
              autoCapitalize="none"
              autoCorrect={false}
            />
          </View>

          {/* Quick Preset Buttons */}
          <View style={styles.presetRow}>
            <TouchableOpacity
              style={styles.presetBtn}
              onPress={() => setUrl('http://192.168.100.76:8000')}
            >
              <Text style={styles.presetText}>IP PC Lokal</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.presetBtn}
              onPress={() => setUrl('http://10.0.2.2:8000')}
            >
              <Text style={styles.presetText}>Android Emu</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.presetBtn}
              onPress={() => setUrl('http://localhost:8000')}
            >
              <Text style={styles.presetText}>Localhost</Text>
            </TouchableOpacity>
          </View>

          {/* Test Status Banner */}
          {testing && (
            <View style={styles.testStatusRow}>
              <ActivityIndicator size="small" color="#000" />
              <Text style={styles.testStatusText}>Menghubungi server...</Text>
            </View>
          )}

          {testResult === true && (
            <View style={[styles.testStatusRow, { backgroundColor: '#D1FAE5' }]}>
              <Feather name="check-circle" size={16} color="#065F46" />
              <Text style={[styles.testStatusText, { color: '#065F46' }]}>
                Server Terhubung! (200 OK)
              </Text>
            </View>
          )}

          {testResult === false && (
            <View style={[styles.testStatusRow, { backgroundColor: THEME.colors.dangerLight }]}>
              <Feather name="alert-circle" size={16} color={THEME.colors.danger} />
              <Text style={[styles.testStatusText, { color: THEME.colors.danger }]}>
                Gagal terhubung. Pastikan PC & HP di Wi-Fi yang sama.
              </Text>
            </View>
          )}

          {/* Action Buttons */}
          <View style={styles.actionsRow}>
            <TouchableOpacity
              style={styles.btnSecondary}
              onPress={handleTest}
              disabled={testing}
            >
              <Feather name="activity" size={14} color="#000" />
              <Text style={styles.btnSecondaryText}>Tes Koneksi</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.btnPrimary} onPress={handleSave}>
              <Feather name="check" size={14} color="#000" />
              <Text style={styles.btnPrimaryText}>Simpan & Terapkan</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.65)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  card: {
    width: '100%',
    backgroundColor: THEME.colors.white,
    borderWidth: THEME.border.width,
    borderColor: THEME.border.color,
    borderRadius: THEME.border.radius,
    padding: 16,
    ...THEME.shadow,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  titleGroup: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  badgeLime: {
    backgroundColor: THEME.colors.lime,
    borderWidth: THEME.border.thin,
    borderColor: '#000',
    padding: 4,
    borderRadius: 6,
  },
  title: {
    fontSize: 14,
    fontWeight: '900',
    color: THEME.colors.black,
  },
  closeBtn: {
    padding: 4,
  },
  desc: {
    fontSize: 11,
    fontFamily: 'monospace',
    color: THEME.colors.grayText,
    marginBottom: 12,
    lineHeight: 16,
  },
  inputBox: {
    backgroundColor: THEME.colors.canvas,
    borderWidth: THEME.border.width,
    borderColor: THEME.border.color,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginBottom: 10,
  },
  input: {
    fontSize: 13,
    fontFamily: 'monospace',
    fontWeight: 'bold',
    color: THEME.colors.black,
  },
  presetRow: {
    flexDirection: 'row',
    gap: 6,
    marginBottom: 12,
  },
  presetBtn: {
    backgroundColor: THEME.colors.grayLight,
    borderWidth: THEME.border.thin,
    borderColor: '#000',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  presetText: {
    fontSize: 10,
    fontFamily: 'monospace',
    fontWeight: 'bold',
  },
  testStatusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    padding: 8,
    borderRadius: 8,
    borderWidth: THEME.border.thin,
    borderColor: '#000',
    marginBottom: 12,
  },
  testStatusText: {
    fontSize: 11,
    fontFamily: 'monospace',
    fontWeight: 'bold',
  },
  actionsRow: {
    flexDirection: 'row',
    gap: 8,
  },
  btnSecondary: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    backgroundColor: THEME.colors.white,
    borderWidth: THEME.border.thin,
    borderColor: '#000',
    paddingVertical: 10,
    borderRadius: 8,
  },
  btnSecondaryText: {
    fontSize: 12,
    fontWeight: '900',
    color: THEME.colors.black,
  },
  btnPrimary: {
    flex: 1.3,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    backgroundColor: THEME.colors.lime,
    borderWidth: THEME.border.thin,
    borderColor: '#000',
    paddingVertical: 10,
    borderRadius: 8,
  },
  btnPrimaryText: {
    fontSize: 12,
    fontWeight: '900',
    color: THEME.colors.black,
  },
});
