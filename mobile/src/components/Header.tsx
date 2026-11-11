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
            <Feather name="book-open" size={18} color="#000000" />
          </View>
          <View>
            <Text style={styles.brandTitle}>NOVEL TL</Text>
            <Text style={styles.brandSub}>KAKUYOMU → EPUB</Text>
          </View>
        </View>

        {/* Server & Settings CTA */}
        <TouchableOpacity
          style={styles.settingsButton}
          onPress={onOpenSettings}
          activeOpacity={0.8}
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
          <Ionicons name="settings-outline" size={14} color="#000000" />
        </TouchableOpacity>
      </View>

      {/* Hero 3-Split Neo-Brutalist Card */}
      <View style={styles.heroCard}>
        {/* Left Dark Column */}
        <View style={styles.heroColDark}>
          <View style={styles.miniBadgeLime}>
            <Ionicons name="flash" size={10} color="#000000" />
            <Text style={styles.miniBadgeText}>AI LOCAL</Text>
          </View>
          <Text style={styles.heroTextLime}>100% OFFLINE</Text>
          <Text style={styles.heroSubText}>Sugoi V4 + Qwen 2.5</Text>
        </View>

        {/* Right Split Column */}
        <View style={styles.heroColRight}>
          <View style={styles.heroRowTop}>
            <Text style={styles.rowLabelText}>KAKUYOMU</Text>
            <View style={styles.miniBadgeWhite}>
              <Text style={styles.miniBadgeTextSm}>SOURCE</Text>
            </View>
          </View>
          <View style={styles.heroRowBottom}>
            <Text style={styles.rowLabelText}>EPUB 3 CLEAN</Text>
            <View style={styles.miniBadgeLime}>
              <Text style={styles.miniBadgeTextSm}>NO COVER</Text>
            </View>
          </View>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginBottom: 16,
  },
  navBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: THEME.colors.white,
    borderWidth: THEME.border.width,
    borderColor: THEME.border.color,
    borderRadius: THEME.border.radius,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginBottom: 10,
    ...THEME.shadowSm,
  },
  brandGroup: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  logoBox: {
    width: 34,
    height: 34,
    backgroundColor: THEME.colors.lime,
    borderWidth: THEME.border.thin,
    borderColor: THEME.border.color,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  brandTitle: {
    fontSize: 15,
    fontWeight: '900',
    color: THEME.colors.black,
    letterSpacing: 0.5,
  },
  brandSub: {
    fontSize: 9,
    fontFamily: 'monospace',
    fontWeight: 'bold',
    color: THEME.colors.grayText,
  },
  settingsButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: THEME.colors.white,
    borderWidth: THEME.border.thin,
    borderColor: THEME.border.color,
    paddingHorizontal: 8,
    paddingVertical: 5,
    borderRadius: 8,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: '#000000',
  },
  settingsText: {
    fontSize: 10,
    fontFamily: 'monospace',
    fontWeight: '900',
    color: THEME.colors.black,
  },
  heroCard: {
    flexDirection: 'row',
    borderWidth: THEME.border.width,
    borderColor: THEME.border.color,
    borderRadius: THEME.border.radius,
    overflow: 'hidden',
    ...THEME.shadowSm,
  },
  heroColDark: {
    flex: 1.2,
    backgroundColor: THEME.colors.espresso,
    padding: 12,
    borderRightWidth: THEME.border.width,
    borderColor: THEME.border.color,
  },
  heroColRight: {
    flex: 1.3,
  },
  heroRowTop: {
    backgroundColor: THEME.colors.peach,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 10,
    paddingVertical: 9,
    borderBottomWidth: THEME.border.width,
    borderColor: THEME.border.color,
  },
  heroRowBottom: {
    backgroundColor: THEME.colors.pink,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 10,
    paddingVertical: 9,
  },
  rowLabelText: {
    fontSize: 11,
    fontFamily: 'monospace',
    fontWeight: '900',
    color: THEME.colors.black,
  },
  heroTextLime: {
    fontSize: 13,
    fontWeight: '900',
    color: THEME.colors.lime,
    marginTop: 6,
  },
  heroSubText: {
    fontSize: 9,
    fontFamily: 'monospace',
    fontWeight: 'bold',
    color: '#D1D5DB',
  },
  miniBadgeLime: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: THEME.colors.lime,
    borderWidth: 1,
    borderColor: '#000000',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
    alignSelf: 'flex-start',
  },
  miniBadgeWhite: {
    backgroundColor: THEME.colors.white,
    borderWidth: 1,
    borderColor: '#000000',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
  },
  miniBadgeText: {
    fontSize: 9,
    fontFamily: 'monospace',
    fontWeight: '900',
    color: '#000000',
  },
  miniBadgeTextSm: {
    fontSize: 8,
    fontFamily: 'monospace',
    fontWeight: '900',
    color: '#000000',
  },
});
