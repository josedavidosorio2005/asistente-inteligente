"""Módulo de consola para mostrar un panel simple (legacy)."""
import os
import json


def mostrar_panel() -> str:
    print("\n--- Panel de Control ---")
    eventos_path = os.path.join(os.path.dirname(__file__), '..', 'resumenes', 'eventos.json')
    if os.path.exists(eventos_path):
        with open(eventos_path, 'r', encoding='utf-8') as f:
            eventos = json.load(f)
        print("Eventos:")
        for ev in eventos:
            print(f"- {ev['evento']} ({ev['fecha']})")
    else:
        print("No hay eventos registrados.")
    return "Panel mostrado en consola."
