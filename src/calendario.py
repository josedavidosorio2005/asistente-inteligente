# calendario.py
# Módulo de gestión de eventos y recordatorios
import json
import os
EVENTOS_PATH = os.path.join(os.path.dirname(__file__), '..', 'resumenes', 'eventos.json')


def crear_evento():
    print("Describe el evento y la fecha (por ejemplo: 'Reunión 2025-08-15'):")
    texto = input("Evento y fecha: ")
    partes = texto.rsplit(' ', 1)
    if len(partes) != 2:
        print("Formato incorrecto. Usa: <evento> <YYYY-MM-DD>")
        return
    evento, fecha = partes
    if os.path.exists(EVENTOS_PATH):
        with open(EVENTOS_PATH, 'r', encoding='utf-8') as f:
            eventos = json.load(f)
    else:
        eventos = []
    eventos.append({'evento': evento, 'fecha': fecha})
    with open(EVENTOS_PATH, 'w', encoding='utf-8') as f:
        json.dump(eventos, f, ensure_ascii=False, indent=2)
    print("Evento creado.")
# Consulta eventos por día o semana
from datetime import datetime, timedelta
def consultar_eventos(modo):
    if not os.path.exists(EVENTOS_PATH):
        print("No hay eventos guardados.")
        return
    with open(EVENTOS_PATH, 'r', encoding='utf-8') as f:
        eventos = json.load(f)
    hoy = datetime.now().date()
    if modo == 'hoy':
        encontrados = [ev for ev in eventos if ev['fecha'] == str(hoy)]
        if encontrados:
            print(f"Eventos para hoy {hoy}:")
            for ev in encontrados:
                print(f"- {ev['evento']} ({ev['fecha']})")
        else:
            print("No tienes eventos para hoy.")
    elif modo == 'semana':
        fin_semana = hoy + timedelta(days=6-hoy.weekday())
        encontrados = [ev for ev in eventos if hoy <= datetime.strptime(ev['fecha'], '%Y-%m-%d').date() <= fin_semana]
        if encontrados:
            print(f"Eventos para esta semana ({hoy} a {fin_semana}):")
            for ev in encontrados:
                print(f"- {ev['evento']} ({ev['fecha']})")
        else:
            print("No tienes eventos para esta semana.")

def editar_evento():
    if not os.path.exists(EVENTOS_PATH):
        print("No hay eventos para editar.")
        return
    with open(EVENTOS_PATH, 'r', encoding='utf-8') as f:
        eventos = json.load(f)
    for i, ev in enumerate(eventos):
        print(f"[{i}] {ev['evento']} - {ev['fecha']}")
    idx = int(input("Selecciona el número de evento a editar: "))
    if 0 <= idx < len(eventos):
        eventos[idx]['evento'] = input("Nuevo texto del evento: ")
        eventos[idx]['fecha'] = input("Nueva fecha (YYYY-MM-DD): ")
        with open(EVENTOS_PATH, 'w', encoding='utf-8') as f:
            json.dump(eventos, f, ensure_ascii=False, indent=2)
        print("Evento editado.")
    else:
        print("Índice no válido.")

def eliminar_evento():
    if not os.path.exists(EVENTOS_PATH):
        print("No hay eventos para eliminar.")
        return
    with open(EVENTOS_PATH, 'r', encoding='utf-8') as f:
        eventos = json.load(f)
    for i, ev in enumerate(eventos):
        print(f"[{i}] {ev['evento']} - {ev['fecha']}")
    idx = int(input("Selecciona el número de evento a eliminar: "))
    if 0 <= idx < len(eventos):
        eventos.pop(idx)
        with open(EVENTOS_PATH, 'w', encoding='utf-8') as f:
            json.dump(eventos, f, ensure_ascii=False, indent=2)
        print("Evento eliminado.")
    else:
        print("Índice no válido.")
