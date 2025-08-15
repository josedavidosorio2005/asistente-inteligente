# ia.py
# Motor de IA para acciones proactivas
import openai
import os

def responder_pregunta(pregunta):
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("[ERROR] Debes definir la variable de entorno OPENAI_API_KEY con tu clave de OpenAI.")
        return
    openai.api_key = api_key
    try:
        respuesta = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "Eres un asistente útil y proactivo para PC."},
                      {"role": "user", "content": pregunta}]
        )
        texto = respuesta.choices[0].message.content.strip()
        print(f"IA: {texto}")
        return texto
    except Exception as e:
        print(f"[ERROR] No se pudo obtener respuesta de la IA: {e}")
