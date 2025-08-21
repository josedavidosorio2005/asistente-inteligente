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
from PyQt5.QtGui import QPainter, QPen, QColor, QLinearGradient, QIcon
from PyQt5.QtCore import Qt, QTimer, QRectF, pyqtSignal

# Asegurar que la carpeta 'src' esté en el path para widgets auxiliares
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(PROJECT_DIR, 'src')
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

# Importar funciones de voz desde el nuevo core; fallback a módulo antiguo si no existe
try:
    # Como añadimos la carpeta 'src' al sys.path, importamos sin el prefijo 'src.'
    from assistant_app.core.voice import listen_once as escuchar_comando, speak as hablar
except Exception:
    from voz import escuchar_comando, hablar
import json
import speech_recognition as sr
from datetime import datetime, timedelta
try:
    from src import db  # nuevo backend SQLite
except ImportError:
    import db  # type: ignore

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
        msg.setWordWrap(True)
        try:
            msg.setTextInteractionFlags(Qt.TextSelectableByMouse)
        except Exception:
            pass
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

    def hablar_async(self, texto: str) -> None:
        """Reproduce TTS en un hilo para no bloquear la UI."""
        def _speak():
            try:
                hablar(texto)
            except Exception:
                pass
        threading.Thread(target=_speak, daemon=True).start()

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
            # Aplicar micrófono configurado
            mic_index = getattr(self, 'config_mic_index', None)
            try:
                mic = sr.Microphone(device_index=mic_index if isinstance(mic_index, int) else None)
            except Exception:
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
        # Ayuda rápida para comandos escritos
        elif texto_l in ("/ayuda", "ayuda", "help"):
            respuesta = (
                "Comandos útiles:\n"
                "- crear evento <nombre> el YYYY-MM-DD [a las HH:MM]\n"
                "- qué tengo hoy | qué tengo semana\n"
                "- abrir calculadora | abrir bloc de notas | abrir navegador\n"
                "- según internet <tu pregunta> | qué es <tema>\n"
                "- crear nota <título> [en <carpeta>] | leer nota <título>\n"
                "- eliminar nota <título> | buscar nota <palabra> [en <carpeta>]\n"
                "- /limpiar_legacy (renombrar archivos legacy eventos.json / notas)\n"
            )
        elif texto_l.strip() == '/limpiar_legacy':
            ok = False
            try:
                ok = db.cleanup_legacy()
            except Exception:
                pass
            respuesta = 'Archivos legacy renombrados.' if ok else 'No había archivos legacy que renombrar.'
        # Decir la hora
        elif "hora" in texto_l:
            from datetime import datetime
            hora = datetime.now().strftime('%H:%M')
            respuesta = f"Son las {hora}."
        # Buscar en Internet (resumen en español y/o Google)
        elif "busca" in texto_l or "buscar" in texto_l:
            import re
            patron = r"busca(r)?( en google)? (.*)"
            m = re.search(patron, texto_l)
            if m and m.group(3):
                query = m.group(3).strip()
                try:
                    from web_search import search_and_answer
                    if m.group(2):
                        # Usuario pidió explícitamente Google
                        respuesta = search_and_answer(query, max_results=5, provider="google")
                    else:
                        # Resumen rápido en español (DuckDuckGo)
                        respuesta = search_and_answer(query, max_results=3)
                except Exception:
                    # Fallback: abrir Google si no hay dependencia
                    import webbrowser
                    url = f"https://www.google.com/search?q={query.replace(' ','+')}"
                    webbrowser.open(url)
                    respuesta = f"Buscando en Google: {query} (abre en el navegador)."
            else:
                respuesta = "¿Qué quieres buscar? Di: 'busca en google ...' o 'busca ...'"
        # Preguntas con respuesta desde Internet (búsqueda + resumen)
        elif any(p in texto_l for p in [
            "según internet", "segun internet", "qué es", "que es", "quién es", "quien es",
            "cómo funciona", "como funciona", "definición de", "definicion de", "investiga",
            "busca en internet", "consulta en internet"
        ]):
            # Ejecutar en segundo plano para no bloquear la UI
            import re
            query = texto_l
            for kw in ["según internet", "segun internet", "busca en internet", "consulta en internet", "investiga"]:
                query = query.replace(kw, "").strip()
            query = re.sub(r"^(qué es|que es|quién es|quien es|cómo funciona|como funciona|definición de|definicion de)\s*", "", query)
            if not query:
                query = texto
            self.chat_signal.emit("Buscando en Internet…", 'sistema')
            self._buscar_internet_async(query, provider="ddg")
            return
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
                    def _fmt(ev):
                        return f"{ev['evento']} ({ev['fecha']} {ev.get('hora','')}).".replace(' ()','')
                    lista = ", ".join([_fmt(ev) for ev in eventos])
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
                    def _fmt(ev):
                        return f"{ev['evento']} ({ev['fecha']} {ev.get('hora','')}).".replace(' ()','')
                    lista = ", ".join([_fmt(ev) for ev in eventos])
                    respuesta = f"Esta semana: {lista}."
                else:
                    respuesta = msg
            except Exception as e:
                respuesta = f"No pude consultar el calendario: {e}"
        # Calendario: crear evento
        elif "crear evento" in texto_l:
            import re
            # Acepta hora opcional: "a las HH:MM" o solo "HH:MM" al final
            patron = r"crear evento (.+?) (?:el|para) (\d{4}-\d{2}-\d{2})(?:\s+(?:a las\s+)?(\d{1,2}:\d{2}))?"
            m = re.search(patron, texto_l)
            if m:
                titulo = m.group(1).strip()
                fecha = m.group(2)
                hora = (m.group(3) or '').strip() or None
                # Normalizar hora a HH:MM
                if hora:
                    try:
                        h, mi = map(int, hora.split(':'))
                        hora = f"{h:02d}:{mi:02d}"
                    except Exception:
                        pass
                try:
                    from calendario import crear_evento
                    msg = crear_evento(titulo, fecha, hora)
                    respuesta = f"{msg} {titulo} el {fecha}{' a las ' + hora if hora else ''}."
                except Exception as e:
                    respuesta = f"No pude crear el evento: {e}"
            else:
                respuesta = "Di: 'crear evento <nombre> el YYYY-MM-DD [a las HH:MM]'."
        # Eliminar evento
        elif "eliminar evento" in texto_l:
            import re
            patron = r"eliminar evento (.+?) (?:el|de) (\d{4}-\d{2}-\d{2})(?:\s+(?:a las\s+)?(\d{1,2}:\d{2}))?"
            m = re.search(patron, texto_l)
            if m:
                titulo = m.group(1).strip()
                fecha = m.group(2)
                hora = (m.group(3) or '').strip() or None
                if hora:
                    try:
                        h, mi = map(int, hora.split(':'))
                        hora = f"{h:02d}:{mi:02d}"
                    except Exception:
                        pass
                try:
                    from calendario import eliminar_evento_por_datos
                    eliminados = eliminar_evento_por_datos(titulo, fecha, hora)
                    if eliminados:
                        respuesta = f"Evento eliminado: {titulo} el {fecha}{' a las ' + hora if hora else ''}."
                    else:
                        respuesta = "No se encontró el evento para eliminar."
                except Exception as e:
                    respuesta = f"Error eliminando el evento: {e}"
            else:
                respuesta = "Di: 'eliminar evento <nombre> el YYYY-MM-DD [a las HH:MM]' para borrarlo."
        # Calendario: abrir calendario
        elif ("calendario" in texto_l) and ("abre" in texto_l or "abrir" in texto_l or "mostrar" in texto_l):
            try:
                self.abrir_calendario()
                respuesta = "Abriendo calendario."
                accion_realizada = True
            except Exception as e:
                respuesta = f"No se pudo abrir el calendario: {e}"
        # Eliminar evento: "eliminar evento <titulo> el YYYY-MM-DD [a las HH:MM]"
        elif "eliminar evento" in texto_l:
            import re
            patron = r"eliminar evento (.+?) el (\d{4}-\d{2}-\d{2})(?:\s+(?:a las\s+)?(\d{1,2}:\d{2}))?"
            m = re.search(patron, texto_l)
            if m:
                titulo = m.group(1).strip()
                fecha = m.group(2)
                hora = (m.group(3) or '').strip() or None
                if hora:
                    try:
                        h, mi = map(int, hora.split(':'))
                        hora = f"{h:02d}:{mi:02d}"
                    except Exception:
                        pass
                try:
                    from calendario import eliminar_evento_por_datos
                    eliminados = eliminar_evento_por_datos(titulo, fecha, hora)
                    if eliminados:
                        respuesta = f"Evento eliminado: {titulo} el {fecha}{' a las '+hora if hora else ''}."
                    else:
                        respuesta = "No se encontró el evento para eliminar."
                except Exception as e:
                    respuesta = f"No pude eliminar el evento: {e}"
            else:
                respuesta = "Formato: eliminar evento <titulo> el YYYY-MM-DD [a las HH:MM]"
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
        self.hablar_async(respuesta)

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
        # Recordatorios de eventos (diario) y alertas puntuales (cada minuto)
        self._recordatorio_fecha_mostrado = None
        self._timer_recordatorios = None
        self._timer_alertas = None
        self._active_notifs = []
        # Config runtime (actualizado desde panel)
        self.config_mic_index = None
        self.init_ui()
        # Mensaje de migración (primera vez)
        try:
            msg_m = db.consume_migration_message()
            if msg_m:
                self.chat_signal.emit(msg_m, 'sistema')
        except Exception:
            pass
        # Iniciar recordatorios después de construir la UI
        try:
            self._iniciar_recorditorios()
        except Exception:
            pass
        # Iniciar alertas puntuales (cada minuto)
        try:
            self._iniciar_alertas()
        except Exception:
            pass

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
        # Botón circular de ayuda
        self.btn_help = QPushButton("?")
        self.btn_help.setFixedSize(40, 40)
        self.btn_help.setStyleSheet(
            "border-radius:20px;border:2px solid #0ff;color:#0ff;background:transparent;"
            "font-weight:bold;font-size:16px;min-width:40px;min-height:40px;"
        )
        try:
            self.btn_help.setCursor(Qt.PointingHandCursor)
            self.btn_help.setToolTip("Mostrar/ocultar ayuda de comandos")
        except Exception:
            pass
        # Contenedor de ayuda plegable
        self.help_container = QWidget()
        help_v = QVBoxLayout(self.help_container)
        help_v.setContentsMargins(0, 0, 0, 0)
        help_v.setSpacing(8)
        self.help_scroll = QScrollArea()
        self.help_scroll.setWidgetResizable(True)
        self.help_scroll.setStyleSheet(
            "QScrollArea{background:rgba(10,20,40,0.45);border:1px solid #0ff;border-radius:12px;}"
            "QScrollBar:vertical{background:transparent;width:8px;}"
            "QScrollBar::handle:vertical{background:#0ff;border-radius:4px;}"
        )
        help_inner = QWidget()
        help_inner_l = QVBoxLayout(help_inner)
        help_inner_l.setContentsMargins(12, 12, 12, 12)
        self.help_label = QLabel()
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet("color:#e6e8ff;font-size:14px;")
        try:
            self.help_label.setTextFormat(Qt.RichText)
            self.help_label.setOpenExternalLinks(True)
        except Exception:
            pass
        self.help_label.setText("")
        help_inner_l.addWidget(self.help_label)
        self.help_scroll.setWidget(help_inner)
        help_v.addWidget(self.help_scroll)
        self.help_container.setVisible(False)

        # Panel de configuración plegable
        self.config_container = QWidget()
        self.config_container.setVisible(False)
        cfg_lay = QVBoxLayout(self.config_container)
        cfg_lay.setContentsMargins(10, 14, 10, 14)
        cfg_lay.setSpacing(12)
        self.config_container.setStyleSheet(
            "QWidget#DeviceCard{background:rgba(255,255,255,0.04);border:1px solid rgba(0,255,255,0.25);border-radius:10px;}"
            "QWidget#DeviceCard:hover{background:rgba(0,255,255,0.08);border:1px solid #0ff;}"
            "QPushButton#DeviceBtn{background:transparent;border:none;text-align:left;padding:0;margin:0;}"
            "QPushButton#DeviceBtn:focus{outline:0;}"
            "QLabel{color:#d0faff;font-size:13px;}"
        )
        title_cfg = QLabel("Audio / Dispositivos")
        title_cfg.setStyleSheet("color:#0ff;font-size:15px;font-weight:600;margin-left:2px;")
        cfg_lay.addWidget(title_cfg)

        # Tarjeta genérica (entrada / salida)
        def build_device_card(nombre_section: str, attr_button: str, click_handler):
            card = QWidget()
            card.setObjectName("DeviceCard")
            v = QVBoxLayout(card)
            v.setContentsMargins(14, 10, 14, 10)
            v.setSpacing(4)
            top_row = QHBoxLayout()
            top_row.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(nombre_section)
            lbl.setStyleSheet("color:#fff;font-size:13px;font-weight:600;")
            top_row.addWidget(lbl)
            top_row.addStretch(1)
            arrow = QLabel("›")  # right chevron
            arrow.setStyleSheet("color:#0ff;font-size:18px;font-weight:bold;")
            top_row.addWidget(arrow)
            v.addLayout(top_row)
            btn = QPushButton("Predeterminado")
            btn.setObjectName("DeviceBtn")
            btn.setStyleSheet("color:#8be9ff;font-size:13px;font-weight:500;padding:0 0 2px 0;")
            btn.clicked.connect(click_handler)
            v.addWidget(btn)
            setattr(self, attr_button, btn)
            cfg_lay.addWidget(card)
        build_device_card("Dispositivo de entrada", 'btn_input_device', lambda: self._show_device_menu('input'))
        build_device_card("Dispositivo de salida", 'btn_output_device', lambda: self._show_device_menu('output'))

        hint = QLabel("Los cambios se guardan al seleccionar un dispositivo.")
        hint.setStyleSheet("color:#6ac7d8;font-size:11px;margin-top:4px;")
        cfg_lay.addWidget(hint)

        cfg_lay.addStretch(1)

        # Botón fila para help/config
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.addWidget(self.btn_help, alignment=Qt.AlignLeft)
        btn_row.addStretch(1)
        panel_lateral.addLayout(btn_row)
        panel_lateral.addWidget(self.help_container)
        panel_lateral.addWidget(self.config_container)

        def menu_btn(text, icon=None):
            btn = QPushButton(text)
            btn.setFixedHeight(48)
            btn.setStyleSheet("color:#0ff;background:transparent;border:none;font-size:17px;text-align:left;padding-left:16px;border-radius:12px;")
            return btn
        panel_lateral.addWidget(menu_btn("Chat"))
        btn_calendario = menu_btn("Calendario")
        panel_lateral.addWidget(btn_calendario)
        panel_lateral.addWidget(menu_btn("Aplicaciones"))
        self.btn_config_toggle = menu_btn("Configuración")
        panel_lateral.addWidget(self.btn_config_toggle)
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
        self.btn_enviar = QPushButton("Enviar")
        try:
            self.btn_enviar.setToolTip("Enviar mensaje (Enter)")
            self.btn_enviar.setCursor(Qt.PointingHandCursor)
        except Exception:
            pass
        self.btn_enviar.setStyleSheet("color:#0ff;border:1px solid #0ff;border-radius:10px;padding:10px;background:transparent;")
        cmd_row.addWidget(self.input_cmd, 1)
        cmd_row.addWidget(self.btn_enviar)
        panel_chat.addLayout(cmd_row)
        panel_chat.addStretch(1)

        # Atajos
        try:
            self.shortcut_mic = QShortcut(Qt.Key_Space, self)
            self.shortcut_mic.activated.connect(self.accion_microfono)
        except Exception:
            pass
        try:
            self.shortcut_exit = QShortcut(Qt.Key_Escape, self)
            self.shortcut_exit.setContext(Qt.ApplicationShortcut)
            self.shortcut_exit.activated.connect(self.cerrar_aplicacion)
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
        self.carpeta_combo = QComboBox()
        self.carpeta_combo.setStyleSheet("background:rgba(0,0,0,0.18);color:#fff;border-radius:8px;padding:6px;font-size:14px;")
        notes_layout.addWidget(self.carpeta_combo)
        btn_crear_carpeta = QPushButton("Crear carpeta…")
        btn_crear_carpeta.setStyleSheet("color:#a0f;border:1px solid #a0f;border-radius:8px;padding:6px;background:transparent;")
        notes_layout.addWidget(btn_crear_carpeta)
        self.lista_notas = QListWidget()
        self.lista_notas.setStyleSheet("background:rgba(0,0,0,0.18);color:#fff;border-radius:8px;padding:6px;font-size:14px;")
        notes_layout.addWidget(self.lista_notas)
        self.titulo_edit = QLineEdit()
        self.titulo_edit.setPlaceholderText("Título de la nota")
        self.titulo_edit.setStyleSheet("background:rgba(0,0,0,0.18);color:#fff;border-radius:8px;padding:8px;font-size:14px;")
        notes_layout.addWidget(self.titulo_edit)
        self.contenido_edit = QTextEdit()
        self.contenido_edit.setPlaceholderText("Contenido…")
        self.contenido_edit.setStyleSheet("background:rgba(0,0,0,0.18);color:#fff;border-radius:8px;padding:8px;font-size:14px;")
        notes_layout.addWidget(self.contenido_edit)
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
        self.btn_enviar.clicked.connect(self.enviar_comando_escrito)
        self.input_cmd.returnPressed.connect(self.enviar_comando_escrito)
        try:
            self.btn_help.clicked.connect(self._toggle_help)
        except Exception:
            pass
        self.btn_config_toggle.clicked.connect(self._toggle_config)

        # Inicializar combos/listas
        self.cargar_combo_carpetas()
        self.cargar_lista_notas()
        try:
            self.input_cmd.setFocus()
        except Exception:
            pass

        # --- Añadir paneles al layout principal ---
        main_layout.addLayout(panel_lateral, 1)
        main_layout.addLayout(panel_chat, 2)
        main_layout.addLayout(panel_notas, 1)
        self.setCentralWidget(central)

        # Cargar config y poblar dispositivos
        self._cargar_config_inicial()
        # (El menú emergente generará la lista en tiempo real; ya no llamamos a refrescar_dispositivos())

    def _cargar_config_inicial(self):
        try:
            from src import config_store
        except Exception:
            import config_store  # type: ignore
        cfg = config_store.load_config()
        self.config_mic_index = cfg.get('mic_index')
        self._actualizar_label_mic()

    def _actualizar_label_mic(self, preview_index=None):
        idx = preview_index if preview_index is not None else getattr(self, 'config_mic_index', None)
        try:
            mic_names = sr.Microphone.list_microphone_names() or []
        except Exception:
            mic_names = []
        if isinstance(idx, int) and 0 <= idx < len(mic_names):
            nombre = mic_names[idx]
            corto = (nombre[:34] + '…') if len(nombre) > 35 else nombre
            texto_btn = f"{corto}"
            if hasattr(self, 'btn_input_device'):
                self.btn_input_device.setText(texto_btn)
            if hasattr(self, 'btn_config_toggle'):
                corto_menu = (nombre[:22] + '…') if len(nombre) > 23 else nombre
                self.btn_config_toggle.setText(f"Configuración · {corto_menu}")
        else:
            if hasattr(self, 'btn_input_device'):
                self.btn_input_device.setText("Predeterminado")
            if hasattr(self, 'btn_config_toggle'):
                self.btn_config_toggle.setText("Configuración")

    def _show_device_menu(self, kind: str):
        from PyQt5.QtWidgets import QMenu, QAction
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu{background:#101821;border:1px solid #0ff;padding:6px;}"
            "QMenu::item{color:#d0faff;padding:6px 26px 6px 24px;border-radius:6px;font-size:13px;}"
            "QMenu::item:selected{background:rgba(0,255,255,0.15);color:#fff;}"
            "QMenu::separator{height:1px;background:rgba(255,255,255,0.12);margin:6px 4px;}"
        )
        try:
            current_mics = sr.Microphone.list_microphone_names() if kind == 'input' else []
        except Exception:
            current_mics = []
        # Acción predeterminada
        act_default = QAction("Predeterminado del sistema", menu)
        act_default.setCheckable(True)
        if kind == 'input' and (self.config_mic_index is None):
            act_default.setChecked(True)
        menu.addAction(act_default)
        def set_default():
            if kind == 'input':
                self.config_mic_index = None
                self._guardar_config()
                self._actualizar_label_mic()
        act_default.triggered.connect(set_default)
        if kind == 'input':
            # Listar mics
            for i, name in enumerate(current_mics):
                act = QAction(f"{name}", menu)
                act.setCheckable(True)
                if self.config_mic_index == i:
                    act.setChecked(True)
                def make_handler(index=i):
                    return lambda: self._select_microphone(index)
                act.triggered.connect(make_handler(i))
                menu.addAction(act)
            menu.addSeparator()
            act_refresh = QAction("Refrescar lista", menu)
            act_refresh.triggered.connect(lambda: self._refresh_devices_menu(menu, kind))
            menu.addAction(act_refresh)
        else:
            # Placeholder salida
            placeholder = QAction("(Solo predeterminado por ahora)", menu)
            placeholder.setEnabled(False)
            menu.addAction(placeholder)
        btn = self.btn_input_device if kind == 'input' else self.btn_output_device
        pos = btn.mapToGlobal(btn.rect().bottomLeft())
        menu.exec_(pos)

    def _refresh_devices_menu(self, old_menu, kind):
        # Cerrar y reabrir menú actualizado
        try:
            old_menu.close()
        except Exception:
            pass
        QTimer.singleShot(0, lambda: self._show_device_menu(kind))

    def _select_microphone(self, index: int):
        self.config_mic_index = index
        self._guardar_config()
        self._actualizar_label_mic()

    def _guardar_config(self):
        try:
            from src import config_store
        except Exception:
            import config_store  # type: ignore
        cfg = config_store.load_config()
        cfg['mic_index'] = self.config_mic_index
        cfg['output_device_index'] = None
        config_store.save_config(cfg)

    def _toggle_config(self, force_close=False):
        visible = self.config_container.isVisible()
        if force_close:
            self.config_container.setVisible(False)
            return
        try:
            if self.help_container.isVisible():
                self.help_container.setVisible(False)
        except Exception:
            pass
        self.config_container.setVisible(not visible)
        if self.config_container.isVisible():
            # Cargar lista actual al abrir
            QTimer.singleShot(50, self._actualizar_label_mic)
    # ...existing code for rest of class (methods below) without the duplicate _toggle_config at bottom...
    # (Se ha eliminado la segunda definición redundante de _toggle_config)
    # ===== Recordatorios de eventos =====
    def _iniciar_recordatorios(self) -> None:
        """Configura un temporizador que recuerda eventos del día una vez al día."""
        # Mostrar inmediatamente si aplica
        self._recordatorio_si_corresponde(force=True)
        # Revisar cada 10 minutos si cambió el día
        self._timer_recordatorios = QTimer(self)
        self._timer_recordatorios.setInterval(10 * 60 * 1000)  # 10 minutos
        self._timer_recorditorios_cb = getattr(self, "_recordatorio_si_corresponde")  # evitar pérdida por GC
        self._timer_recordatorios.timeout.connect(self._recorditorio_timeout)
        self._timer_recordatorios.start()

    def _recorditorio_timeout(self) -> None:
        try:
            self._recordatorio_si_corresponde()
        except Exception:
            pass

    def _recordatorio_si_corresponde(self, force: bool = False) -> None:
        from datetime import datetime as _dt
        hoy_str = str(_dt.now().date())
        if (not force) and (self._recordatorio_fecha_mostrado == hoy_str):
            return
        # Consultar eventos de hoy
        try:
            from calendario import consultar_eventos
            eventos, msg = consultar_eventos('hoy')
        except Exception:
            eventos = []
            msg = "No pude consultar el calendario."
        # Filtrar completados para no anunciar
        pendientes = [ev for ev in eventos if not ev.get('completado')]
        completados = [ev for ev in eventos if ev.get('completado')]
        if pendientes:
            lista = ", ".join([f"{ev['evento']} ({ev['fecha']} {ev.get('hora','')}).".replace(' ()','') for ev in pendientes])
            aviso = f"Recordatorio: Hoy tienes {len(pendientes)} evento(s): {lista}."
            if completados:
                aviso += f" Ya completados: {len(completados)}."
        else:
            aviso = msg
        # Emitir aviso solo si hay algo útil o si es la primera vez del día
        if eventos:
            self.chat_signal.emit(aviso, 'sistema')
            self.hablar_async(aviso)
        self._recordatorio_fecha_mostrado = hoy_str

    # ===== Alertas de eventos (hora exacta y 5 minutos antes) =====
    def _iniciar_alertas(self) -> None:
        """Temporizador que revisa cada minuto si hay que disparar alertas."""
        self._timer_alertas = QTimer(self)
        self._timer_alertas.setInterval(60 * 1000)  # 1 minuto
        self._timer_alertas.timeout.connect(self._revisar_alertas)
        self._timer_alertas.start()

    def _revisar_alertas(self) -> None:
        from datetime import datetime as _dt
        hora_actual = _dt.now().strftime('%H:%M')
        fecha_actual = str(_dt.now().date())
        try:
            from calendario import leer_eventos
            eventos = leer_eventos()
        except Exception:
            eventos = []
        for ev in eventos:
            fecha = ev.get('fecha')
            hora = ev.get('hora')
            if ev.get('completado'):
                continue
            if fecha != fecha_actual or not hora:
                continue
            # Comparar hora exacta
            if hora == hora_actual:
                self._disparar_alerta(ev, previo=False)
            # Comparar 5 minutos antes
            try:
                h, m = map(int, hora.split(':'))
                dt_ev = _dt.strptime(f"{fecha} {h:02d}:{m:02d}", "%Y-%m-%d %H:%M")
                dt_prev = dt_ev - timedelta(minutes=5)
                if _dt.now().strftime('%Y-%m-%d %H:%M') == dt_prev.strftime('%Y-%m-%d %H:%M'):
                    self._disparar_alerta(ev, previo=True)
            except Exception:
                continue

    def _disparar_alerta(self, ev: dict, previo: bool) -> None:
        """Muestra en chat, reproduce sonido y notificación interactiva."""
        titulo = ev.get('evento', 'Evento')
        fecha = ev.get('fecha')
        hora = ev.get('hora', '')
        tipo = "(en 5 min) " if previo else ""
        msg = f"Alerta {tipo}: {titulo} a las {hora} el {fecha}."
        # Chat + voz
        self.chat_signal.emit(msg, 'sistema')
        self.hablar_async(msg)
        # Sonido breve (usar winsound en Windows)
        try:
            if sys.platform == 'win32':
                import winsound
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass
        # Notificación interactiva en Qt
        try:
            self._notificacion_interactiva_evento(titulo, fecha, hora, previo)
        except Exception:
            pass

    def _notificar_sistema(self, titulo: str, mensaje: str) -> None:
        """Muestra una notificación del sistema en Windows.

        En Windows usa win10toast si está disponible; si no, intenta Toast de winrt.
        """
        if sys.platform != 'win32':
            return
        # Intentar win10toast
        try:
            from win10toast import ToastNotifier  # type: ignore
            toaster = ToastNotifier()
            toaster.show_toast(titulo, mensaje, icon_path=None, duration=5, threaded=True)
            return
        except Exception:
            pass
        # Fallback: simple aviso por consola si no hay backend
        try:
            print(f"[NOTIFICACIÓN] {titulo}: {mensaje}")
        except Exception:
            pass

    def _notificacion_interactiva_evento(self, titulo: str, fecha: str, hora: str, previo: bool) -> None:
        """Muestra un pequeño diálogo flotante con acciones: Ya lo hice, Posponer 5 min."""
        try:
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
        except Exception:
            return
        dlg = QDialog(self)
        dlg.setWindowFlags(dlg.windowFlags() | Qt.Tool | Qt.WindowStaysOnTopHint)
        dlg.setStyleSheet("background:#1e1f29;color:#fff;QPushButton{border:1px solid #0ff;border-radius:8px;padding:6px 10px;background:transparent;color:#0ff;} QPushButton:hover{background:rgba(0,255,255,0.1);} QLabel{color:#e6e8ff;}")
        dlg.setWindowTitle("Recordatorio de evento")
        lay = QVBoxLayout()
        txt = "(en 5 min) " if previo else ""
        lbl = QLabel(f"{txt}{titulo} — {fecha} {hora}")
        lay.addWidget(lbl)
        btns = QHBoxLayout()
        btn_done = QPushButton("Ya lo hice")
        btn_snooze = QPushButton("Posponer 5 min")
        btns.addWidget(btn_done)
        btns.addWidget(btn_snooze)
        lay.addLayout(btns)
        dlg.setLayout(lay)
        dlg.resize(380, 120)

        def marcar_completado():
            try:
                from calendario import marcar_evento_completado
                marcar_evento_completado(titulo, fecha, hora or None, True)
            except Exception:
                pass
            dlg.accept()

        def posponer():
            # Programar una alerta manual 5 minutos después
            try:
                from datetime import datetime as _dt
                from datetime import timedelta as _td
                objetivo = _dt.now() + _td(minutes=5)
                # Temporizador único
                t = QTimer(self)
                t.setSingleShot(True)
                t.setInterval(5 * 60 * 1000)
                def fire():
                    ev = {'evento': titulo, 'fecha': objetivo.strftime('%Y-%m-%d'), 'hora': objetivo.strftime('%H:%M')}
                    self._disparar_alerta(ev, previo=False)
                t.timeout.connect(fire)
                t.start()
            except Exception:
                pass
            dlg.accept()

        btn_done.clicked.connect(marcar_completado)
        btn_snooze.clicked.connect(posponer)
        self._active_notifs.append(dlg)
        dlg.show()
        try:
            dlg.raise_()
            dlg.activateWindow()
        except Exception:
            pass

    # ===== Helpers de notas (GUI) =====
    def carpeta_actual(self) -> str | None:
        if not hasattr(self, 'carpeta_combo') or self.carpeta_combo.count() == 0:
            return None
        val = self.carpeta_combo.currentText().strip()
        return None if val == "(sin carpeta)" else val

    def cargar_combo_carpetas(self) -> None:
        try:
            carpetas = db.note_list_folders()
        except Exception:
            carpetas = []
        self.carpeta_combo.blockSignals(True)
        self.carpeta_combo.clear()
        self.carpeta_combo.addItem("(sin carpeta)")
        for c in carpetas:
            self.carpeta_combo.addItem(c)
        self.carpeta_combo.blockSignals(False)

    def cargar_lista_notas(self) -> None:
        carpeta = self.carpeta_actual()
        try:
            titulos = db.note_list_titles(carpeta)
        except Exception:
            titulos = []
        self.lista_notas.clear()
        for t in titulos:
            self.lista_notas.addItem(t)

    def cargar_nota_desde_lista(self, item) -> None:
        titulo = item.text()
        carpeta = self.carpeta_actual()
        try:
            contenido = db.note_get(titulo, carpeta)
        except Exception:
            contenido = None
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
        if db.note_upsert(titulo, contenido, carpeta):
            self.chat_signal.emit(f"Nota '{titulo}' guardada.", 'sistema')
            self.cargar_lista_notas()
        else:
            QMessageBox.critical(self, "Notas", "Error guardando la nota en la base de datos.")

    def eliminar_nota_desde_gui(self) -> None:
        item = self.lista_notas.currentItem()
        if not item:
            QMessageBox.information(self, "Notas", "Selecciona una nota para eliminar.")
            return
        titulo = item.text()
        carpeta = self.carpeta_actual()
        if db.note_delete(titulo, carpeta):
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
            # Crear una nota dummy para asegurar carpeta en listado si está vacía
            dummy_title = f"__carpeta__{nombre}__placeholder__"
            db.note_upsert(dummy_title, "", nombre)
            # Eliminar placeholder si existía
            db.note_delete(dummy_title, nombre)
            self.cargar_combo_carpetas()
            idx = self.carpeta_combo.findText(nombre)
            if idx >= 0:
                self.carpeta_combo.setCurrentIndex(idx)
            self.cargar_lista_notas()

    # ===== Helpers de notas (BD) =====
    def guardar_nota(self, titulo: str, contenido: str, carpeta: str | None = None) -> None:
        db.note_upsert(titulo, contenido, carpeta)

    def leer_nota(self, titulo: str, carpeta: str | None = None) -> str | None:
        return db.note_get(titulo, carpeta)

    def eliminar_nota(self, titulo: str, carpeta: str | None = None) -> bool:
        return db.note_delete(titulo, carpeta)

    def buscar_notas(self, palabra: str, carpeta: str | None = None) -> list[tuple[str, str | None]]:
        return db.note_search(palabra, carpeta)

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
            lay = QVBoxLayout()
            calw = CalendarioEventos(eventos_path, parent=dlg)
            try:
                calw.evento_toggle_completado.connect(
                    lambda titulo, fecha, hora, done: self.chat_signal.emit(
                        ("✔️ Evento completado: " if done else "↩️ Evento marcado como pendiente: ") +
                        f"{titulo} ({fecha}{' '+hora if hora else ''})",
                        'sistema'
                    )
                )
                calw.evento_eliminado.connect(
                    lambda titulo, fecha, hora: self.chat_signal.emit(
                        f"🗑️ Evento eliminado: {titulo} ({fecha}{' '+hora if hora else ''})",
                        'sistema'
                    )
                )
            except Exception:
                pass
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
