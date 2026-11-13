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
  const [forceTranslate, setForceTranslate] = useState(false);

  const handleGenerate = () => {
    if (isGenerating) return;
    onStartGenerate({
      url: novel.url,
      rangeType,
      customRange: rangeType === 'range' ? customRange.trim() : undefined,
      mode,
      targetLang,
      forceTranslate,
    });
  };

  return (
    <View style={styles.card}>
      {/* Novel Header Info */}
      <View style={styles.novelHeader}>
        <View style={styles.metaRow}>
          <View style={styles.badgeLime}>
            <Text style={styles.badgeLimeText}>SELECTED NOVEL</Text>
          </View>
          <View style={[styles.badgeWhite, { backgroundColor: novel.source === 'syosetu' ? '#E78FB3' : '#FFC0AD' }]}>
            <Text style={[styles.totalEpisodesText, { color: '#121212', fontWeight: '900' }]}>
              {novel.source === 'syosetu' ? 'SYOSETU' : 'KAKUYOMU'}
            </Text>
          </View>
          <View style={styles.badgeWhite}>
            <Text style={styles.totalEpisodesText}>{novel.totalEpisodes} Chapters</Text>
          </View>
        </View>

        {/* Full Title */}
        <Text style={styles.novelTitle}>
          {(targetLang === 'id' && novel.titleId) ? novel.titleId : (novel.titleEn || novel.titleJa || 'Japanese Web Novel')}
        </Text>

        {/* Author & ID */}
        <Text style={styles.novelSub} numberOfLines={1}>
          {(targetLang === 'id' && novel.authorId) ? novel.authorId : (novel.authorEn || novel.authorJa)} • ID: {novel.workId}
        </Text>
      </View>

      {/* Chapter Selection */}
      <View style={styles.section}>
        <View style={styles.sectionHeaderRow}>
          <Text style={styles.sectionTitle}>SELECT CHAPTERS</Text>
          <Text style={styles.sectionSub}>1 EPUB file</Text>
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
              <Feather name="bookmark" size={15} color="#121212" />
              <View>
                <Text style={styles.optionTitle}>Current Chapter Only</Text>
                <Text style={styles.optionDesc}>
                  Chapter #{novel.currentEpisodeIndex} from URL
                </Text>
              </View>
            </View>
            <View style={styles.pillBlack}>
              <Text style={styles.pillBlackText}>CH #{novel.currentEpisodeIndex}</Text>
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
            <Feather name="sliders" size={15} color="#121212" />
            <View>
              <Text style={styles.optionTitle}>Custom Chapter Range</Text>
              <Text style={styles.optionDesc}>e.g. 1-5 or 1,2,3</Text>
            </View>
          </View>
          <View style={styles.pillBlack}>
            <Text style={styles.pillBlackText}>CUSTOM</Text>
          </View>
        </TouchableOpacity>

        {/* Custom Range Input Field */}
        {rangeType === 'range' && (
          <View style={styles.customInputBox}>
            <Text style={styles.customInputLabel}>Enter Chapter Range (e.g. 1-5 or 1,2,3):</Text>
            <TextInput
              style={styles.customInput}
              value={customRange}
              onChangeText={setCustomRange}
              placeholder="1-5"
              placeholderTextColor="#9CA3AF"
              keyboardType="numbers-and-punctuation"
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
            <Ionicons name="flame" size={16} color="#121212" />
            <View>
              <Text style={styles.optionTitle}>All Chapters (Complete)</Text>
              <Text style={styles.optionDesc}>Compile all {novel.totalEpisodes} chapters</Text>
            </View>
          </View>
          <View style={styles.allPillRow}>
            <View style={styles.pillPink}>
              <Text style={styles.pillPinkText}>ALL</Text>
            </View>
            <View style={styles.pillBlack}>
              <Text style={styles.pillBlackText}>1-{novel.totalEpisodes}</Text>
            </View>
          </View>
        </TouchableOpacity>
      </View>

      {/* Target Language Selection */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>TRANSLATION LANGUAGE (AI MODEL)</Text>
        <View style={styles.grid2}>
          {/* English Fast */}
          <TouchableOpacity
            style={[
              styles.gridCard,
              targetLang === 'en' && styles.gridCardActive,
            ]}
            onPress={() => setTargetLang('en')}
            activeOpacity={0.8}
          >
            <View style={styles.gridCardHeader}>
              <Text style={styles.gridCardTitle}>EN</Text>
              <View
                style={[
                  styles.radioDot,
                  targetLang === 'en' && styles.radioDotActive,
                ]}
              />
            </View>
            <Text style={styles.gridCardSub}>Sugoi V4</Text>
          </TouchableOpacity>

          {/* English Polished */}
          <TouchableOpacity
            style={[
              styles.gridCard,
              targetLang === 'en_polished' && styles.gridCardActive,
            ]}
            onPress={() => setTargetLang('en_polished')}
            activeOpacity={0.8}
          >
            <View style={styles.gridCardHeader}>
              <Text style={styles.gridCardTitle}>EN++</Text>
              <View
                style={[
                  styles.radioDot,
                  targetLang === 'en_polished' && styles.radioDotActive,
                ]}
              />
            </View>
            <Text style={styles.gridCardSub}>Sugoi + AI</Text>
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
              <Text style={styles.gridCardTitle}>ID</Text>
              <View
                style={[
                  styles.radioDot,
                  targetLang === 'id' && styles.radioDotActive,
                ]}
              />
            </View>
            <Text style={styles.gridCardSub}>SeaLLM 1.5B</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Layout Format Selection */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>EPUB TEXT FORMAT</Text>
        <View style={styles.grid2}>
          <TouchableOpacity
            style={[
              styles.gridCard,
              mode === 'translated' && styles.gridCardActive,
            ]}
            onPress={() => setMode('translated')}
            activeOpacity={0.8}
          >
            <Text style={styles.gridCardTitle}>100% Clean</Text>
            <Text style={styles.gridCardSub}>No Japanese Text</Text>
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
            <Text style={styles.gridCardSub}>JP + Translation</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Force Re-translate Checkbox */}
      <TouchableOpacity
        style={styles.checkboxRow}
        onPress={() => setForceTranslate(!forceTranslate)}
        activeOpacity={0.8}
      >
        <View style={[styles.checkboxBox, forceTranslate && styles.checkboxBoxActive]}>
          {forceTranslate && <Feather name="check" size={13} color="#121212" />}
        </View>
        <View style={styles.checkboxTextCol}>
          <Text style={styles.checkboxTitle}>Force Re-translate (Bypass Cache)</Text>
          <Text style={styles.checkboxSubtitle}>
            Re-processes chapters from scratch even if already cached
          </Text>
        </View>
      </TouchableOpacity>

      {/* Generate CTA Button */}
      <TouchableOpacity
        style={[styles.generateBtn, isGenerating && styles.generateBtnDisabled]}
        onPress={handleGenerate}
        disabled={isGenerating}
        activeOpacity={0.8}
      >
        <Feather name="download" size={18} color="#121212" />
        <Text style={styles.generateBtnText}>GENERATE EPUB NOW</Text>
        <Feather name="arrow-right" size={16} color="#121212" />
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
  novelHeader: {
    paddingBottom: 10,
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
    borderColor: '#121212',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
  },
  badgeLimeText: {
    fontSize: 9,
    fontFamily: 'monospace',
    fontWeight: '900',
    color: '#121212',
  },
  badgeWhite: {
    backgroundColor: THEME.colors.canvas,
    borderWidth: 1,
    borderColor: '#121212',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
  },
  totalEpisodesText: {
    fontSize: 10,
    fontFamily: 'monospace',
    fontWeight: 'bold',
    color: '#121212',
  },
  novelTitle: {
    fontSize: 13,
    fontWeight: '900',
    color: THEME.colors.black,
    lineHeight: 18,
    marginBottom: 4,
  },
  novelSub: {
    fontSize: 10,
    fontFamily: 'monospace',
    fontWeight: 'bold',
    color: '#4B5563',
  },
  section: {
    marginBottom: 16,
  },
  sectionHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  sectionTitle: {
    fontSize: 10,
    fontWeight: '900',
    color: THEME.colors.espresso,
    letterSpacing: 0.4,
    marginBottom: 8,
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
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginBottom: 8,
  },
  optionCardActive: {
    backgroundColor: THEME.colors.lime,
    borderWidth: THEME.border.width,
    borderColor: '#121212',
    ...THEME.shadowSm,
  },
  optionLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flex: 1,
  },
  optionTitle: {
    fontSize: 11,
    fontWeight: '900',
    color: THEME.colors.black,
  },
  optionDesc: {
    fontSize: 9,
    fontFamily: 'monospace',
    color: '#4B5563',
  },
  pillBlack: {
    backgroundColor: '#121212',
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
    borderColor: '#121212',
  },
  pillPinkText: {
    fontSize: 9,
    fontFamily: 'monospace',
    fontWeight: '900',
    color: '#121212',
  },
  allPillRow: {
    flexDirection: 'row',
    gap: 4,
  },
  customInputBox: {
    backgroundColor: THEME.colors.canvas,
    borderWidth: 1.5,
    borderColor: '#121212',
    borderRadius: 8,
    padding: 8,
    marginBottom: 6,
  },
  customInputLabel: {
    fontSize: 9,
    fontFamily: 'monospace',
    fontWeight: 'bold',
    color: '#4B5563',
    marginBottom: 4,
  },
  customInput: {
    fontSize: 12,
    fontFamily: 'monospace',
    fontWeight: 'bold',
    color: '#121212',
    backgroundColor: '#FFF',
    borderWidth: 1,
    borderColor: '#121212',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 5,
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
    padding: 12,
  },
  gridCardActive: {
    backgroundColor: THEME.colors.lime,
    borderWidth: THEME.border.width,
    borderColor: '#121212',
    ...THEME.shadowSm,
  },
  gridCardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 2,
  },
  gridCardTitle: {
    fontSize: 11,
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
    borderColor: '#121212',
    backgroundColor: '#FFF',
  },
  radioDotActive: {
    backgroundColor: '#121212',
  },
  checkboxRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
    gap: 12,
  },
  checkboxBox: {
    width: 20,
    height: 20,
    borderWidth: 2,
    borderColor: '#121212',
    backgroundColor: '#FFFFFF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkboxBoxActive: {
    backgroundColor: THEME.colors.lime,
  },
  checkboxTextCol: {
    flex: 1,
  },
  checkboxTitle: {
    fontSize: 11,
    fontWeight: '900',
    color: '#121212',
  },
  checkboxSubtitle: {
    fontFamily: 'monospace',
    fontSize: 9,
    fontWeight: 'bold',
    color: '#6B7280',
    marginTop: 1,
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
    height: 48,
    marginTop: 2,
    ...THEME.shadowSm,
  },
  generateBtnDisabled: {
    opacity: 0.6,
  },
  generateBtnText: {
    fontSize: 12,
    fontWeight: '900',
    color: '#121212',
    letterSpacing: 0.4,
  },
});
