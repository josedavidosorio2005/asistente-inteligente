"""Utilidades centrales de voz (ASR + TTS).

Funciones expuestas:
- listen_once(max_retries=3, state_cb=None) -> str | None
- speak(text, state_cb=None) -> None

Notas:
- Usa Google Speech Recognition vía SpeechRecognition (requiere Internet).
- Usa gTTS + playsound para TTS con limpieza de temporales.
"""
import os
import tempfile
import speech_recognition as sr
from gtts import gTTS
from playsound import playsound

def listen_once(max_retries: int = 3, state_cb=None) -> str | None:
    r = sr.Recognizer()
    with sr.Microphone() as source:
        if state_cb:
            state_cb("Calibrando micrófono, por favor guarda silencio...")
        r.adjust_for_ambient_noise(source, duration=1.5)
        if state_cb:
            state_cb(f"Nivel de ruido detectado: {r.energy_threshold:.2f}")
        for _ in range(max_retries):
            if state_cb:
                state_cb("Habla ahora...")
            try:
                audio = r.listen(source, phrase_time_limit=10)
                if state_cb:
                    state_cb("Procesando...")
                return r.recognize_google(audio, language='es-ES')
            except sr.UnknownValueError:
                if state_cb:
                    state_cb("No se entendió, intenta de nuevo...")
            except Exception as e:
                if state_cb:
                    state_cb(f"[ERROR] No se pudo transcribir el audio: {e}")
        return None

def speak(text: str, state_cb=None) -> None:
    tmp_mp3 = None
    try:
        tts = gTTS(text=text, lang='es', slow=False)
        tmp_mp3 = tempfile.mktemp(suffix='.mp3')
        tts.save(tmp_mp3)
        playsound(tmp_mp3)
    except Exception as e:
        if state_cb:
            state_cb(f"[ERROR] No se pudo reproducir el audio: {e}")
    finally:
        if tmp_mp3 and os.path.exists(tmp_mp3):
            try:
                os.remove(tmp_mp3)
            except Exception:
                pass
