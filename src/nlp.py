"""Módulo sencillo de NLP para detectar intención en comandos de texto.

No requiere dependencias pesadas obligatorias. Intenta usar spaCy si está
instalado (para lematización y normalización); si no, recurre a heurísticas
simples con regex y similitud difusa.

API principal:
    analyze(texto: str) -> dict
        Devuelve un diccionario con claves:
           intent: str | None
           params: dict
           confidence: float (0-1)
           tokens: list[str] (debug)

Intenciones soportadas (intent):
    greet, help, time, create_event, delete_event, query_events_day, query_events_week,
    open_app, create_note, delete_note, search_note, cleanup_legacy, reminder_create,
    exit_app, change_theme, change_voice

Se diseñó para ampliarse fácilmente agregando patrones a INTENT_PATTERNS.
"""
from __future__ import annotations
import re, difflib, datetime as _dt
try:
    import dateparser  # type: ignore
except Exception:  # pragma: no cover
    dateparser = None  # fallback
from typing import Optional, Dict, Any, List, Tuple

_nlp = None  # spaCy pipeline (lazy)

def _load_spacy():
    global _nlp
    if _nlp is not None:
        return _nlp
    try:
        import spacy  # type: ignore
        # Intentar modelo español, fallback a modelo pequeño inglés para normalizar
        for model in ("es_core_news_sm", "en_core_web_sm"):
            try:
                _nlp = spacy.load(model)  # type: ignore
                break
            except Exception:
                continue
    except Exception:
        _nlp = False  # Marcador de que no hay spaCy
    return _nlp

NORMALIZE_MAP = {
    'á':'a','é':'e','í':'i','ó':'o','ú':'u','ü':'u','ñ':'n'
}

def _basic_normalize(text: str) -> str:
    text = text.lower().strip()
    for a,b in NORMALIZE_MAP.items():
        text = text.replace(a,b)
    return re.sub(r"\s+"," ", text)

DATE_REGEX = re.compile(r"(\d{4}-\d{2}-\d{2})")
TIME_REGEX = re.compile(r"(\d{1,2}:\d{2})")

INTENT_PATTERNS: List[Tuple[str, List[str]]] = [
    ("greet", ["hola","buenos dias","buenas tardes","buenas noches"]),
    ("help", ["/ayuda","ayuda","help"]),
    ("time", ["hora es","hora tienes","que hora"]),
    ("query_events_day", ["que tengo hoy","qué tengo hoy","agenda hoy"]),
    ("query_events_week", ["que tengo semana","qué tengo semana","agenda semana"]),
    ("cleanup_legacy", ["/limpiar_legacy"]),
    ("exit_app", ["salir","cerrar asistente","terminar asistente"]),
]

APP_KEYWORDS = ["calculadora","bloc de notas","notas","navegador","chrome","internet","explorador","terminal"]

THEMES = ["claro","oscuro"]
VOICE_SPEEDS = ["lento","normal","rapido"]
VOICE_GENDERS = ["masculina","femenina"]

def _ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()

def _best_pattern(norm: str) -> tuple[Optional[str], float]:
    best = (None, 0.0)
    for intent, pats in INTENT_PATTERNS:
        for p in pats:
            r = _ratio(norm, p)
            if r > best[1]:
                best = (intent, r)
    return best

EVENT_CREATE_REGEX = re.compile(
    r"crear evento (?P<title>.+?) (?:el|para) (?P<date>\d{4}-\d{2}-\d{2})(?:.*?(?:a las )?(?P<time>\d{1,2}:\d{2}))?",
    re.IGNORECASE
)
EVENT_DELETE_REGEX = re.compile(
    r"eliminar evento (?P<title>.+?) (?:el|de) (?P<date>\d{4}-\d{2}-\d{2})(?:.*?(?:a las )?(?P<time>\d{1,2}:\d{2}))?",
    re.IGNORECASE
)
NOTE_CREATE_REGEX = re.compile(r"crear nota (?P<title>.+?)(?: en (?P<folder>.+))?$", re.IGNORECASE)
NOTE_DELETE_REGEX = re.compile(r"eliminar nota (?P<title>.+?)(?: en (?P<folder>.+))?$", re.IGNORECASE)
NOTE_SEARCH_REGEX = re.compile(r"buscar nota (?P<term>.+?)(?: en (?P<folder>.+))?$", re.IGNORECASE)

