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
        usar_ia = False
        if 'salir' in comando:
            respuesta = "Asistente finalizado."
            print(respuesta)
            hablar(respuesta)
            break
        elif 'analizar pantalla' in comando:
            respuesta = analizar_pantalla()
            if 'ayuda' in comando or 'explica' in comando:
                usar_ia = True
        elif 'crear evento' in comando:
            respuesta = crear_evento()
            if 'ayuda' in comando or 'explica' in comando:
                usar_ia = True
        elif 'editar evento' in comando:
            respuesta = editar_evento()
            if 'ayuda' in comando or 'explica' in comando:
                usar_ia = True
        elif 'eliminar evento' in comando:
            respuesta = eliminar_evento()
            if 'ayuda' in comando or 'explica' in comando:
                usar_ia = True
        elif 'panel' in comando:
            respuesta = mostrar_panel()
            if 'ayuda' in comando or 'explica' in comando:
                usar_ia = True
        elif comando.startswith('pregunta '):
            pregunta = comando[len('pregunta '):]
            respuesta = responder_pregunta(pregunta)
        elif 'qué tengo hoy' in comando:
            respuesta = consultar_eventos('hoy')
            if 'ayuda' in comando or 'explica' in comando:
                usar_ia = True
        elif 'qué tengo esta semana' in comando or 'semana' in comando:
            respuesta = consultar_eventos('semana')
            if 'ayuda' in comando or 'explica' in comando:
                usar_ia = True
        else:
            usar_ia = True
            respuesta = "No entendí el comando por voz. ¿Quieres que la IA te ayude?"
        # Si la respuesta es vacía o el usuario pidió ayuda, consulta a la IA
        if usar_ia or not respuesta:
            from ia import responder_pregunta as ia_responder
            pregunta_ia = f"Ayuda o información sobre el comando: '{comando}' y la respuesta previa: '{respuesta if respuesta else ''}'"
            respuesta_ia = ia_responder(pregunta_ia)
            if respuesta_ia:
                print(respuesta_ia)
                hablar(respuesta_ia)
            else:
                mensaje = respuesta if respuesta else "Acción realizada."
                print(mensaje)
                hablar(mensaje)
        else:
            print(respuesta)
            hablar(respuesta)

if __name__ == "__main__":
    iniciar_asistente()
