import sys
import os
import threading
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDialog, QLineEdit, QComboBox, QGraphicsDropShadowEffect, QStackedLayout
from PyQt5.QtGui import QPainter, QBrush, QPen, QColor, QFont, QLinearGradient
from PyQt5.QtCore import Qt, QTimer, QRectF, pyqtSignal, QPropertyAnimation, QEasingCurve
from src.particulas_widget import FondoParticulas

# Importar funciones del asistente
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
from voz import escuchar_comando, hablar
import json
from datetime import datetime, timedelta

class MicrofonoWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.animacion = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animacion)
        self.timer.start(40)
        self.setMinimumSize(300, 400)

    def update_animacion(self):
        self.animacion = (self.animacion + 2) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect()
        # Fondo gradiente animado
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0, QColor(20, 30, 60))
        grad.setColorAt(0.5, QColor(40, 0, 80))
        grad.setColorAt(1, QColor(0, 255, 255, 80))
        painter.fillRect(rect, grad)
        # Círculo animado neón
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(0,255,255), 7)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        r = QRectF(rect.center().x()-80, rect.center().y()-80, 160, 160)
        painter.drawArc(r, self.animacion*16, 270*16)
        # Micrófono (SVG-like, neón)
        painter.setPen(QPen(QColor(255,255,255), 4))
        painter.setBrush(Qt.NoBrush)
        cx, cy = rect.center().x(), rect.center().y()
        painter.drawEllipse(cx-30, cy-40, 60, 80)
        painter.setPen(QPen(QColor(0,255,255), 4))
        painter.drawLine(cx, cy+40, cx, cy+70)
        painter.drawArc(cx-25, cy+60, 50, 20, 0, 180*16)