REMINDER_REGEX = re.compile(
    r"(crear|pon|establece?) (?:un )?(recordatorio|alarma) (?P<title>.+?) (?:para|el|en) (?P<when>.+)$",
    re.IGNORECASE
)

CHANGE_THEME_REGEX = re.compile(r"(cambia|poner|pon) tema (?P<theme>\w+)", re.IGNORECASE)
CHANGE_VOICE_REGEX = re.compile(r"(cambia|poner|pon) voz (?P<voice>.+)$", re.IGNORECASE)

def _parse_natural_datetime(frase: str) -> Optional[_dt.datetime]:
    if not dateparser:
        return None
    settings = {"PREFER_DATES_FROM":"future","RELATIVE_BASE": _dt.datetime.now()}
    try:
        return dateparser.parse(frase, settings=settings)  # type: ignore
    except Exception:
        return None

def analyze(text: str) -> Dict[str, Any]:
    original = text
    norm = _basic_normalize(text)
    tokens: List[str] = norm.split()
    params: Dict[str, Any] = {}

    # Eventos crear
    m = EVENT_CREATE_REGEX.search(text)
    if m:
        params = m.groupdict()
        return {"intent":"create_event","params":params,"confidence":0.95,"tokens":tokens}
    # Eventos eliminar
    m = EVENT_DELETE_REGEX.search(text)
    if m:
        params = m.groupdict()
        return {"intent":"delete_event","params":params,"confidence":0.95,"tokens":tokens}
    # Notas
    for intent, rgx in (("create_note", NOTE_CREATE_REGEX),("delete_note", NOTE_DELETE_REGEX),("search_note", NOTE_SEARCH_REGEX)):
        m = rgx.search(text)
        if m:
            params = m.groupdict()
            return {"intent":intent,"params":params,"confidence":0.9,"tokens":tokens}
    # Recordatorio
    m = REMINDER_REGEX.search(text)
    if m:
        gd = m.groupdict()
        dt = _parse_natural_datetime(gd.get('when',''))
        if dt:
            params = {"title": gd.get('title'), "when_iso": dt.isoformat()}
            return {"intent":"reminder_create","params":params,"confidence":0.9,"tokens":tokens}
        else:
            params = {"title": gd.get('title'), "when_text": gd.get('when')}
            return {"intent":"reminder_create","params":params,"confidence":0.6,"tokens":tokens}

    # Cambiar tema
    m = CHANGE_THEME_REGEX.search(text)
    if m:
        theme = _basic_normalize(m.group('theme'))
        if theme in THEMES:
            return {"intent":"change_theme","params":{"theme":theme},"confidence":0.9,"tokens":tokens}
        return {"intent":"change_theme","params":{"theme":theme},"confidence":0.5,"tokens":tokens}

    # Cambiar voz (solo marca el texto, UI confirmará)
    m = CHANGE_VOICE_REGEX.search(text)
    if m:
        voice_raw = m.group('voice').strip()
        return {"intent":"change_voice","params":{"voice":voice_raw},"confidence":0.7,"tokens":tokens}

    # Abrir app
    if norm.startswith("abrir "):
        for kw in APP_KEYWORDS:
            if kw in norm:
                return {"intent":"open_app","params":{"app":kw},"confidence":0.85,"tokens":tokens}
        return {"intent":"open_app","params":{},"confidence":0.6,"tokens":tokens}

    # Heurísticos directos
    if "hora" in tokens:
        return {"intent":"time","params":{},"confidence":0.75,"tokens":tokens}

    # Consultas agenda básicas
    if ("que" in tokens or "qué" in original.lower()) and "tengo" in tokens and "hoy" in tokens:
        return {"intent":"query_events_day","params":{},"confidence":0.8,"tokens":tokens}
    if ("que" in tokens or "qué" in original.lower()) and "tengo" in tokens and "semana" in tokens:
        return {"intent":"query_events_week","params":{},"confidence":0.8,"tokens":tokens}

    # Patrón general
    intent, score = _best_pattern(norm)
    if intent and score >= 0.75:
        return {"intent":intent, "params":{}, "confidence":score, "tokens":tokens}

    return {"intent":None, "params":{}, "confidence":0.0, "tokens":tokens}

__all__ = ["analyze"]
