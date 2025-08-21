"""Backend de calendario usando SQLite (db.py) con API compatible previa.

Se mantienen los nombres de funciones para no romper el resto del código.
"""
from __future__ import annotations
from datetime import datetime, timedelta
try:  # Permite uso como 'from src import calendario' y también 'import calendario'
    from . import db  # type: ignore
except ImportError:  # cuando se importa como módulo suelto
    import db  # type: ignore


def crear_evento(evento: str, fecha: str, hora: str | None = None) -> str:
    ok = db.event_create(evento, fecha, hora)
    return "Evento creado." if ok else "No se pudo crear el evento (posible duplicado)."


def consultar_eventos(modo: str) -> tuple[list[dict], str]:
    hoy = datetime.now().date()
    if modo == 'hoy':
        evs = db.event_list_day(str(hoy))
        eventos = [
            {
                'evento': e['title'],
                'fecha': e['date'],
                'hora': e['time'],
                'completado': bool(e['completed'])
            } for e in evs
        ]
        if eventos:
            return eventos, f"Eventos para hoy {hoy}: {len(eventos)}"
        return [], "No tienes eventos para hoy."
    elif modo == 'semana':
        # Semana hasta domingo (o 6 días más desde hoy)
        fin_semana = hoy + timedelta(days=6 - hoy.weekday())
        evs = db.event_list_week(str(hoy), str(fin_semana))
        eventos = [
            {
                'evento': e['title'],
                'fecha': e['date'],
                'hora': e['time'],
                'completado': bool(e['completed'])
            } for e in evs
        ]
        if eventos:
            return eventos, f"Eventos para esta semana ({hoy} a {fin_semana})."
        return [], "No tienes eventos para esta semana."
    return [], "Modo no soportado."


def editar_evento(idx: int, nuevo_evento: str, nueva_fecha: str) -> str:
    # No hay índice en el nuevo modelo; se omite (se podría mapear con ID real)
    return "Edición por índice no soportada en BD."


def eliminar_evento(idx: int) -> str:
    return "Eliminación por índice no soportada en BD."


def leer_eventos(dias_hacia_adelante: int = 365) -> list[dict]:
    """Devuelve eventos próximos hasta 'dias_hacia_adelante'.

    Parametros:
        dias_hacia_adelante: rango futuro a recuperar (por defecto 365).
    """
    from datetime import date as _date
    if dias_hacia_adelante < 0:
        dias_hacia_adelante = 0
    start = _date.today()
    end = start + timedelta(days=dias_hacia_adelante)
    try:
        evs = db.event_list_week(str(start), str(end))
    except Exception:
        return []
    return [{
        'evento': e['title'],
        'fecha': e['date'],
        'hora': e['time'],
        'completado': bool(e['completed'])
    } for e in evs]


def marcar_evento_completado(evento: str, fecha: str, hora: str | None = None, completado: bool = True) -> bool:
    return db.event_toggle_complete(evento, fecha, hora, completado)


def eliminar_evento_por_datos(evento: str, fecha: str, hora: str | None = None) -> int:
    return db.event_delete(evento, fecha, hora)
