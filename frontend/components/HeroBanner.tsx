import { View, Image, StyleSheet, Platform, Dimensions } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';

const mobileHeroAsset = require('../assets/images/heroes/CloudDistrict_Mobile_Hero_v1_A_Final.png');

const SCREEN_HEIGHT = Dimensions.get('window').height;
const NATIVE_HERO_HEIGHT = Math.round(SCREEN_HEIGHT * 0.26);

export default function HeroBanner({ testID = 'hero-banner' }: { testID?: string }) {
  if (Platform.OS === 'web') {
    let uri: string;
    if (typeof mobileHeroAsset === 'number') {
      uri = Image.resolveAssetSource(mobileHeroAsset)?.uri ?? '';
    } else {
      uri = '';
    }
    return (
      <View style={styles.wrapper}>
        <img
          src={uri}
          style={{ width: '100%', height: '26vh', objectFit: 'cover', objectPosition: 'center center', display: 'block' }}
          data-testid={testID}
          alt="Cloud District Hero"
        />
        <LinearGradient
          colors={['transparent', '#0c0c0c']}
          style={styles.gradient}
        />
      </View>
    );
  }

  return (
    <View style={styles.wrapper}>
      <Image
        source={mobileHeroAsset}
        style={styles.nativeImage}
        resizeMode="cover"
        testID={testID}
      />
      <LinearGradient
        colors={['transparent', '#0c0c0c']}
        style={styles.gradient}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    width: '100%',
    overflow: 'hidden',
  },
  nativeImage: {
    width: '100%',
    height: NATIVE_HERO_HEIGHT,
  },
  gradient: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    height: 60,
  },
});
