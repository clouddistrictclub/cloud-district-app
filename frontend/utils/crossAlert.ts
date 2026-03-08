import { Alert, Platform } from 'react-native';

type AlertButton = {
  text: string;
  style?: 'default' | 'cancel' | 'destructive';
  onPress?: () => void;
};

export function crossAlert(title: string, message: string, buttons?: AlertButton[]) {
  if (Platform.OS !== 'web') {
    Alert.alert(title, message, buttons);
    return;
  }

  if (!buttons || buttons.length === 0) {
    window.alert(`${title}\n\n${message}`);
    return;
  }

  const cancel = buttons.find(b => b.style === 'cancel');
  const action = buttons.find(b => b.style !== 'cancel') || buttons[0];

  if (buttons.length === 1) {
    window.alert(`${title}\n\n${message}`);
    buttons[0].onPress?.();
    return;
  }

  const confirmed = window.confirm(`${title}\n\n${message}`);
  if (confirmed) {
    action?.onPress?.();
  } else {
    cancel?.onPress?.();
  }
}
