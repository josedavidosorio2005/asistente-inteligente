# main.py
# Orquestador principal del asistente inteligente


from vision import analizar_pantalla
from voz import escuchar_comando, escuchar_comando_continuo, hablar
from calendario import crear_evento, editar_evento, eliminar_evento, consultar_eventos
from ia import responder_pregunta
from interfaz import mostrar_panel


def iniciar_asistente():
    print("Bienvenido al asistente inteligente.")
    print("Puedes decir el nombre de activación por voz o escribirlo. Si no dices nada, será 'asistente'.")
    print("Por favor, di el nombre de activación que prefieres...")
    nombre_clave = escuchar_comando()
    if not nombre_clave:
        nombre_clave = input("O escríbelo aquí (Enter para 'asistente'): ").strip().lower()
    if not nombre_clave:
        nombre_clave = "asistente"
    nombre_clave = nombre_clave.lower().strip()
    print(f"El nombre de activación es: '{nombre_clave}'. Di '{nombre_clave}' seguido de tu comando.")
    print("Comandos disponibles: analizar pantalla, crear evento, editar evento, eliminar evento, panel, pregunta <texto>, qué tengo hoy, qué tengo esta semana, salir")
    while True:
        comando = escuchar_comando_continuo()
        if not comando:
            continue
        comando = comando.lower().strip()
        if not comando.startswith(nombre_clave):
            continue  # Ignora todo lo que no empiece con el nombre clave
        comando = comando[len(nombre_clave):].strip()
        if not comando:
            continue
        respuesta = None
        if 'salir' in comando:
            respuesta = "Asistente finalizado."
            print(respuesta)
            hablar(respuesta)
            break
        elif 'analizar pantalla' in comando:
            respuesta = analizar_pantalla()
        elif 'crear evento' in comando:
            respuesta = crear_evento()
        elif 'editar evento' in comando:
            respuesta = editar_evento()
        elif 'eliminar evento' in comando:
            respuesta = eliminar_evento()
        elif 'panel' in comando:
            respuesta = mostrar_panel()
        elif comando.startswith('pregunta '):
            pregunta = comando[len('pregunta '):]
            respuesta = responder_pregunta(pregunta)
        elif 'qué tengo hoy' in comando:
            respuesta = consultar_eventos('hoy')
        elif 'qué tengo esta semana' in comando or 'semana' in comando:
            respuesta = consultar_eventos('semana')
        else:
            respuesta = "No entendí el comando por voz. Intenta de nuevo."
            print(respuesta)
            hablar(respuesta)
            continue
        if respuesta:
            print(respuesta)
            hablar(respuesta)
        else:
            mensaje = "Acción realizada."
            print(mensaje)
            hablar(mensaje)

if __name__ == "__main__":
    iniciar_asistente()
