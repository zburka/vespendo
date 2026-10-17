import { useEffect, useState } from 'react';
import { Keyboard, Platform } from 'react-native';

/**
 * iOS-en a billentyűzet magassága (a párbeszédablakot ennyivel feljebb toljuk, hogy a Mentés látszódjon).
 * Androidon az ablak maga átméreteződik, ott 0.
 */
export function useKeyboardHeight(): number {
  const [magassag, setMagassag] = useState(0);

  useEffect(() => {
    if (Platform.OS !== 'ios') return;
    const mutat = Keyboard.addListener('keyboardWillShow', (e) =>
      setMagassag(e.endCoordinates.height),
    );
    const rejt = Keyboard.addListener('keyboardWillHide', () => setMagassag(0));
    return () => {
      mutat.remove();
      rejt.remove();
    };
  }, []);

  return magassag;
}
