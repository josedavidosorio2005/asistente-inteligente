"""
Aplicación PyQt del Asistente Inteligente.

Responsabilidades principales:
- UI de chat y notas.
- Activación por voz (hotword simple "hey asistente").
- Acciones básicas (abrir apps, buscar, hora, CRUD notas, sync Drive opcional).

Buenas prácticas aplicadas:
- Señales Qt para actualizar UI desde hilos.
- Docstrings y anotaciones para mayor claridad.
- Limpieza de estilos e importaciones.
"""

import sys
import os
import threading
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDialog, QLineEdit, QComboBox, QListWidget, QTextEdit, QMessageBox, QInputDialog, QScrollArea, QShortcut
from PyQt5.QtGui import QPainter, QPen, QColor, QLinearGradient
from PyQt5.QtCore import Qt, QTimer, QRectF, pyqtSignal

# Asegurar que la carpeta 'src' esté en el path para widgets auxiliares
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(PROJECT_DIR, 'src')
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

# Importar funciones de voz desde el nuevo core; fallback a módulo antiguo si no existe
try:
    from src.assistant_app.core.voice import listen_once as escuchar_comando, speak as hablar
except Exception:
    from voz import escuchar_comando, hablar
import json
from datetime import datetime, timedelta

class MicrofonoWidget(QWidget):
    """Widget decorativo que dibuja un micrófono con efecto neón animado."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.animacion = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animacion)
        self.timer.start(40)
        self.setMinimumSize(300, 400)

    def update_animacion(self) -> None:
        self.animacion = (self.animacion + 2) % 360
        self.update()

    def paintEvent(self, event):  # type: ignore[override]
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
    """Ventana principal del asistente.

    Emite mensajes al chat mediante `chat_signal(texto, tipo)` donde tipo ∈ {'usuario','sistema'}.
    """

    chat_signal = pyqtSignal(str, str)

    def _aplicar_color_titulo_windows(self, widget=None, rgb: tuple[int,int,int] = (102, 221, 255)) -> None:
        """Intenta colorear la barra de título en Windows 11 (DWMWA_CAPTION_COLOR).
        No hace nada en otros sistemas o si la API no está disponible.
        """
        if sys.platform != 'win32':
            return
        try:
            import ctypes
            from ctypes import wintypes
            DWMWA_CAPTION_COLOR = 35
            r, g, b = rgb
            colorref = (b) | (g << 8) | (r << 16)  # COLORREF 0x00bbggrr
            hwnd = int((widget or self).winId())
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                wintypes.HWND(hwnd),
                ctypes.c_uint(DWMWA_CAPTION_COLOR),
                ctypes.byref(wintypes.DWORD(colorref)),
                ctypes.sizeof(wintypes.DWORD)
            )
        except Exception:
            pass

    def mostrar_mensaje_chat(self, texto: str, tipo: str) -> None:
        """Pinta un mensaje en el chat con estilo básico y hace autoscroll.

        tipo: 'usuario' o 'sistema'.
        """
        if not hasattr(self, 'chat_layout') or self.chat_layout is None:
            return
        msg = QLabel(texto)
        if tipo == 'usuario':
            msg.setStyleSheet(
                "background:rgba(0,255,255,0.10);border-radius:12px;padding:10px 16px;font-size:16px;color:#0ff;"
            )
        else:
            msg.setStyleSheet(
                "background:rgba(0,0,0,0.18);border-radius:12px;padding:10px 16px;font-size:16px;color:#fff;"
            )
        self.chat_layout.addWidget(msg)
        self.autoscroll_chat()

    def sincronizar_con_drive(self, modo: str = 'ambos') -> None:
        """
        Sincroniza notas con Google Drive.
        modo: 'subir', 'descargar' o 'ambos'.
        Esta implementación es un placeholder seguro: muestra un mensaje si no está configurado.
        """
        try:
            import io  # noqa: F401
            import pickle  # noqa: F401
            from googleapiclient.discovery import build  # type: ignore # noqa: F401
            from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore # noqa: F401
            self.chat_signal.emit("Sincronización de Drive requiere credenciales; configúralas para activar esta función.", 'sistema')
        except Exception:
            self.chat_signal.emit("Drive no está configurado en este equipo.", 'sistema')

    def autoscroll_chat(self) -> None:
        if hasattr(self, 'chat_scroll') and self.chat_scroll is not None:
            try:
                bar = self.chat_scroll.verticalScrollBar()
                bar.setValue(bar.maximum())
            except Exception:
                pass

    def activar_reconocimiento_voz(self) -> None:
        import speech_recognition as sr
        import threading
        # Estado visual del micrófono mientras escucha
        if not hasattr(self, '_btn_micro_style') and hasattr(self, 'btn_micro'):
            self._btn_micro_style = self.btn_micro.styleSheet()
        if hasattr(self, 'btn_micro'):
            self.btn_micro.setEnabled(False)
            self.btn_micro.setStyleSheet("border-radius:40px;background:rgba(255,0,0,0.15);border:3px solid #f55;")
        if hasattr(self, 'speak_lbl'):
            self.speak_lbl.setText("Escuchando…")
        def reconocer():
            r = sr.Recognizer()
            mic = sr.Microphone()
            with mic as source:
                self.chat_signal.emit('Habla ahora...', 'sistema')
                audio = r.listen(source, timeout=5, phrase_time_limit=7)
            try:
                texto = r.recognize_google(audio, language='es-ES')
                self.chat_signal.emit(texto, 'usuario')
                self.responder_asistente(texto)
            except Exception:
                self.chat_signal.emit('No se entendió, intenta de nuevo.', 'sistema')
            finally:
                # Restaurar UI del micrófono en el hilo principal
                QTimer.singleShot(0, lambda: (
                    hasattr(self, 'btn_micro') and self.btn_micro.setEnabled(True),
                    hasattr(self, 'btn_micro') and hasattr(self, '_btn_micro_style') and self.btn_micro.setStyleSheet(self._btn_micro_style),
                    hasattr(self, 'speak_lbl') and self.speak_lbl.setText("Habla ahora")
                ))
        threading.Thread(target=reconocer, daemon=True).start()

    def responder_asistente(self, texto: str) -> None:
        # Detección de intención básica
        texto_l = texto.lower()
        respuesta = ""
        accion_realizada = False
        # Saludo
        if any(s in texto_l for s in ["hola", "buenos días", "buenas tardes", "buenas noches"]):
            respuesta = "¡Hola! ¿En qué puedo ayudarte?"
        # Sincronizar notas con Google Drive (subir y descargar)
        elif ("sincroniza" in texto_l or "sube" in texto_l) and "drive" in texto_l:
            self.chat_signal.emit("Subiendo notas a Google Drive...", 'sistema')
            self.sincronizar_con_drive(modo='subir')
            respuesta = "Notas subidas a Drive."
            accion_realizada = True
        elif "descarga" in texto_l and "drive" in texto_l:
            self.chat_signal.emit("Descargando notas de Google Drive...", 'sistema')
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
        # Calendario: consultar hoy/semana
        elif (("qué tengo" in texto_l) or ("que tengo" in texto_l)) and ("hoy" in texto_l):
            try:
                from calendario import consultar_eventos
                eventos, msg = consultar_eventos('hoy')
                if eventos:
                    lista = ", ".join([f"{ev['evento']} ({ev['fecha']})" for ev in eventos])
                    respuesta = f"Hoy tienes: {lista}."
                else:
                    respuesta = msg
            except Exception as e:
                respuesta = f"No pude consultar el calendario: {e}"
        elif (("qué tengo" in texto_l) or ("que tengo" in texto_l)) and ("semana" in texto_l):
            try:
                from calendario import consultar_eventos
                eventos, msg = consultar_eventos('semana')
                if eventos:
                    lista = ", ".join([f"{ev['evento']} ({ev['fecha']})" for ev in eventos])
                    respuesta = f"Esta semana: {lista}."
                else:
                    respuesta = msg
            except Exception as e:
                respuesta = f"No pude consultar el calendario: {e}"
        # Calendario: crear evento
        elif "crear evento" in texto_l:
            import re
            m = re.search(r"crear evento (.+?) (?:el|para) (\d{4}-\d{2}-\d{2})", texto_l)
            if m:
                evento = m.group(1).strip()
                fecha = m.group(2)
                try:
                    from calendario import crear_evento
                    msg = crear_evento(evento, fecha)
                    respuesta = f"{msg} '{evento}' el {fecha}."
                except Exception as e:
                    respuesta = f"No pude crear el evento: {e}"
            else:
                respuesta = "Di: 'crear evento <nombre> el YYYY-MM-DD'."
        # Calendario: abrir calendario
        elif ("calendario" in texto_l) and ("abre" in texto_l or "abrir" in texto_l or "mostrar" in texto_l):
            try:
                self.abrir_calendario()
                respuesta = "Abriendo calendario."
                accion_realizada = True
            except Exception as e:
                respuesta = f"No se pudo abrir el calendario: {e}"
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
        self.chat_signal.emit(respuesta, 'sistema')
        try:
            hablar(respuesta)
        except Exception:
            pass

    def enviar_comando_escrito(self) -> None:
        """Lee el texto del input, lo envía al chat y procesa la respuesta."""
        try:
            texto = self.input_cmd.text().strip()
        except Exception:
            texto = ""
        if not texto:
            return
        self.chat_signal.emit(texto, 'usuario')
        self.responder_asistente(texto)
        try:
            self.input_cmd.clear()
        except Exception:
            pass
    def accion_microfono(self) -> None:
        self.activar_reconocimiento_voz()
    def showEvent(self, event):  # type: ignore[override]
        super().showEvent(event)
        # Iniciar escucha continua solo una vez
        if not hasattr(self, '_escucha_iniciada'):
            self.iniciar_escucha_hey_asistente()
            self._escucha_iniciada = True
    def closeEvent(self, event):  # type: ignore[override]
        try:
            self.escuchando = False
            if hasattr(self, '_escucha_thread') and self._escucha_thread and self._escucha_thread.is_alive():
                self._escucha_thread.join(timeout=1.0)
        except Exception:
            pass
        super().closeEvent(event)
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Asistente Inteligente - Voz")
        self.setGeometry(200, 100, 420, 740)
        self.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #111, stop:1 #444);")
        self.escuchando = False
        self.chat_layout = None
        self.chat_signal.connect(self.mostrar_mensaje_chat)
        self._escucha_iniciada = False
        self.init_ui()

    def init_ui(self) -> None:
        # --- Estructura principal ---
        central = QWidget()
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(24)

        # --- Panel lateral ---
        panel_lateral = QVBoxLayout()
        panel_lateral.setSpacing(32)
        panel_lateral.setAlignment(Qt.AlignTop)
        logo = QLabel()
        logo.setFixedSize(48, 48)
        logo.setStyleSheet("border-radius:24px;border:3px solid #0ff;background:rgba(0,255,255,0.08);")
        panel_lateral.addWidget(logo, alignment=Qt.AlignHCenter)
        titulo = QLabel("Asistente de PC")
        titulo.setStyleSheet("color:#0ff;font-size:22px;font-family:'Orbitron', 'Montserrat', Arial;font-weight:bold;")
        panel_lateral.addWidget(titulo, alignment=Qt.AlignHCenter)
        def menu_btn(text, icon=None):
            btn = QPushButton(text)
            btn.setFixedHeight(48)
            btn.setStyleSheet("color:#0ff;background:transparent;border:none;font-size:17px;text-align:left;padding-left:16px;border-radius:12px;")
            return btn
        panel_lateral.addWidget(menu_btn("Chat"))
        btn_calendario = menu_btn("Calendario")
        panel_lateral.addWidget(btn_calendario)
        panel_lateral.addWidget(menu_btn("Aplicaciones"))
        panel_lateral.addWidget(menu_btn("Configuración"))
        panel_lateral.addStretch(1)

        # --- Panel central (chat) ---
        panel_chat = QVBoxLayout()
        panel_chat.setSpacing(18)
        chat_box = QWidget()
        chat_box.setStyleSheet("background:rgba(10,20,40,0.7);border:2px solid #0ff;border-radius:18px;")
        chat_box.setMinimumWidth(340)
        chat_layout = QVBoxLayout(chat_box)
        chat_layout.setContentsMargins(18, 18, 18, 18)
        chat_layout.setSpacing(12)
        self.chat_layout = chat_layout
        msg1 = QLabel("<span style='color:#fff;'>¿En qué puedo ayudarte hoy?</span><span style='float:right;color:#0ff;font-size:12px;'>10:00</span>")
        msg1.setStyleSheet("background:rgba(0,0,0,0.18);border-radius:12px;padding:10px 16px;font-size:16px;")
        chat_layout.addWidget(msg1)
        msg2 = QLabel("<span style='color:#fff;'>Necesito ayuda con mi presentación</span><span style='float:right;color:#0ff;font-size:12px;'>10:01</span>")
        msg2.setStyleSheet("background:rgba(0,0,0,0.18);border-radius:12px;padding:10px 16px;font-size:16px;")
        chat_layout.addWidget(msg2)
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setStyleSheet("QScrollArea{border:0;} QScrollBar:vertical{background:transparent;width:8px;} QScrollBar::handle:vertical{background:#0ff;border-radius:4px;}")
        self.chat_scroll.setWidget(chat_box)
        panel_chat.addWidget(self.chat_scroll)

        # Botón micrófono grande
        self.btn_micro = QPushButton()
        self.btn_micro.setFixedSize(80, 80)
        self.btn_micro.setStyleSheet("border-radius:40px;background:rgba(0,255,255,0.10);border:3px solid #0ff;")
        self.btn_micro.setIconSize(self.btn_micro.size())
        self.btn_micro.setText("")
        self.btn_micro.clicked.connect(self.accion_microfono)
        panel_chat.addWidget(self.btn_micro, alignment=Qt.AlignHCenter)
        # Texto "Habla ahora"
        self.speak_lbl = QLabel("Habla ahora")
        self.speak_lbl.setStyleSheet("color:#0ff;font-size:18px;font-family:'Orbitron', 'Montserrat', Arial;")
        panel_chat.addWidget(self.speak_lbl, alignment=Qt.AlignHCenter)
        # Entrada de comandos escritos
        cmd_row = QHBoxLayout()
        self.input_cmd = QLineEdit()
        self.input_cmd.setPlaceholderText("Escribe un comando o pregunta…")
        self.input_cmd.setStyleSheet("background:rgba(0,0,0,0.25);color:#fff;border-radius:10px;padding:10px;font-size:14px;border:1px solid #0ff;")
        btn_enviar = QPushButton("Enviar")
        btn_enviar.setStyleSheet("color:#0ff;border:1px solid #0ff;border-radius:10px;padding:10px;background:transparent;")
        cmd_row.addWidget(self.input_cmd, 1)
        cmd_row.addWidget(btn_enviar)
        panel_chat.addLayout(cmd_row)
        panel_chat.addStretch(1)

        # Atajo de teclado para activar el micrófono (Barra espaciadora)
        try:
            self.shortcut_mic = QShortcut(Qt.Key_Space, self)
            self.shortcut_mic.activated.connect(self.accion_microfono)
        except Exception:
            pass

        # --- Panel de notas ---
        panel_notas = QVBoxLayout()
        panel_notas.setSpacing(10)
        notes_box = QWidget()
        notes_box.setStyleSheet("background:rgba(30,0,60,0.7);border:2px solid #a0f;border-radius:18px;")
        notes_box.setMinimumWidth(260)
        notes_layout = QVBoxLayout(notes_box)
        notes_layout.setContentsMargins(12, 12, 12, 12)
        notes_lbl = QLabel("Notas")
        notes_lbl.setStyleSheet("color:#a0f;font-size:18px;font-family:'Orbitron', 'Montserrat', Arial;font-weight:bold;")
        notes_layout.addWidget(notes_lbl)
        # Selector de carpeta y crear
        self.carpeta_combo = QComboBox()
        self.carpeta_combo.setStyleSheet("background:rgba(0,0,0,0.18);color:#fff;border-radius:8px;padding:6px;font-size:14px;")
        notes_layout.addWidget(self.carpeta_combo)
        btn_crear_carpeta = QPushButton("Crear carpeta…")
        btn_crear_carpeta.setStyleSheet("color:#a0f;border:1px solid #a0f;border-radius:8px;padding:6px;background:transparent;")
        notes_layout.addWidget(btn_crear_carpeta)
        # Lista de notas
        self.lista_notas = QListWidget()
        self.lista_notas.setStyleSheet("background:rgba(0,0,0,0.18);color:#fff;border-radius:8px;padding:6px;font-size:14px;")
        notes_layout.addWidget(self.lista_notas)
        # Edición de nota
        self.titulo_edit = QLineEdit()
        self.titulo_edit.setPlaceholderText("Título de la nota")
        self.titulo_edit.setStyleSheet("background:rgba(0,0,0,0.18);color:#fff;border-radius:8px;padding:8px;font-size:14px;")
        notes_layout.addWidget(self.titulo_edit)
        self.contenido_edit = QTextEdit()
        self.contenido_edit.setPlaceholderText("Contenido…")
        self.contenido_edit.setStyleSheet("background:rgba(0,0,0,0.18);color:#fff;border-radius:8px;padding:8px;font-size:14px;")
        notes_layout.addWidget(self.contenido_edit)
        # Botones
        btns_row = QHBoxLayout()
        btn_save = QPushButton("Guardar")
        btn_save.setStyleSheet("color:#a0f;border:1px solid #a0f;border-radius:8px;padding:8px;background:transparent;")
        btn_del = QPushButton("Eliminar")
        btn_del.setStyleSheet("color:#f77;border:1px solid #f77;border-radius:8px;padding:8px;background:transparent;")
        btns_row.addWidget(btn_save)
        btns_row.addWidget(btn_del)
        notes_layout.addLayout(btns_row)
        notes_box.setLayout(notes_layout)
        panel_notas.addWidget(notes_box)
        panel_notas.addStretch(1)

        # Wiring
        btn_calendario.clicked.connect(self.abrir_calendario)
        btn_crear_carpeta.clicked.connect(self.crear_carpeta_desde_gui)
        self.carpeta_combo.activated.connect(self.cargar_lista_notas)
        self.lista_notas.itemClicked.connect(self.cargar_nota_desde_lista)
        btn_save.clicked.connect(self.guardar_nota_desde_gui)
        btn_del.clicked.connect(self.eliminar_nota_desde_gui)
        btn_enviar.clicked.connect(self.enviar_comando_escrito)
        self.input_cmd.returnPressed.connect(self.enviar_comando_escrito)

        # Inicializar combos/listas
        self.cargar_combo_carpetas()
        self.cargar_lista_notas()

        # --- Añadir paneles al layout principal ---
        main_layout.addLayout(panel_lateral, 1)
        main_layout.addLayout(panel_chat, 2)
        main_layout.addLayout(panel_notas, 1)
        self.setCentralWidget(central)

    # ===== Helpers de notas (GUI) =====
    def carpeta_actual(self) -> str | None:
        if not hasattr(self, 'carpeta_combo') or self.carpeta_combo.count() == 0:
            return None
        val = self.carpeta_combo.currentText().strip()
        return None if val == "(sin carpeta)" else val

    def cargar_combo_carpetas(self) -> None:
        base = self.ruta_notas()
        os.makedirs(base, exist_ok=True)
        carpetas = [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))]
        self.carpeta_combo.blockSignals(True)
        self.carpeta_combo.clear()
        self.carpeta_combo.addItem("(sin carpeta)")
        for c in sorted(carpetas):
            self.carpeta_combo.addItem(c)
        self.carpeta_combo.blockSignals(False)

    def cargar_lista_notas(self) -> None:
        carpeta = self.carpeta_actual()
        ruta = self.ruta_notas(carpeta)
        os.makedirs(ruta, exist_ok=True)
        self.lista_notas.clear()
        for f in sorted(os.listdir(ruta)):
            if f.endswith('.txt'):
                self.lista_notas.addItem(os.path.splitext(f)[0])

    def cargar_nota_desde_lista(self, item) -> None:
        titulo = item.text()
        carpeta = self.carpeta_actual()
        contenido = self.leer_nota(titulo, carpeta)
        if contenido is None:
            self.chat_signal.emit(f"No se pudo abrir la nota '{titulo}'.", 'sistema')
            return
        self.titulo_edit.setText(titulo)
        self.contenido_edit.setPlainText(contenido)

    def guardar_nota_desde_gui(self) -> None:
        titulo = self.titulo_edit.text().strip()
        contenido = self.contenido_edit.toPlainText()
        if not titulo:
            QMessageBox.warning(self, "Notas", "El título no puede estar vacío.")
            return
        carpeta = self.carpeta_actual()
        try:
            self.guardar_nota(titulo, contenido, carpeta)
            self.chat_signal.emit(f"Nota '{titulo}' guardada.", 'sistema')
            self.cargar_lista_notas()
        except Exception as e:
            QMessageBox.critical(self, "Notas", f"Error guardando la nota: {e}")

    def eliminar_nota_desde_gui(self) -> None:
        item = self.lista_notas.currentItem()
        if not item:
            QMessageBox.information(self, "Notas", "Selecciona una nota para eliminar.")
            return
        titulo = item.text()
        carpeta = self.carpeta_actual()
        if self.eliminar_nota(titulo, carpeta):
            self.chat_signal.emit(f"Nota '{titulo}' eliminada.", 'sistema')
            self.cargar_lista_notas()
            if self.titulo_edit.text().strip() == titulo:
                self.titulo_edit.clear()
                self.contenido_edit.clear()
        else:
            QMessageBox.warning(self, "Notas", f"No se pudo eliminar la nota '{titulo}'.")

    def crear_carpeta_desde_gui(self) -> None:
        nombre, ok = QInputDialog.getText(self, "Crear carpeta", "Nombre de la carpeta:")
        if ok:
            nombre = nombre.strip()
            if not nombre:
                QMessageBox.information(self, "Notas", "El nombre no puede estar vacío.")
                return
            os.makedirs(self.ruta_notas(nombre), exist_ok=True)
            self.cargar_combo_carpetas()
            idx = self.carpeta_combo.findText(nombre)
            if idx >= 0:
                self.carpeta_combo.setCurrentIndex(idx)
            self.cargar_lista_notas()

    # ===== Helpers de notas (filesystem) =====
    def ruta_notas(self, carpeta: str | None = None) -> str:
        base = os.path.join(PROJECT_DIR, 'notas')
        return os.path.join(base, carpeta) if carpeta else base

    def ruta_nota(self, titulo: str, carpeta: str | None = None) -> str:
        nombre = f"{titulo}.txt"
        return os.path.join(self.ruta_notas(carpeta), nombre)

    def guardar_nota(self, titulo: str, contenido: str, carpeta: str | None = None) -> None:
        ruta = self.ruta_nota(titulo, carpeta)
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write(contenido)

    def leer_nota(self, titulo: str, carpeta: str | None = None) -> str | None:
        ruta = self.ruta_nota(titulo, carpeta)
        if not os.path.exists(ruta):
            return None
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return None

    def eliminar_nota(self, titulo: str, carpeta: str | None = None) -> bool:
        ruta = self.ruta_nota(titulo, carpeta)
        if os.path.exists(ruta):
            try:
                os.remove(ruta)
                return True
            except Exception:
                return False
        return False

    def buscar_notas(self, palabra: str, carpeta: str | None = None) -> list[tuple[str, str]]:
        resultados: list[tuple[str, str]] = []
        palabra_l = palabra.lower()
        carpetas = [carpeta] if carpeta else [d for d in os.listdir(self.ruta_notas()) if os.path.isdir(self.ruta_notas(d))]
        for c in carpetas:
            ruta = self.ruta_notas(c)
            for f in os.listdir(ruta):
                if f.endswith('.txt'):
                    titulo = os.path.splitext(f)[0]
                    try:
                        with open(os.path.join(ruta, f), 'r', encoding='utf-8') as fh:
                            contenido = fh.read().lower()
                        if palabra_l in titulo.lower() or palabra_l in contenido:
                            resultados.append((titulo, c))
                    except Exception:
                        pass
        return resultados

    # ===== Calendario =====
    def abrir_calendario(self) -> None:
        """Abre el calendario de eventos en un diálogo modal."""
        try:
            from PyQt5.QtWidgets import QDialog, QVBoxLayout
            from calendario_widget import CalendarioEventos
            eventos_dir = os.path.join(PROJECT_DIR, 'resumenes')
            os.makedirs(eventos_dir, exist_ok=True)
            eventos_path = os.path.join(eventos_dir, 'eventos.json')
            dlg = QDialog(self)
            dlg.setWindowTitle("Calendario de eventos")
            # Asegurar botones de minimizar/maximizar/cerrar
            try:
                dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
            except Exception:
                pass
            lay = QVBoxLayout(dlg)
            calw = CalendarioEventos(eventos_path, parent=dlg)
            lay.addWidget(calw)
            dlg.setLayout(lay)
            # Abrir maximizado (con barra de título visible)
            try:
                dlg.showMaximized()
            except Exception:
                dlg.resize(960, 720)
            # Color de barra de título (Windows 11+)
            QTimer.singleShot(0, lambda: self._aplicar_color_titulo_windows(dlg))
            dlg.exec_()
        except Exception as e:
            self.chat_signal.emit(f"No se pudo abrir el calendario: {e}", 'sistema')

    # ===== Escucha continua (hotword placeholder) =====
    def iniciar_escucha_hey_asistente(self) -> None:
        if getattr(self, 'escuchando', False):
            return
        self.escuchando = True
        def _loop():
            import time
            while getattr(self, 'escuchando', False):
                time.sleep(1.0)
        self._escucha_thread = threading.Thread(target=_loop, daemon=True)
        self._escucha_thread.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = AsistenteMain()
    # Asegurar botones de minimizar/maximizar/cerrar y mostrar maximizada
    try:
        ventana.setWindowFlags(ventana.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
    except Exception:
        pass
    ventana.showMaximized()
    # Aplicar color a la barra de título (Windows 11+)
    QTimer.singleShot(0, ventana._aplicar_color_titulo_windows)
    sys.exit(app.exec_())
