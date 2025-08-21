"""Gestión sencilla de eventos y recordatorios.

Persiste en `resumenes/eventos.json`.
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timedelta

EVENTOS_PATH = os.path.join(os.path.dirname(__file__), '..', 'resumenes', 'eventos.json')


def crear_evento(evento: str, fecha: str, hora: str | None = None) -> str:
    """Crea un evento con fecha ISO (YYYY-MM-DD) y hora opcional (HH:MM).

    Devuelve mensaje de estado.
    """
    if os.path.exists(EVENTOS_PATH):
        with open(EVENTOS_PATH, 'r', encoding='utf-8') as f:
            eventos = json.load(f)
    else:
        eventos = []
    ev = {'evento': evento, 'fecha': fecha, 'completado': False}
    if hora:
        ev['hora'] = hora
    eventos.append(ev)
    with open(EVENTOS_PATH, 'w', encoding='utf-8') as f:
        json.dump(eventos, f, ensure_ascii=False, indent=2)
    return "Evento creado."
# Consulta eventos por día o semana
def consultar_eventos(modo: str) -> tuple[list[dict], str]:
    """Consulta eventos por modo ('hoy' o 'semana').

    Retorna una tupla: (lista_eventos, mensaje_humano).
    """
    if not os.path.exists(EVENTOS_PATH):
        return [], "No hay eventos guardados."
    with open(EVENTOS_PATH, 'r', encoding='utf-8') as f:
        eventos = json.load(f)
    hoy = datetime.now().date()
    if modo == 'hoy':
        encontrados = [ev for ev in eventos if ev['fecha'] == str(hoy)]
        if encontrados:
            return encontrados, f"Eventos para hoy {hoy}: {encontrados}"
        else:
            return [], "No tienes eventos para hoy."
    elif modo == 'semana':
        fin_semana = hoy + timedelta(days=6-hoy.weekday())
        encontrados = [ev for ev in eventos if hoy <= datetime.strptime(ev['fecha'], '%Y-%m-%d').date() <= fin_semana]
        if encontrados:
            return encontrados, f"Eventos para esta semana ({hoy} a {fin_semana}): {encontrados}"
        else:
            return [], "No tienes eventos para esta semana."

def editar_evento(idx: int, nuevo_evento: str, nueva_fecha: str) -> str:
    """Edita un evento por índice. Devuelve mensaje de estado."""
    if not os.path.exists(EVENTOS_PATH):
        return "No hay eventos para editar."
    with open(EVENTOS_PATH, 'r', encoding='utf-8') as f:
        eventos = json.load(f)
    if 0 <= idx < len(eventos):
        eventos[idx]['evento'] = nuevo_evento
        eventos[idx]['fecha'] = nueva_fecha
        with open(EVENTOS_PATH, 'w', encoding='utf-8') as f:
            json.dump(eventos, f, ensure_ascii=False, indent=2)
        return "Evento editado."
    else:
        return "Índice no válido."

def eliminar_evento(idx: int) -> str:
    """Elimina un evento por índice. Devuelve mensaje de estado."""
    if not os.path.exists(EVENTOS_PATH):
        return "No hay eventos para eliminar."
    with open(EVENTOS_PATH, 'r', encoding='utf-8') as f:
        eventos = json.load(f)
    if 0 <= idx < len(eventos):
        eventos.pop(idx)
        with open(EVENTOS_PATH, 'w', encoding='utf-8') as f:
            json.dump(eventos, f, ensure_ascii=False, indent=2)
        return "Evento eliminado."
    else:
        return "Índice no válido."

def leer_eventos() -> list[dict]:
    """Lee y devuelve todos los eventos guardados (puede incluir clave 'hora')."""
    if not os.path.exists(EVENTOS_PATH):
        return []
    try:
        with open(EVENTOS_PATH, 'r', encoding='utf-8') as f:
            eventos = json.load(f)
        if isinstance(eventos, list):
            return eventos
        return []
    except Exception:
        return []

def marcar_evento_completado(evento: str, fecha: str, hora: str | None = None, completado: bool = True) -> bool:
    """Marca el primer evento que coincida como completado (o no).

    Coincide por fecha y título; si se proporciona hora, también por hora.
    Devuelve True si se actualizó algo.
    """
    if not os.path.exists(EVENTOS_PATH):
        return False
    try:
        with open(EVENTOS_PATH, 'r', encoding='utf-8') as f:
            eventos = json.load(f)
        cambiado = False
        for ev in eventos:
            if ev.get('fecha') == fecha and ev.get('evento') == evento and (hora is None or ev.get('hora') == hora):
                ev['completado'] = bool(completado)
                cambiado = True
                break
        if cambiado:
            with open(EVENTOS_PATH, 'w', encoding='utf-8') as f:
                json.dump(eventos, f, ensure_ascii=False, indent=2)
        return cambiado
    except Exception:
        return False

def eliminar_evento_por_datos(evento: str, fecha: str, hora: str | None = None) -> int:
    """Elimina eventos que coincidan con (evento, fecha [, hora]).

    Si hora es None elimina todos los que coincidan por título y fecha sin considerar hora.
    Devuelve la cantidad eliminada.
    """
    if not os.path.exists(EVENTOS_PATH):
        return 0
    try:
        with open(EVENTOS_PATH, 'r', encoding='utf-8') as f:
            eventos = json.load(f)
        inicial = len(eventos)
        if hora is None:
            eventos = [ev for ev in eventos if not (ev.get('evento') == evento and ev.get('fecha') == fecha)]
        else:
            eventos = [ev for ev in eventos if not (ev.get('evento') == evento and ev.get('fecha') == fecha and ev.get('hora') == hora)]
        eliminados = inicial - len(eventos)
        if eliminados:
            with open(EVENTOS_PATH, 'w', encoding='utf-8') as f:
                json.dump(eventos, f, ensure_ascii=False, indent=2)
        return eliminados
    except Exception:
        return 0
