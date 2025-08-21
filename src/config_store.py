"""Almacenamiento sencillo de configuración de la aplicación.

Guarda:
  - mic_index: índice del micrófono seleccionado (int o None)
  - output_device_index: índice del dispositivo de salida (int o None)

Los índices coinciden con el orden enumerado al mostrar dispositivos.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'
DATA_DIR.mkdir(exist_ok=True)
CFG_PATH = DATA_DIR / 'config.json'

DEFAULT_CFG: Dict[str, Any] = {
    "mic_index": None,
    "output_device_index": None,
}

def load_config() -> Dict[str, Any]:
    try:
        if CFG_PATH.exists():
            data = json.loads(CFG_PATH.read_text(encoding='utf-8'))
            merged = DEFAULT_CFG.copy()
            for k in DEFAULT_CFG:
                if k in data:
                    merged[k] = data[k]
            return merged
    except Exception:
        pass
    return DEFAULT_CFG.copy()

def save_config(cfg: Dict[str, Any]) -> bool:
    try:
        out = {k: cfg.get(k) for k in DEFAULT_CFG.keys()}
        CFG_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
        return True
    except Exception:
        return False
