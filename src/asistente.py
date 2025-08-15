



import mss
import numpy as np
import cv2
import sys
import requests
import tempfile
import pyttsx3
import speech_recognition as sr
import threading
import tkinter as tk
import os
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from gtts import gTTS
from playsound import playsound

# Captura la pantalla completa
def capturar_pantalla():
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        img = np.array(screenshot)
        # Convertir BGRA a BGR
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img

# Extrae texto usando la API de OCR.space
# Extrae texto usando la API de OCR.space
# Extrae texto usando la API de OCR.space
def extraer_texto(img):
    # Guardar imagen temporalmente
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        cv2.imwrite(tmp.name, img)
        tmp_path = tmp.name
    with open(tmp_path, 'rb') as f:
        r = requests.post(
            'https://api.ocr.space/parse/image',
            files={'filename': f},
            data={'language': 'spa', 'isOverlayRequired': False},
            headers={'apikey': 'helloworld'}  # clave pública gratuita para pruebas
        )
    try:
        result = r.json()
        if result.get('IsErroredOnProcessing'):
            return '[ERROR] ' + result.get('ErrorMessage', ['Error desconocido'])[0]
        parsed = result['ParsedResults'][0]['ParsedText']
        return parsed
    except Exception as e:
        return f'[ERROR] No se pudo procesar la imagen: {e}'

# Filtra solo información relevante del texto
def filtrar_texto(texto):
    lineas = texto.split('\n')
    relevantes = []
    for linea in lineas:
        l = linea.strip()
        # Ignora líneas vacías, menús comunes y palabras sueltas
        if not l or len(l) < 4:
            continue
        if l.lower() in ["archivo", "editar", "ver", "ir", "ejecutar", "selección", "ayuda", "main", "src"]:
            continue
        relevantes.append(l)
    return '\n'.join(relevantes)

# Guarda el resumen en una base de datos simple (JSON)
def guardar_resumen(nombre_imagen, resumen):
    db_path = os.path.join(os.path.dirname(__file__), '..', 'resumenes', 'resumenes.json')
    db_path = os.path.abspath(db_path)
    if os.path.exists(db_path):
        with open(db_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {}
    data[nombre_imagen] = resumen
    with open(db_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Consulta la base de datos de resúmenes por palabra clave
def consultar_resumenes(palabra):
    db_path = os.path.join(os.path.dirname(__file__), '..', 'resumenes', 'resumenes.json')
    db_path = os.path.abspath(db_path)
    if not os.path.exists(db_path):
        print("No hay resúmenes guardados.")
        return
    with open(db_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    encontrados = []
    for nombre, resumen in data.items():
        if palabra.lower() in resumen.lower():
            encontrados.append((nombre, resumen))
    if encontrados:
        print(f"\nResúmenes que contienen '{palabra}':")
        for nombre, resumen in encontrados:
            print(f"\nImagen: {nombre}\nResumen:\n{resumen}")
    else:
        print(f"No se encontró la palabra '{palabra}' en ningún resumen.")

# Dicta el texto detectado por voz
def dictar_texto(texto, voz_natural=True):
    if voz_natural:
        try:
            tts = gTTS(text=texto, lang='es', slow=False)
            tmp_path = os.path.join(tempfile.gettempdir(), 'voz_asistente.mp3')
            tts.save(tmp_path)
            playsound(tmp_path)
            os.remove(tmp_path)
            return
        except Exception as e:
            print(f"[ERROR] Voz natural falló, usando voz estándar. {e}")
    # Fallback a voz estándar
    engine = pyttsx3.init()
    engine.setProperty('rate', 160)
    engine.say(texto)
    engine.runAndWait()

# Escucha por voz la orden de "detener"
def escuchar_orden():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Di 'detener' para finalizar el asistente...")
        audio = r.listen(source, phrase_time_limit=4)
    try:
        comando = r.recognize_google(audio, language='es-ES').lower()
        print(f"Comando detectado: {comando}")
        if "detener" in comando or "acabar" in comando or "parar" in comando:
            return True
    except Exception:
        pass
    return False


# Ventana flotante con recuadro rojo
class OverlayRedBox(threading.Thread):
    def __init__(self):
        super().__init__()
        self.root = None
        self._stop = threading.Event()

    def run(self):
        self.root = tk.Tk()
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.2)
        self.root.configure(bg='black')
        canvas = tk.Canvas(self.root, bg='black', highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        width = self.root.winfo_screenwidth()
        height = self.root.winfo_screenheight()
        canvas.create_rectangle(5, 5, width-5, height-5, outline='red', width=8)
        self.root.protocol("WM_DELETE_WINDOW", self.stop)
        while not self._stop.is_set():
            self.root.update()
        self.root.destroy()

    def stop(self):
        self._stop.set()


# Handler para procesar nuevas imágenes en la carpeta
class PantallazoHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            print(f"\nNuevo pantallazo detectado: {event.src_path}")
            try:
                img = cv2.imread(event.src_path)
                if img is None:
                    print("No se pudo leer la imagen.")
                    return
                texto = extraer_texto(img)
                resumen = filtrar_texto(texto)
                if not resumen.strip():
                    resumen = "No se detectó información relevante en la imagen."
                print("Resumen del pantallazo:")
                print(resumen)
                dictar_texto(resumen)
                guardar_resumen(os.path.basename(event.src_path), resumen)
            except Exception as e:
                print(f"[ERROR] Procesando imagen: {e}")

def main():
    carpeta = os.path.join(os.path.dirname(__file__), '..', 'pantallazos')
    carpeta = os.path.abspath(carpeta)
    print(f"Monitoreando la carpeta: {carpeta}\nSube o guarda aquí tus pantallazos para procesarlos automáticamente.")
    # Procesar imágenes ya existentes al iniciar
    for archivo in os.listdir(carpeta):
        if archivo.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            ruta = os.path.join(carpeta, archivo)
            print(f"\nProcesando imagen existente: {ruta}")
            try:
                img = cv2.imread(ruta)
                if img is None:
                    print("No se pudo leer la imagen.")
                    continue
                texto = extraer_texto(img)
                resumen = filtrar_texto(texto)
                if not resumen.strip():
                    resumen = "No se detectó información relevante en la imagen."
                print("Resumen del pantallazo:")
                print(resumen)
                dictar_texto(resumen)
                guardar_resumen(os.path.basename(ruta), resumen)
            except Exception as e:
                print(f"[ERROR] Procesando imagen: {e}")
    event_handler = PantallazoHandler()
    observer = Observer()
    observer.schedule(event_handler, carpeta, recursive=False)
    observer.start()
    try:
        print("Presiona Ctrl+C para detener el asistente.")
        print("Opciones disponibles:")
        print("  [1] Buscar en resúmenes por palabra clave")
        print("  [2] Listar todos los resúmenes")
        print("  [3] Salir")
        while True:
            comando = input("\nSelecciona una opción (1, 2, 3) o presiona Enter para continuar monitoreando imágenes: ").strip()
            if comando == '1':
                palabra = input("Ingresa la palabra clave a buscar: ").strip()
                if palabra:
                    consultar_resumenes(palabra)
            elif comando == '2':
                consultar_resumenes("")
            elif comando == '3':
                print("Saliendo del asistente...")
                break
    except KeyboardInterrupt:
        print("\nAsistente detenido por el usuario.")
    finally:
        observer.stop()
        observer.join()

if __name__ == "__main__":
    main()