class AsistenteMain(QMainWindow):
    def sincronizar_con_drive(self, modo='ambos'):
        """
        Sincroniza notas con Google Drive.
        modo: 'subir', 'descargar' o 'ambos'
        """
        import pickle, os, io
        from googleapiclient.discovery import build
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
        SCOPES = ['https://www.googleapis.com/auth/drive.file']
        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        service = build('drive', 'v3', credentials=creds)
        base = self.ruta_notas()
        # SUBIR
        if modo in ('subir', 'ambos'):
            subidos = 0
            for root, dirs, files in os.walk(base):
                for file in files:
                    if file.endswith('.txt'):
                        file_path = os.path.join(root, file)
                        # Evitar duplicados: buscar si ya existe en Drive
                        query = f"name='{file}' and mimeType='text/plain'"
                        res = service.files().list(q=query, fields="files(id)").execute()
                        if res.get('files'):
                            continue  # Ya existe
                        metadata = {'name': file, 'parents': []}
                        try:
                            media = MediaFileUpload(file_path, mimetype='text/plain')
                            service.files().create(body=metadata, media_body=media, fields='id').execute()
                            subidos += 1
                        except Exception as e:
                            print(f"Error subiendo {file}: {e}")
            self.mostrar_mensaje_chat(f"Notas subidas a Drive: {subidos}", tipo='sistema')
        # DESCARGAR
        if modo in ('descargar', 'ambos'):
            descargados = 0
            results = service.files().list(q="mimeType='text/plain'", fields="files(id, name)").execute()
            items = results.get('files', [])
            for item in items:
                file_id = item['id']
                file_name = item['name']
                local_path = os.path.join(base, file_name)
                if os.path.exists(local_path):
                    continue  # Ya existe local
                try:
                    request = service.files().get_media(fileId=file_id)
                    fh = io.FileIO(local_path, 'wb')
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                    descargados += 1
                except Exception as e:
                    print(f"Error descargando {file_name}: {e}")
            self.mostrar_mensaje_chat(f"Notas descargadas de Drive: {descargados}", tipo='sistema')
    def ruta_notas(self, carpeta=None):
        base = os.path.join(os.path.dirname(__file__), 'notas')
        if carpeta:
            return os.path.join(base, carpeta)
        return base

    def guardar_nota(self, titulo, contenido, carpeta=None):
        ruta = self.ruta_notas(carpeta)
        os.makedirs(ruta, exist_ok=True)
        with open(os.path.join(ruta, f"{titulo}.txt"), "w", encoding="utf-8") as f:
            f.write(contenido)

    def leer_nota(self, titulo, carpeta=None):
        ruta = self.ruta_notas(carpeta)
        try:
            with open(os.path.join(ruta, f"{titulo}.txt"), "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None

    def eliminar_nota(self, titulo, carpeta=None):
        ruta = self.ruta_notas(carpeta)
        try:
            os.remove(os.path.join(ruta, f"{titulo}.txt"))
            return True
        except Exception:
            return False

    def buscar_notas(self, palabra, carpeta=None):
        ruta = self.ruta_notas(carpeta)
        resultados = []
        if not os.path.exists(ruta):
            return resultados
        for root, dirs, files in os.walk(ruta):
            for file in files:
                if file.endswith('.txt'):
                    path = os.path.join(root, file)
                    with open(path, 'r', encoding='utf-8') as f:
                        contenido = f.read()
                        if palabra.lower() in contenido.lower() or palabra.lower() in file.lower():
                            resultados.append((file[:-4], os.path.relpath(root, ruta)))
        return resultados
    def iniciar_escucha_hey_asistente(self):
        import speech_recognition as sr
        import threading
        self.escuchando = True
        def escuchar():
            r = sr.Recognizer()
            mic = sr.Microphone()
            with mic as source:
                r.adjust_for_ambient_noise(source)
            while self.escuchando:
                with mic as source:
                    try:
                        audio = r.listen(source, timeout=1, phrase_time_limit=4)
                        texto = r.recognize_google(audio, language='es-ES')
                        if 'hey asistente' in texto.lower():
                            self.mostrar_mensaje_chat('Escuchando... (activado por voz)', tipo='sistema')
                            self.activar_reconocimiento_voz()
                    except sr.WaitTimeoutError:
                        continue
                    except Exception:
                        continue
        threading.Thread(target=escuchar, daemon=True).start()

    def mostrar_mensaje_chat(self, texto, tipo='usuario'):
        # Busca el chat_layout y añade un QLabel con el texto
        for child in self.findChildren(QWidget):
            if hasattr(child, 'layout') and child.layout() and child.layout().count() > 0:
                lay = child.layout()
                if lay.count() > 0 and isinstance(lay.itemAt(0).widget(), QLabel):
                    # Es el chat_layout
                    msg = QLabel(texto)
                    if tipo == 'usuario':
                        msg.setStyleSheet("background:rgba(0,0,0,0.18);border-radius:12px;padding:10px 16px;font-size:16px;color:#fff;")
                    else:
                        msg.setStyleSheet("background:rgba(0,255,255,0.10);border-radius:12px;padding:10px 16px;font-size:16px;color:#0ff;")
                    lay.addWidget(msg)
                    break

    def activar_reconocimiento_voz(self):
        import speech_recognition as sr
        import threading
        def reconocer():
            r = sr.Recognizer()
            mic = sr.Microphone()
            with mic as source:
                self.mostrar_mensaje_chat('Habla ahora...', tipo='sistema')
                audio = r.listen(source, timeout=5, phrase_time_limit=7)
            try:
                texto = r.recognize_google(audio, language='es-ES')
                self.mostrar_mensaje_chat(texto, tipo='usuario')
                self.responder_asistente(texto)
            except Exception:
                self.mostrar_mensaje_chat('No se entendió, intenta de nuevo.', tipo='sistema')
        threading.Thread(target=reconocer, daemon=True).start()

    def responder_asistente(self, texto):
        # Detección de intención básica
        texto_l = texto.lower()
        respuesta = ""
        accion_realizada = False
        # Saludo
        if any(s in texto_l for s in ["hola", "buenos días", "buenas tardes", "buenas noches"]):
            respuesta = "¡Hola! ¿En qué puedo ayudarte?"
        # Sincronizar notas con Google Drive (subir y descargar)
        elif ("sincroniza" in texto_l or "sube" in texto_l) and "drive" in texto_l:
            self.mostrar_mensaje_chat("Subiendo notas a Google Drive...", tipo='sistema')
            self.sincronizar_con_drive(modo='subir')
            respuesta = "Notas subidas a Drive."
            accion_realizada = True
        elif "descarga" in texto_l and "drive" in texto_l:
            self.mostrar_mensaje_chat("Descargando notas de Google Drive...", tipo='sistema')
            self.sincronizar_con_drive(modo='descargar')
            respuesta = "Notas descargadas de Drive."
            accion_realizada = True
        # Abrir aplicación o navegador
        elif "abrir" in texto_l:
            import subprocess
            if "calculadora" in texto_l:
                respuesta = "Abriendo la calculadora."
                accion_realizada = True
                try:
                    subprocess.Popen('calc.exe')
                except Exception:
                    respuesta = "No pude abrir la calculadora."
            elif "bloc de notas" in texto_l or "notas" in texto_l:
                respuesta = "Abriendo el bloc de notas."
                accion_realizada = True
                try:
                    subprocess.Popen('notepad.exe')
                except Exception:
                    respuesta = "No pude abrir el bloc de notas."
            elif "navegador" in texto_l or "chrome" in texto_l or "internet" in texto_l:
                respuesta = "Abriendo el navegador."
                accion_realizada = True
                try:
                    subprocess.Popen('start chrome', shell=True)
                except Exception:
                    respuesta = "No pude abrir el navegador."
            else:
                respuesta = "¿Qué aplicación deseas abrir?"
        # Decir la hora
        elif "hora" in texto_l:
            from datetime import datetime
            hora = datetime.now().strftime('%H:%M')
            respuesta = f"Son las {hora}."
        # Buscar en Google
        elif "busca" in texto_l or "buscar" in texto_l:
            import webbrowser
            import re
            patron = r"busca(r)? (en google )?(.*)"
            m = re.search(patron, texto_l)
            if m and m.group(3):
                query = m.group(3).strip()
                url = f"https://www.google.com/search?q={query.replace(' ','+')}"
                webbrowser.open(url)
                respuesta = f"Buscando '{query}' en Google."
            else:
                respuesta = "¿Qué quieres que busque en Google?"
        # Reproducir música
        elif "reproduce" in texto_l or "pon música" in texto_l:
            import webbrowser
            respuesta = "Reproduciendo música en YouTube."
            webbrowser.open("https://www.youtube.com/results?search_query=música")
        # Apagar o reiniciar PC
        elif "apaga" in texto_l or "apagar" in texto_l:
            respuesta = "Apagando el equipo."
            import os
            os.system("shutdown /s /t 1")
        elif "reinicia" in texto_l or "reiniciar" in texto_l:
            respuesta = "Reiniciando el equipo."
            import os
            os.system("shutdown /r /t 1")
        # Quién eres
        elif "quién eres" in texto_l or "quien eres" in texto_l or "tu nombre" in texto_l:
            respuesta = "Soy tu asistente inteligente, siempre listo para ayudarte."
        # Crear nota en carpeta
        elif "crear nota" in texto_l:
            import re
            m = re.search(r"crear nota (.+?)( en (.+))?$", texto_l)
            if m:
                titulo = m.group(1).strip()
                carpeta = m.group(3).strip() if m.group(3) else None
                self.guardar_nota(titulo, "", carpeta)
                respuesta = f"Nota '{titulo}' creada{' en '+carpeta if carpeta else ''}. ¿Qué contenido quieres guardar?"
            else:
                respuesta = "¿Cómo se llama la nota?"
        # Editar nota
        elif "editar nota" in texto_l:
            import re
            m = re.search(r"editar nota (.+?)( en (.+))?$", texto_l)
            if m:
                titulo = m.group(1).strip()
                carpeta = m.group(3).strip() if m.group(3) else None
                contenido = self.leer_nota(titulo, carpeta)
                if contenido is not None:
                    respuesta = f"¿Qué nuevo contenido quieres para la nota '{titulo}'?"
                    # Aquí podrías guardar el nuevo contenido en la siguiente interacción
                else:
                    respuesta = f"No encontré la nota '{titulo}'."
            else:
                respuesta = "¿Qué nota quieres editar?"
        # Eliminar nota
        elif "eliminar nota" in texto_l:
            import re
            m = re.search(r"eliminar nota (.+?)( en (.+))?$", texto_l)
            if m:
                titulo = m.group(1).strip()
                carpeta = m.group(3).strip() if m.group(3) else None
                ok = self.eliminar_nota(titulo, carpeta)
                if ok:
                    respuesta = f"Nota '{titulo}' eliminada."
                else:
                    respuesta = f"No encontré la nota '{titulo}'."
            else:
                respuesta = "¿Qué nota quieres eliminar?"
        # Buscar nota
        elif "buscar nota" in texto_l:
            import re
            m = re.search(r"buscar nota (.+?)( en (.+))?$", texto_l)
            if m:
                palabra = m.group(1).strip()
                carpeta = m.group(3).strip() if m.group(3) else None
                resultados = self.buscar_notas(palabra, carpeta)
                if resultados:
                    respuesta = "Notas encontradas: " + ", ".join([f"'{t}' (carpeta: {c})" for t,c in resultados])
                else:
                    respuesta = "No se encontraron notas con ese término."
            else:
                respuesta = "¿Qué palabra quieres buscar en las notas?"
        # Crear carpeta
        elif "crear carpeta" in texto_l:
            import re
            m = re.search(r"crear carpeta (.+)$", texto_l)
            if m:
                carpeta = m.group(1).strip()
                os.makedirs(self.ruta_notas(carpeta), exist_ok=True)
                respuesta = f"Carpeta '{carpeta}' creada."
            else:
                respuesta = "¿Cómo se llama la carpeta?"
        # Fallback
        else:
            respuesta = 'Comando recibido: ' + texto
        self.mostrar_mensaje_chat(respuesta, tipo='sistema')
        try:
            from gtts import gTTS
            import playsound
            tts = gTTS(respuesta, lang='es')
            tts.save('respuesta.mp3')
            playsound.playsound('respuesta.mp3', True)
            os.remove('respuesta.mp3')
        except Exception:
            pass
    def accion_microfono(self):
        self.activar_reconocimiento_voz()
    def showEvent(self, event):
        super().showEvent(event)
        # Iniciar escucha continua solo una vez
        if not hasattr(self, '_escucha_iniciada'):
            self.iniciar_escucha_hey_asistente()
            self._escucha_iniciada = True
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Asistente Inteligente - Voz")
        self.setGeometry(200, 100, 420, 740)
        self.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #111, stop:1 #444);")
        self.init_ui()

    def init_ui(self):
        # --- Estructura principal ---
        central = QWidget()
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(24)

        # --- Panel lateral ---
        panel_lateral = QVBoxLayout()
        panel_lateral.setSpacing(32)
        panel_lateral.setAlignment(Qt.AlignTop)
        # Logo y título
        logo = QLabel()
        logo.setFixedSize(48,48)
        logo.setStyleSheet("border-radius:24px;border:3px solid #0ff;background:rgba(0,255,255,0.08);")
        panel_lateral.addWidget(logo, alignment=Qt.AlignHCenter)
        titulo = QLabel("Asistente de PC")
        titulo.setStyleSheet("color:#0ff;font-size:22px;font-family:'Orbitron', 'Montserrat', Arial;font-weight:bold;")
        panel_lateral.addWidget(titulo, alignment=Qt.AlignHCenter)
        # Botones menú
        def menu_btn(text, icon=None):
            btn = QPushButton(text)
            btn.setFixedHeight(48)
            btn.setStyleSheet("color:#0ff;background:transparent;border:none;font-size:17px;text-align:left;padding-left:16px;border-radius:12px;")
            return btn
        panel_lateral.addWidget(menu_btn("Chat"))
        panel_lateral.addWidget(menu_btn("Aplicaciones"))
        panel_lateral.addWidget(menu_btn("Configuración"))
        panel_lateral.addStretch(1)

        # --- Panel central (chat) ---
        panel_chat = QVBoxLayout()
        panel_chat.setSpacing(18)
        # Chat bubbles
        chat_box = QWidget()
        chat_box.setStyleSheet("background:rgba(10,20,40,0.7);border:2px solid #0ff;border-radius:18px;")
        chat_box.setMinimumWidth(340)
        chat_layout = QVBoxLayout(chat_box)
        chat_layout.setContentsMargins(18,18,18,18)
        chat_layout.setSpacing(12)
        # Mensajes ejemplo
        msg1 = QLabel("<span style='color:#fff;'>¿En qué puedo ayudarte hoy?</span><span style='float:right;color:#0ff;font-size:12px;'>10:00</span>")
        msg1.setStyleSheet("background:rgba(0,0,0,0.18);border-radius:12px;padding:10px 16px;font-size:16px;")
        chat_layout.addWidget(msg1)
        msg2 = QLabel("<span style='color:#fff;'>Necesito ayuda con mi presentación</span><span style='float:right;color:#0ff;font-size:12px;'>10:01</span>")
        msg2.setStyleSheet("background:rgba(0,0,0,0.18);border-radius:12px;padding:10px 16px;font-size:16px;")
        chat_layout.addWidget(msg2)
        panel_chat.addWidget(chat_box)
        # Botón micrófono grande
        self.btn_micro = QPushButton()
        self.btn_micro.setFixedSize(80,80)
        self.btn_micro.setStyleSheet("border-radius:40px;background:rgba(0,255,255,0.10);border:3px solid #0ff;")
        self.btn_micro.setIconSize(self.btn_micro.size())
        self.btn_micro.setText("")
        self.btn_micro.clicked.connect(self.accion_microfono)
        panel_chat.addWidget(self.btn_micro, alignment=Qt.AlignHCenter)
        # Texto "Habla ahora"
        speak_lbl = QLabel("Habla ahora")
        speak_lbl.setStyleSheet("color:#0ff;font-size:18px;font-family:'Orbitron', 'Montserrat', Arial;")
        panel_chat.addWidget(speak_lbl, alignment=Qt.AlignHCenter)
        panel_chat.addStretch(1)

        # --- Panel de notas ---
        panel_notas = QVBoxLayout()
        panel_notas.setSpacing(18)
        notes_box = QWidget()
        notes_box.setStyleSheet("background:rgba(30,0,60,0.7);border:2px solid #a0f;border-radius:18px;")
        notes_box.setMinimumWidth(220)
        notes_layout = QVBoxLayout(notes_box)
        notes_layout.setContentsMargins(14,14,14,14)
        notes_lbl = QLabel("Notas")
        notes_lbl.setStyleSheet("color:#a0f;font-size:18px;font-family:'Orbitron', 'Montserrat', Arial;font-weight:bold;")
        notes_layout.addWidget(notes_lbl)
        self.notes_edit = QLineEdit()
        self.notes_edit.setStyleSheet("background:rgba(0,0,0,0.18);color:#fff;border-radius:10px;padding:10px 8px;font-size:15px;")
        self.notes_edit.setText("Preparar diapositivas para la presentación")
        notes_layout.addWidget(self.notes_edit)
        notes_box.setLayout(notes_layout)
        panel_notas.addWidget(notes_box)
        # Botón guardar nota
        btn_save = QPushButton("Guardar nota")
        btn_save.setStyleSheet("color:#a0f;font-size:17px;font-family:'Orbitron', 'Montserrat', Arial;border-radius:12px;padding:10px 0px;border:2px solid #a0f;background:transparent;")
        panel_notas.addWidget(btn_save)
        panel_notas.addStretch(1)

        # --- Añadir paneles al layout principal ---
        main_layout.addLayout(panel_lateral, 1)
        main_layout.addLayout(panel_chat, 2)
        main_layout.addLayout(panel_notas, 1)
        self.setCentralWidget(central)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = AsistenteMain()
    ventana.show()
    sys.exit(app.exec_())
