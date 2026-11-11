import React from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { Ionicons, Feather } from '@expo/vector-icons';
import { THEME } from '../theme';

interface NovelInputProps {
  url: string;
  onChangeUrl: (url: string) => void;
  onSubmit: () => void;
  isLoading: boolean;
}

const DEFAULT_EXAMPLE_URL =
  'https://kakuyomu.jp/works/2912051607243271731/episodes/2912051607330854893';

export const NovelInput: React.FC<NovelInputProps> = ({
  url,
  onChangeUrl,
  onSubmit,
  isLoading,
}) => {
  return (
    <View style={styles.card}>
      {/* Step Title Header */}
      <View style={styles.headerRow}>
        <View style={styles.badgeGroup}>
          <View style={styles.stepBadge}>
            <Ionicons name="flash" size={10} color="#121212" />
            <Text style={styles.stepBadgeText}>LANGKAH 1</Text>
          </View>
          <Text style={styles.titleText}>LINK NOVEL KAKUYOMU</Text>
        </View>

        {url.length > 0 && (
          <TouchableOpacity
            onPress={() => onChangeUrl('')}
            style={styles.clearBtn}
            hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
          >
            <Feather name="trash-2" size={12} color="#6B7280" />
            <Text style={styles.clearText}>Hapus</Text>
          </TouchableOpacity>
        )}
      </View>

      <Text style={styles.subtitle}>
        Tempel tautan halaman utama atau salah satu bab dari Kakuyomu.
      </Text>

      {/* Input Box */}
      <View style={styles.inputContainer}>
        <Feather name="link-2" size={16} color="#6B7280" style={styles.inputIcon} />
        <TextInput
          style={styles.input}
          value={url}
          onChangeText={onChangeUrl}
          placeholder="https://kakuyomu.jp/works/..."
          placeholderTextColor="#9CA3AF"
          autoCapitalize="none"
          autoCorrect={false}
          editable={!isLoading}
        />
      </View>

      {/* Example Button */}
      <TouchableOpacity
        style={styles.exampleBtn}
        onPress={() => onChangeUrl(DEFAULT_EXAMPLE_URL)}
        disabled={isLoading}
        activeOpacity={0.8}
      >
        <View style={styles.exampleLeft}>
          <Ionicons name="sparkles" size={12} color="#121212" />
          <Text style={styles.exampleText}>PAKAI CONTOH ROMCOM</Text>
        </View>
        <Text style={styles.exampleDomain}>kakuyomu.jp</Text>
      </TouchableOpacity>

      {/* Submit Button */}
      <TouchableOpacity
        style={[styles.submitBtn, isLoading && styles.submitBtnDisabled]}
        onPress={onSubmit}
        disabled={isLoading || !url.trim()}
        activeOpacity={0.8}
      >
        {isLoading ? (
          <View style={styles.loadingRow}>
            <ActivityIndicator size="small" color="#121212" />
            <Text style={styles.submitText}>MENGAMBIL DETAIL NOVEL...</Text>
          </View>
        ) : (
          <View style={styles.submitRow}>
            <Text style={styles.submitText}>AMBIL DETAIL NOVEL</Text>
            <Feather name="arrow-right" size={16} color="#121212" />
          </View>
        )}
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: THEME.colors.white,
    borderWidth: THEME.border.width,
    borderColor: THEME.border.color,
    borderRadius: THEME.border.radius,
    padding: 14,
    marginBottom: 14,
    ...THEME.shadowSm,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  badgeGroup: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  stepBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
    backgroundColor: THEME.colors.lime,
    borderWidth: 1.5,
    borderColor: '#121212',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
  },
  stepBadgeText: {
    fontSize: 9,
    fontFamily: 'monospace',
    fontWeight: '900',
    color: '#121212',
  },
  titleText: {
    fontSize: 12,
    fontWeight: '900',
    color: THEME.colors.black,
    letterSpacing: 0.3,
  },
  clearBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 4,
    paddingVertical: 2,
  },
  clearText: {
    fontSize: 10,
    fontFamily: 'monospace',
    fontWeight: 'bold',
    color: '#6B7280',
  },
  subtitle: {
    fontSize: 11,
    fontFamily: 'monospace',
    color: '#6B7280',
    marginBottom: 10,
    lineHeight: 15,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: THEME.colors.canvas,
    borderWidth: THEME.border.width,
    borderColor: THEME.border.color,
    borderRadius: 8,
    paddingHorizontal: 10,
    height: 44,
    marginBottom: 8,
  },
  inputIcon: {
    marginRight: 8,
  },
  input: {
    flex: 1,
    fontSize: 12,
    fontFamily: 'monospace',
    fontWeight: 'bold',
    color: THEME.colors.black,
    paddingVertical: 0,
  },
  exampleBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: THEME.colors.peach,
    borderWidth: THEME.border.thin,
    borderColor: '#121212',
    paddingHorizontal: 10,
    paddingVertical: 7,
    borderRadius: 8,
    marginBottom: 12,
  },
  exampleLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  exampleText: {
    fontSize: 9,
    fontFamily: 'monospace',
    fontWeight: '900',
    color: '#121212',
  },
  exampleDomain: {
    fontSize: 9,
    fontFamily: 'monospace',
    fontWeight: 'bold',
    color: '#6B7280',
  },
  submitBtn: {
    backgroundColor: THEME.colors.lime,
    borderWidth: THEME.border.width,
    borderColor: THEME.border.color,
    borderRadius: 10,
    height: 48,
    alignItems: 'center',
    justifyContent: 'center',
    ...THEME.shadowSm,
  },
  submitBtnDisabled: {
    opacity: 0.6,
  },
  submitRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  loadingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  submitText: {
    fontSize: 12,
    fontWeight: '900',
    color: '#121212',
    letterSpacing: 0.4,
  },
});
