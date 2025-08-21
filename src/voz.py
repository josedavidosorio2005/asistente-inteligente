"""Módulo de voz (ASR + TTS) con personalización.

Expuesto para compatibilidad: escuchar_comando, escuchar_comando_continuo, hablar.

Personalización (persistida en tabla config SQLite vía config_store/db):
 - voice_lang (str) : código de idioma gTTS (ej: 'es', 'en', 'fr').
 - voice_speed (str): 'lento' | 'normal' | 'rapido'.
 - voice_gender (str): 'femenina' | 'masculina' (placeholder, gTTS no permite cambio real de género).

Si speed == 'rapido' intenta acelerar el audio usando pydub si está disponible.
"""
import speech_recognition as sr
from gtts import gTTS
from playsound import playsound
import tempfile
import os
try:
    from src import config_store  # type: ignore
except Exception:  # pragma: no cover
    import config_store  # type: ignore
from typing import Optional

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
def hablar(texto: str, callback_estado=None, *, lang: Optional[str] = None, speed: Optional[str] = None, gender: Optional[str] = None) -> None:
    """Habla texto usando gTTS respetando preferencias.

    Parámetros explícitos (lang, speed, gender) tienen prioridad; si son None se leen de config.
    speed: lento -> gTTS slow=True; rapido -> post-proceso (pydub) si disponible.
    gender: placeholder (gTTS no soporta cambio real; se guarda sólo como preferencia futura).
    """
    cfg = {}
    try:
        cfg = config_store.load_config()
    except Exception:
        cfg = {}
    lang = lang or cfg.get('voice_lang') or 'es'
    speed = speed or cfg.get('voice_speed') or 'normal'
    gender = gender or cfg.get('voice_gender') or 'femenina'
    slow_flag = True if speed == 'lento' else False
    tmp_mp3 = None
    tmp_fast = None
    try:
        if callback_estado:
            callback_estado(f"[TTS] Generando voz ({lang}, {speed}, {gender})…")
        tts = gTTS(text=texto, lang=lang, slow=slow_flag)
        tmp_mp3 = tempfile.mktemp(suffix='.mp3')
        tts.save(tmp_mp3)
        play_path = tmp_mp3
        if speed == 'rapido':
            try:
                from pydub import AudioSegment  # type: ignore
                seg = AudioSegment.from_file(tmp_mp3)
                # Acelerar 1.25x manteniendo pitch aproximado (método simple cambia pitch ligeramente)
                sped = seg._spawn(seg.raw_data, overrides={'frame_rate': int(seg.frame_rate * 1.25)})
                sped = sped.set_frame_rate(seg.frame_rate)
                tmp_fast = tempfile.mktemp(suffix='.mp3')
                sped.export(tmp_fast, format='mp3')
                play_path = tmp_fast
            except Exception:
                pass
        playsound(play_path)
    except Exception as e:
        if callback_estado:
            callback_estado(f"[ERROR] No se pudo reproducir el audio: {e}")
    finally:
        for f in (tmp_mp3, tmp_fast):
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass
