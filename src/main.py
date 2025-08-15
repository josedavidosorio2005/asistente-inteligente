# main.py
# Orquestador principal del asistente inteligente


from vision import analizar_pantalla
from voz import escuchar_comando, escuchar_comando_continuo
from calendario import crear_evento, editar_evento, eliminar_evento, consultar_eventos
from ia import responder_pregunta
from interfaz import mostrar_panel


def iniciar_asistente():
    print("Asistente inteligente iniciado. Puedes hablar en cualquier momento.")
    print("Comandos por voz: analizar pantalla, crear evento, editar evento, eliminar evento, panel, pregunta <texto>, qué tengo hoy, qué tengo esta semana, salir")
    while True:
        comando = escuchar_comando_continuo()
        if not comando:
            continue
        comando = comando.lower()
        if 'salir' in comando:
            print("Asistente finalizado.")
            break
        elif 'analizar pantalla' in comando:
            analizar_pantalla()
        elif 'crear evento' in comando:
            crear_evento()
        elif 'editar evento' in comando:
            editar_evento()
        elif 'eliminar evento' in comando:
            eliminar_evento()
        elif 'panel' in comando:
            mostrar_panel()
        elif comando.startswith('pregunta '):
            pregunta = comando[len('pregunta '):]
            responder_pregunta(pregunta)
        elif 'qué tengo hoy' in comando:
            consultar_eventos('hoy')
        elif 'qué tengo esta semana' in comando or 'semana' in comando:
            consultar_eventos('semana')
        else:
            print("No entendí el comando por voz. Intenta de nuevo.")

if __name__ == "__main__":
    iniciar_asistente()
