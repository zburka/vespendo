import { Alert as NativAlert, type AlertButton, Platform } from 'react-native';

/**
 * `Alert`-kompatibilis üzenetablak. Natívan a rendszer párbeszédablaka, weben (PWA) a `window.alert` / `window.confirm`,
 * mert a react-native-web `Alert.alert`-je nem csinál semmit. Többgombos hívásnál a webes megerősítés `Rendben` ágán
 * az utolsó nem-megszakító gomb fut le.
 */
export const Alert = {
  alert(cim: string, uzenet?: string, gombok?: AlertButton[]) {
    if (Platform.OS !== 'web') {
      NativAlert.alert(cim, uzenet, gombok);
      return;
    }
    const szoveg = uzenet ? `${cim}\n\n${uzenet}` : cim;
    const muvelet = gombok?.filter((g) => g.style !== 'cancel' && g.onPress);
    if (gombok && gombok.length > 1 && muvelet?.length) {
      if (window.confirm(szoveg)) muvelet[muvelet.length - 1].onPress?.();
      return;
    }
    window.alert(szoveg);
    gombok?.[0]?.onPress?.();
  },
};
