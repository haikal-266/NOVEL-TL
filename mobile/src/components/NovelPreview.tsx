import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { Feather, Ionicons } from '@expo/vector-icons';
import { THEME } from '../theme';
import {
  NovelInspectResponse,
  RangeType,
  TranslationMode,
  TargetLanguage,
  GenerateRequest,
} from '../types';

interface NovelPreviewProps {
  novel: NovelInspectResponse;
  isGenerating: boolean;
  onStartGenerate: (req: GenerateRequest) => void;
}

export const NovelPreview: React.FC<NovelPreviewProps> = ({
  novel,
  isGenerating,
  onStartGenerate,
}) => {
  const [rangeType, setRangeType] = useState<RangeType>(
    novel.currentEpisodeId ? 'current' : 'range'
  );
  const [customRange, setCustomRange] = useState('1-5');
  const [mode, setMode] = useState<TranslationMode>('translated');
  const [targetLang, setTargetLang] = useState<TargetLanguage>('en');

  const handleGenerate = () => {
    if (isGenerating) return;
    onStartGenerate({
      url: novel.url,
      rangeType,
      customRange: rangeType === 'range' ? customRange.trim() : undefined,
      mode,
      targetLang,
    });
  };

  return (
    <View style={styles.card}>
      {/* Novel Header Info */}
      <View style={styles.novelHeader}>
        <View style={styles.metaRow}>
          <View style={styles.badgeLime}>
            <Text style={styles.badgeLimeText}>NOVEL TERPILIH</Text>
          </View>
          <Text style={styles.totalEpisodesText}>{novel.totalEpisodes} Bab</Text>
        </View>

        {/* Full Title */}
        <Text style={styles.novelTitle}>
          {novel.titleEn || novel.titleJa || 'Japanese Web Novel'}
        </Text>

        {/* Author & ID */}
        <Text style={styles.novelSub}>
          {novel.authorEn || novel.authorJa} • ID: {novel.workId}
        </Text>
      </View>

      {/* Chapter Selection */}
      <View style={styles.section}>
        <View style={styles.sectionHeaderRow}>
          <Text style={styles.sectionTitle}>PILIH BAB</Text>
          <Text style={styles.sectionSub}>1 file EPUB</Text>
        </View>

        {/* Option 1: Current Episode */}
        {novel.currentEpisodeIndex && (
          <TouchableOpacity
            style={[
              styles.optionCard,
              rangeType === 'current' && styles.optionCardActive,
            ]}
            onPress={() => setRangeType('current')}
            activeOpacity={0.8}
          >
            <View style={styles.optionLeft}>
              <Feather name="bookmark" size={15} color="#000" />
              <View>
                <Text style={styles.optionTitle}>Hanya Bab Saat Ini</Text>
                <Text style={styles.optionDesc}>
                  Bab #{novel.currentEpisodeIndex} sesuai URL
                </Text>
              </View>
            </View>
            <View style={styles.pillBlack}>
              <Text style={styles.pillBlackText}>BAB #{novel.currentEpisodeIndex}</Text>
            </View>
          </TouchableOpacity>
        )}

        {/* Option 2: Custom Range */}
        <TouchableOpacity
          style={[
            styles.optionCard,
            rangeType === 'range' && styles.optionCardActive,
          ]}
          onPress={() => setRangeType('range')}
          activeOpacity={0.8}
        >
          <View style={styles.optionLeft}>
            <Feather name="sliders" size={15} color="#000" />
            <View>
              <Text style={styles.optionTitle}>Rentang Bab (Custom)</Text>
              <Text style={styles.optionDesc}>Misal: 1-5 atau 1,2,3</Text>
            </View>
          </View>
          <View style={styles.pillBlack}>
            <Text style={styles.pillBlackText}>CUSTOM</Text>
          </View>
        </TouchableOpacity>

        {/* Custom Range Input Field */}
        {rangeType === 'range' && (
          <View style={styles.customInputBox}>
            <Text style={styles.customInputLabel}>Masukkan Nomor Bab:</Text>
            <TextInput
              style={styles.customInput}
              value={customRange}
              onChangeText={setCustomRange}
              placeholder="1-5 atau 1,2,3"
              placeholderTextColor="#9CA3AF"
            />
          </View>
        )}

        {/* Option 3: All Episodes */}
        <TouchableOpacity
          style={[
            styles.optionCard,
            rangeType === 'all' && styles.optionCardActive,
          ]}
          onPress={() => setRangeType('all')}
          activeOpacity={0.8}
        >
          <View style={styles.optionLeft}>
            <Ionicons name="flame" size={16} color="#000" />
            <View>
              <Text style={styles.optionTitle}>Mode Sampe Tamat</Text>
              <Text style={styles.optionDesc}>Kompilasi semua {novel.totalEpisodes} bab</Text>
            </View>
          </View>
          <View style={styles.allPillRow}>
            <View style={styles.pillPink}>
              <Text style={styles.pillPinkText}>SEMUA</Text>
            </View>
            <View style={styles.pillBlack}>
              <Text style={styles.pillBlackText}>1-{novel.totalEpisodes}</Text>
            </View>
          </View>
        </TouchableOpacity>
      </View>

      {/* Target Language Selection */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>BAHASA TERJEMAHAN (MODEL AI)</Text>
        <View style={styles.grid2}>
          {/* English Option */}
          <TouchableOpacity
            style={[
              styles.gridCard,
              targetLang === 'en' && styles.gridCardActive,
            ]}
            onPress={() => setTargetLang('en')}
            activeOpacity={0.8}
          >
            <View style={styles.gridCardHeader}>
              <Text style={styles.gridCardTitle}>ENGLISH</Text>
              <View
                style={[
                  styles.radioDot,
                  targetLang === 'en' && styles.radioDotActive,
                ]}
              />
            </View>
            <Text style={styles.gridCardSub}>Sugoi V4 (Ultra Cepat)</Text>
          </TouchableOpacity>

          {/* Indonesian Option */}
          <TouchableOpacity
            style={[
              styles.gridCard,
              targetLang === 'id' && styles.gridCardActive,
            ]}
            onPress={() => setTargetLang('id')}
            activeOpacity={0.8}
          >
            <View style={styles.gridCardHeader}>
              <Text style={styles.gridCardTitle}>INDONESIA</Text>
              <View
                style={[
                  styles.radioDot,
                  targetLang === 'id' && styles.radioDotActive,
                ]}
              />
            </View>
            <Text style={styles.gridCardSub}>Bridge Sugoi + Qwen</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Layout Format Selection */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>TAMPILAN TEKS EPUB</Text>
        <View style={styles.grid2}>
          <TouchableOpacity
            style={[
              styles.gridCard,
              mode === 'translated' && styles.gridCardActive,
            ]}
            onPress={() => setMode('translated')}
            activeOpacity={0.8}
          >
            <Text style={styles.gridCardTitle}>100% Bersih</Text>
            <Text style={styles.gridCardSub}>Tanpa Teks Jepang</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              styles.gridCard,
              mode === 'bilingual' && styles.gridCardActive,
            ]}
            onPress={() => setMode('bilingual')}
            activeOpacity={0.8}
          >
            <Text style={styles.gridCardTitle}>Bilingual</Text>
            <Text style={styles.gridCardSub}>Paragraf JP + TL</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Generate CTA Button */}
      <TouchableOpacity
        style={[styles.generateBtn, isGenerating && styles.generateBtnDisabled]}
        onPress={handleGenerate}
        disabled={isGenerating}
        activeOpacity={0.85}
      >
        <Feather name="download" size={18} color="#000" />
        <Text style={styles.generateBtnText}>GENERATE EPUB SEKARANG</Text>
        <Feather name="arrow-right" size={16} color="#000" />
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
    marginBottom: 16,
    ...THEME.shadow,
  },
  novelHeader: {
    paddingBottom: 12,
    borderBottomWidth: 1.5,
    borderBottomColor: '#E5E7EB',
    marginBottom: 12,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  badgeLime: {
    backgroundColor: THEME.colors.lime,
    borderWidth: 1,
    borderColor: '#000',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
  },
  badgeLimeText: {
    fontSize: 9,
    fontFamily: 'monospace',
    fontWeight: '900',
    color: '#000',
  },
  totalEpisodesText: {
    fontSize: 10,
    fontFamily: 'monospace',
    fontWeight: 'bold',
    color: '#6B7280',
  },
  novelTitle: {
    fontSize: 14,
    fontWeight: '900',
    color: THEME.colors.black,
    lineHeight: 19,
    marginBottom: 4,
  },
  novelSub: {
    fontSize: 11,
    fontFamily: 'monospace',
    fontWeight: 'bold',
    color: '#4B5563',
  },
  section: {
    marginBottom: 12,
  },
  sectionHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  sectionTitle: {
    fontSize: 11,
    fontWeight: '900',
    color: THEME.colors.espresso,
    letterSpacing: 0.4,
    marginBottom: 6,
  },
  sectionSub: {
    fontSize: 10,
    fontFamily: 'monospace',
    fontWeight: 'bold',
    color: '#9CA3AF',
  },
  optionCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: THEME.colors.white,
    borderWidth: THEME.border.thin,
    borderColor: THEME.border.color,
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 8,
    marginBottom: 6,
  },
  optionCardActive: {
    backgroundColor: THEME.colors.lime,
    borderWidth: THEME.border.width,
    ...THEME.shadowSm,
  },
  optionLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flex: 1,
  },
  optionTitle: {
    fontSize: 12,
    fontWeight: '900',
    color: THEME.colors.black,
  },
  optionDesc: {
    fontSize: 9,
    fontFamily: 'monospace',
    color: '#4B5563',
  },
  pillBlack: {
    backgroundColor: '#000',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
  },
  pillBlackText: {
    fontSize: 9,
    fontFamily: 'monospace',
    fontWeight: 'bold',
    color: '#FFF',
  },
  pillPink: {
    backgroundColor: THEME.colors.pink,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#000',
  },
  pillPinkText: {
    fontSize: 9,
    fontFamily: 'monospace',
    fontWeight: '900',
    color: '#000',
  },
  allPillRow: {
    flexDirection: 'row',
    gap: 4,
  },
  customInputBox: {
    backgroundColor: THEME.colors.canvas,
    borderWidth: 1.5,
    borderColor: '#000',
    borderRadius: 8,
    padding: 8,
    marginBottom: 6,
  },
  customInputLabel: {
    fontSize: 9,
    fontFamily: 'monospace',
    fontWeight: 'bold',
    color: '#6B7280',
    marginBottom: 4,
  },
  customInput: {
    fontSize: 12,
    fontFamily: 'monospace',
    fontWeight: 'bold',
    color: '#000',
    backgroundColor: '#FFF',
    borderWidth: 1,
    borderColor: '#000',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  grid2: {
    flexDirection: 'row',
    gap: 8,
  },
  gridCard: {
    flex: 1,
    backgroundColor: THEME.colors.white,
    borderWidth: THEME.border.thin,
    borderColor: THEME.border.color,
    borderRadius: 8,
    padding: 10,
  },
  gridCardActive: {
    backgroundColor: THEME.colors.lime,
    borderWidth: THEME.border.width,
    ...THEME.shadowSm,
  },
  gridCardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 2,
  },
  gridCardTitle: {
    fontSize: 12,
    fontWeight: '900',
    color: THEME.colors.black,
  },
  gridCardSub: {
    fontSize: 9,
    fontFamily: 'monospace',
    fontWeight: 'bold',
    color: '#4B5563',
  },
  radioDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    borderWidth: 1.5,
    borderColor: '#000',
    backgroundColor: '#FFF',
  },
  radioDotActive: {
    backgroundColor: '#000',
  },
  generateBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: THEME.colors.lime,
    borderWidth: THEME.border.width,
    borderColor: THEME.border.color,
    borderRadius: 10,
    paddingVertical: 13,
    marginTop: 4,
    ...THEME.shadowSm,
  },
  generateBtnDisabled: {
    opacity: 0.6,
  },
  generateBtnText: {
    fontSize: 13,
    fontWeight: '900',
    color: '#000',
    letterSpacing: 0.5,
  },
});
