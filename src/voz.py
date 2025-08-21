"""Módulo de voz (ASR + TTS) con personalización y motores seleccionables.

Expuesto para compatibilidad: escuchar_comando, escuchar_comando_continuo, hablar.

Personalización (persistida en tabla config SQLite vía config_store/db):
 - voice_lang (str) : código de idioma gTTS (ej: 'es', 'en', 'fr').
 - voice_speed (str): 'lento' | 'normal' | 'rapido'.
 - voice_gender (str): 'femenina' | 'masculina' (placeholder, gTTS no permite cambio real de género).

Si speed == 'rapido' intenta acelerar el audio usando pydub si está disponible.
"""
import speech_recognition as sr
from playsound import playsound
try:
    from gtts import gTTS  # gTTS puede faltar si se elige edge
except Exception:  # pragma: no cover
    gTTS = None  # type: ignore
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
def _tts_gtts(texto: str, lang: str, speed: str, gender: str, callback_estado=None) -> str:
    if not gTTS:
        raise RuntimeError("gTTS no disponible")
    slow_flag = True if speed == 'lento' else False
    tts = gTTS(text=texto, lang=lang, slow=slow_flag)
    tmp_mp3 = tempfile.mktemp(suffix='.mp3')
    tts.save(tmp_mp3)
    # Aceleración rápida
    if speed == 'rapido':
        try:
            from pydub import AudioSegment  # type: ignore
            seg = AudioSegment.from_file(tmp_mp3)
            sped = seg._spawn(seg.raw_data, overrides={'frame_rate': int(seg.frame_rate * 1.25)})
            sped = sped.set_frame_rate(seg.frame_rate)
            fast = tempfile.mktemp(suffix='.mp3')
            sped.export(fast, format='mp3')
            os.remove(tmp_mp3)
            tmp_mp3 = fast
        except Exception:
            pass
    return tmp_mp3

def _tts_edge(texto: str, lang: str, speed: str, gender: str, voice_name: Optional[str], callback_estado=None) -> str:
    """Genera audio usando edge-tts (necesita paquete edge-tts instalado)."""
    try:
        import asyncio, edge_tts  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("edge-tts no disponible: instala 'edge-tts'") from e
    # Seleccionar voz
    # Si no se especifica voice_name, elegir una por idioma y género
    async def _gen():
        voices = await edge_tts.list_voices()  # list of dict
        selected = None
        # Intentar coincidencia por lang y gender
        for v in voices:
            if lang.lower() in v.get('Locale','').lower() and gender.lower().startswith(v.get('Gender','').lower()[:1]):
                selected = v['Name']
                if voice_name and v['Name'] == voice_name:
                    break
        if not selected and voices:
            selected = voices[0]['Name']
        chosen = voice_name or selected
        if not chosen:
            raise RuntimeError('No hay voces disponibles edge')
        rate = {'lento':'-15%','normal':'0%','rapido':'+15%'}.get(speed,'0%')
        communicate = edge_tts.Communicate(texto, chosen, rate=rate)
        tmp_mp3 = tempfile.mktemp(suffix='.mp3')
        with open(tmp_mp3, 'wb') as f:
            async for chunk in communicate.stream():
                if chunk['type'] == 'audio':
                    f.write(chunk['data'])
        return tmp_mp3, chosen
    tmp_mp3, chosen_voice = asyncio.run(_gen())
    if callback_estado:
        callback_estado(f"[TTS] Voz Edge: {chosen_voice}")
    return tmp_mp3

def hablar(texto: str, callback_estado=None, *, lang: Optional[str] = None, speed: Optional[str] = None, gender: Optional[str] = None, provider: Optional[str] = None) -> None:
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
    provider = provider or cfg.get('voice_provider') or 'gtts'
    # Validar disponibilidad de motor edge
    if provider == 'edge':
        try:
            import edge_tts  # type: ignore  # noqa: F401
        except Exception:
            # Fallback a gtts si edge no está instalado
            provider = 'gtts'
    voice_name = cfg.get('voice_name') if isinstance(cfg.get('voice_name'), str) else None
    tmp_mp3 = None
    try:
        if callback_estado:
            callback_estado(f"[TTS] Generando voz {provider} ({lang}, {speed}, {gender})…")
        if provider == 'edge':
            tmp_mp3 = _tts_edge(texto, lang, speed, gender, voice_name, callback_estado)
        else:  # gtts por defecto
            tmp_mp3 = _tts_gtts(texto, lang, speed, gender, callback_estado)
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
