import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Feather, Ionicons } from '@expo/vector-icons';
import { THEME } from '../theme';

interface HeaderProps {
  serverConnected: boolean;
  onOpenSettings: () => void;
}

export const Header: React.FC<HeaderProps> = ({ serverConnected, onOpenSettings }) => {
  return (
    <View style={styles.container}>
      {/* Top Navbar */}
      <View style={styles.navBar}>
        <View style={styles.brandGroup}>
          <View style={styles.logoBox}>
            <Feather name="book-open" size={18} color="#121212" />
          </View>
          <View>
            <Text style={styles.brandTitle}>NOVEL TL</Text>
            <Text style={styles.brandSub}>KAKUYOMU → EPUB</Text>
          </View>
        </View>

        {/* Server Status & Settings CTA */}
        <TouchableOpacity
          style={styles.settingsButton}
          onPress={onOpenSettings}
          activeOpacity={0.75}
        >
          <View
            style={[
              styles.statusDot,
              { backgroundColor: serverConnected ? THEME.colors.lime : THEME.colors.danger },
            ]}
          />
          <Text style={styles.settingsText}>
            {serverConnected ? 'SERVER ON' : 'CONNECT'}
          </Text>
          <Ionicons name="settings-sharp" size={13} color="#121212" />
        </TouchableOpacity>
      </View>

      {/* Sleek Feature Bar (Compact Neo-Brutalist Strip) */}
      <View style={styles.featureStrip}>
        <View style={styles.featureItemDark}>
          <View style={styles.featureIconBadge}>
            <Ionicons name="flash" size={10} color="#121212" />
          </View>
          <View style={styles.featureCol}>
            <Text style={styles.featureTitleLight}>100% OFFLINE AI</Text>
            <Text style={styles.featureSubLight}>Sugoi V4 + Qwen 2.5</Text>
          </View>
        </View>

        <View style={styles.featureItemPeach}>
          <Text style={styles.featurePeachLabel}>EPUB 3</Text>
          <View style={styles.cleanPill}>
            <Text style={styles.cleanPillText}>0 WATERMARK</Text>
          </View>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginBottom: 14,
  },
  navBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: THEME.colors.white,
    borderWidth: THEME.border.width,
    borderColor: THEME.border.color,
    borderRadius: THEME.border.radius,
    paddingHorizontal: 14,
    paddingVertical: 10,
    marginBottom: 8,
    ...THEME.shadowSm,
  },
  brandGroup: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  logoBox: {
    width: 36,
    height: 36,
    backgroundColor: THEME.colors.lime,
    borderWidth: THEME.border.thin,
    borderColor: THEME.border.color,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  brandTitle: {
    fontSize: 16,
    fontWeight: '900',
    color: THEME.colors.black,
    letterSpacing: 0.5,
  },
  brandSub: {
    fontSize: 9,
    fontFamily: 'monospace',
    fontWeight: 'bold',
    color: THEME.colors.grayText,
    marginTop: 1,
  },
  settingsButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: THEME.colors.canvas,
    borderWidth: THEME.border.thin,
    borderColor: THEME.border.color,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: '#121212',
  },
  settingsText: {
    fontSize: 10,
    fontFamily: 'monospace',
    fontWeight: '900',
    color: THEME.colors.black,
  },
  featureStrip: {
    flexDirection: 'row',
    borderWidth: THEME.border.width,
    borderColor: THEME.border.color,
    borderRadius: THEME.border.radiusSm,
    overflow: 'hidden',
    ...THEME.shadowSm,
  },
  featureItemDark: {
    flex: 1.35,
    backgroundColor: THEME.colors.espresso,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 10,
    paddingVertical: 7,
    borderRightWidth: THEME.border.thin,
    borderColor: THEME.border.color,
  },
  featureIconBadge: {
    width: 18,
    height: 18,
    borderRadius: 5,
    backgroundColor: THEME.colors.lime,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#121212',
  },
  featureCol: {
    justifyContent: 'center',
  },
  featureTitleLight: {
    fontSize: 10,
    fontWeight: '900',
    color: THEME.colors.lime,
    letterSpacing: 0.3,
  },
  featureSubLight: {
    fontSize: 8,
    fontFamily: 'monospace',
    fontWeight: 'bold',
    color: '#D1D5DB',
  },
  featureItemPeach: {
    flex: 1,
    backgroundColor: THEME.colors.peach,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 10,
    paddingVertical: 7,
  },
  featurePeachLabel: {
    fontSize: 10,
    fontFamily: 'monospace',
    fontWeight: '900',
    color: THEME.colors.black,
  },
  cleanPill: {
    backgroundColor: THEME.colors.lime,
    borderWidth: 1,
    borderColor: '#121212',
    paddingHorizontal: 5,
    paddingVertical: 2,
    borderRadius: 4,
  },
  cleanPillText: {
    fontSize: 8,
    fontFamily: 'monospace',
    fontWeight: '900',
    color: '#121212',
  },
});
