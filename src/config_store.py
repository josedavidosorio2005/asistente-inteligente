"""Fachada de compatibilidad para configuración usando la base de datos.

Se mantiene la misma interfaz pública (load_config/save_config) pero ahora
los valores se guardan en la tabla `config` de SQLite (ver db.config_*).

Claves reconocidas:
 - mic_index
 - output_device_index
Se aceptan valores adicionales y se devuelven al cargar.
"""
from __future__ import annotations
from typing import Any, Dict

try:
    from src import db  # tipo: ignore
except Exception:  # pragma: no cover
    import db  # type: ignore

DEFAULT_CFG: Dict[str, Any] = {
    'mic_index': None,
    'output_device_index': None,
    'voice_lang': 'es',
    'voice_speed': 'normal',  # lento | normal | rapido
    'voice_gender': 'femenina',  # femenina | masculina (placeholder)
    'voice_provider': 'gtts',  # gtts | edge
    'voice_name': None,  # nombre específico motor (Edge)
    'ui_theme': 'neon',  # neon | claro | oscuro
}

def load_config() -> Dict[str, Any]:
    data = DEFAULT_CFG.copy()
    try:
        all_cfg = db.config_load_all()
        for k, v in all_cfg.items():
            data[k] = v
    except Exception:
        pass
    return data

def save_config(cfg: Dict[str, Any]) -> bool:
    ok = True
    for k, v in cfg.items():
        try:
            if not db.config_set(k, v):
                ok = False
        except Exception:
            ok = False
    return ok
