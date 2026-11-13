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
            <Text style={styles.stepBadgeText}>STEP 1</Text>
          </View>
          <Text style={styles.titleText}>NOVEL URL</Text>
        </View>

        {url.length > 0 && (
          <TouchableOpacity
            onPress={() => onChangeUrl('')}
            style={styles.clearBtn}
            hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
          >
            <Feather name="trash-2" size={12} color="#6B7280" />
            <Text style={styles.clearText}>Clear</Text>
          </TouchableOpacity>
        )}
      </View>

      <Text style={styles.subtitle}>
        Kakuyomu (kakuyomu.jp) or Syosetu (ncode.syosetu.com) link.
      </Text>

      {/* Input Box */}
      <View style={styles.inputContainer}>
        <Feather name="link-2" size={16} color="#6B7280" style={styles.inputIcon} />
        <TextInput
          style={styles.input}
          value={url}
          onChangeText={onChangeUrl}
          placeholder="https://kakuyomu.jp/... or syosetu.com/..."
          placeholderTextColor="#9CA3AF"
          autoCapitalize="none"
          autoCorrect={false}
          editable={!isLoading}
        />
      </View>

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
            <Text style={styles.submitText}>FETCHING NOVEL DETAILS...</Text>
          </View>
        ) : (
          <View style={styles.submitRow}>
            <Text style={styles.submitText}>FETCH NOVEL DETAILS</Text>
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
  examplesRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 12,
  },
  exampleBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 5,
    backgroundColor: THEME.colors.peach,
    borderWidth: THEME.border.thin,
    borderColor: '#121212',
    paddingHorizontal: 8,
    paddingVertical: 7,
    borderRadius: 8,
  },
  exampleBtnLime: {
    backgroundColor: THEME.colors.lime,
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
