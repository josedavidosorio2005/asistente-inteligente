"""Módulo de voz legado (ASR + TTS) usado como respaldo.

Expuesto para compatibilidad: escuchar_comando, escuchar_comando_continuo, hablar.
"""
import speech_recognition as sr
from gtts import gTTS
from playsound import playsound
import tempfile
import os

def escuchar_comando(max_reintentos: int = 3, callback_estado=None) -> str | None:
    r = sr.Recognizer()
    with sr.Microphone() as source:
        if callback_estado:
            callback_estado("Calibrando micrófono, por favor guarda silencio...")
        r.adjust_for_ambient_noise(source, duration=1.5)
        if callback_estado:
            callback_estado(f"Nivel de ruido detectado: {r.energy_threshold:.2f}")
        for intento in range(max_reintentos):
            if callback_estado:
                callback_estado("Habla ahora...")
            try:
                audio = r.listen(source, phrase_time_limit=10)
                if callback_estado:
                    callback_estado("Procesando...")
                texto = r.recognize_google(audio, language='es-ES')
                if callback_estado:
                    callback_estado(f"Transcripción: {texto}")
                return texto
            except sr.UnknownValueError:
                if callback_estado:
                    callback_estado("No se entendió, intenta de nuevo...")
            except Exception as e:
                if callback_estado:
                    callback_estado(f"[ERROR] No se pudo transcribir el audio: {e}")
        return None

# Escucha continuamente hasta captar un comando válido
def escuchar_comando_continuo(callback_estado=None) -> str | None:
    if callback_estado:
        callback_estado("(Micrófono activo, di un comando...)")
    while True:
        texto = escuchar_comando(callback_estado=callback_estado)
        if texto:
            return texto

# Función para hablar cualquier texto (respuesta profesional)
def hablar(texto: str, callback_estado=None) -> None:
    tmp_mp3 = None
    try:
        tts = gTTS(text=texto, lang='es', slow=False)
        tmp_mp3 = tempfile.mktemp(suffix='.mp3')
        tts.save(tmp_mp3)
        playsound(tmp_mp3)
    except Exception as e:
        if callback_estado:
            callback_estado(f"[ERROR] No se pudo reproducir el audio: {e}")
    finally:
        if tmp_mp3 and os.path.exists(tmp_mp3):
            try:
                os.remove(tmp_mp3)
            except Exception:
                pass
