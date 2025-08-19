# ia.py
# Motor de IA para acciones proactivas
import os
from transformers import pipeline

def responder_pregunta(pregunta):
    try:
        # Usa un modelo más grande y coherente: gpt2-xl
        generator = pipeline('text-generation', model='gpt2-xl')
        prompt = f"Usuario: {pregunta}\nAsistente:"
        resultado = generator(prompt, max_length=150, num_return_sequences=1)
        texto = resultado[0]['generated_text'].split('Asistente:')[-1].strip()
        print(f"IA (GPT2-xl local): {texto}")
        return texto
    except Exception as e:
        print(f"[ERROR] No se pudo obtener respuesta de la IA local: {e}")
