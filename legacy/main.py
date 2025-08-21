# Legacy: orquestador por voz en consola (reubicado desde src/main.py)
from legacy.vision import analizar_pantalla
from src.voz import escuchar_comando, escuchar_comando_continuo, hablar
from src.calendario import crear_evento, editar_evento, eliminar_evento, consultar_eventos
from src.ia import responder_pregunta
from src.interfaz import mostrar_panel

def iniciar_asistente():
    # Contenido original mantenido sin cambios significativos
    print("Bienvenido al asistente inteligente (legacy consola).")
    nombre_clave = escuchar_comando() or input("Nombre de activación (Enter para 'asistente'): ").strip().lower() or "asistente"
    print(f"Nombre clave: '{nombre_clave}'. Di '{nombre_clave}' seguido de tu comando.")
    while True:
        comando = escuchar_comando_continuo()
        if not comando:
            continue
        comando = comando.lower().strip()
        if not comando.startswith(nombre_clave):
            continue
        comando = comando[len(nombre_clave):].strip()
        if not comando:
            continue
        if 'salir' in comando:
            msg = "Asistente finalizado."
            print(msg); hablar(msg); break
        elif 'analizar pantalla' in comando:
            analizar_pantalla()
        elif comando.startswith('pregunta '):
            print(responder_pregunta(comando[len('pregunta '):]))
        else:
            print("Comando no reconocido en modo legacy.")

if __name__ == "__main__":
    iniciar_asistente()
