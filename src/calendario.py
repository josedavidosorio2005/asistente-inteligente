# calendario.py
# Módulo de gestión de eventos y recordatorios
import json
import os
EVENTOS_PATH = os.path.join(os.path.dirname(__file__), '..', 'resumenes', 'eventos.json')


def crear_evento(evento, fecha):
    """Crea un evento. Devuelve mensaje de estado."""
    if os.path.exists(EVENTOS_PATH):
        with open(EVENTOS_PATH, 'r', encoding='utf-8') as f:
            eventos = json.load(f)
    else:
        eventos = []
    eventos.append({'evento': evento, 'fecha': fecha})
    with open(EVENTOS_PATH, 'w', encoding='utf-8') as f:
        json.dump(eventos, f, ensure_ascii=False, indent=2)
    return "Evento creado."
# Consulta eventos por día o semana
from datetime import datetime, timedelta
def consultar_eventos(modo):
    """Devuelve lista de eventos según el modo ('hoy' o 'semana') y mensaje de estado."""
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

def editar_evento(idx, nuevo_evento, nueva_fecha):
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

def eliminar_evento(idx):
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
