/** 运行时必需。训练开始前 TTS「开始拍摄」；与 stepCueSound 亮灯哔声分离。 */

function pickChineseVoice() {
  if (!window.speechSynthesis) return null;
  const voices = window.speechSynthesis.getVoices();
  return voices.find((v) => v.lang && v.lang.startsWith('zh')) || null;
}

export function cancelStartCueSpeech() {
  try {
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
  } catch (error) {
    // ignore
  }
}

export function speakStartCue(text = '开始拍摄') {
  return new Promise((resolve) => {
    if (!window.speechSynthesis || !window.SpeechSynthesisUtterance) {
      resolve();
      return;
    }
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'zh-CN';
      utterance.rate = 1.05;
      const voice = pickChineseVoice();
      if (voice) utterance.voice = voice;
      utterance.onend = () => resolve();
      utterance.onerror = (event) => {
        console.warn('开始提示语音失败:', event.error || event);
        resolve();
      };
      window.speechSynthesis.speak(utterance);
    } catch (error) {
      console.warn('开始提示语音不可用:', error);
      resolve();
    }
  });
}
