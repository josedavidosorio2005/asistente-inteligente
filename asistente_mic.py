"""
Aplicación PyQt del Asistente Inteligente.

Funciones clave:
- Chat con mensajes de usuario/sistema.
- Entrada por voz (botón micrófono) y por texto (QLineEdit + Enter/Enviar).
- CRUD de notas en archivos de texto, con carpetas.
- Calendario: diálogo visual y comandos básicos (hoy/semana/crear evento).
- Placeholders seguros para Drive y hotword.

Buenas prácticas:
- Señales Qt para actualizar UI desde hilos.
- Manejo de errores defensivo.
- Estilos unificados.
"""

from __future__ import annotations
import os
import sys
import threading
from datetime import datetime
from typing import Optional

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# Asegurar que la carpeta 'src' esté en el path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(PROJECT_DIR, 'src')
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

# Importar voz desde core nuevo; fallback a legado
try:
    from src.assistant_app.core.voice import listen_once as escuchar_comando, speak as hablar  # type: ignore
except Exception:
    try:
        from src.voz import escuchar_comando, hablar  # type: ignore
    except Exception:
        def escuchar_comando(*args, **kwargs):
            return None
        def hablar(*args, **kwargs):
            pass


class AsistenteMain(QMainWindow):
    """Ventana principal del asistente."""

    chat_signal = pyqtSignal(str, str)  # texto, tipo in {'usuario','sistema'}

    # ========= Ciclo de vida =========
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Asistente Inteligente - Voz")
        self.setGeometry(200, 100, 420, 740)
        self.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #111, stop:1 #444);")

        self.chat_layout = None  # se asigna en init_ui
        self.chat_signal.connect(self.mostrar_mensaje_chat)
        self.escuchando = False
        self._escucha_thread: Optional[threading.Thread] = None
        self._escucha_iniciada = False

        self.init_ui()

    def showEvent(self, event):  # type: ignore[override]
        super().showEvent(event)
        if not self._escucha_iniciada:
            self.iniciar_escucha_hey_asistente()
            self._escucha_iniciada = True

    def closeEvent(self, event):  # type: ignore[override]
        try:
            self.escuchando = False
            if self._escucha_thread and self._escucha_thread.is_alive():
                self._escucha_thread.join(timeout=1.0)
        except Exception:
            pass
        super().closeEvent(event)

    # ========= UI =========
    def init_ui(self) -> None:
        central = QWidget()
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(24)

        # Panel lateral
        panel_lateral = QVBoxLayout()
        panel_lateral.setSpacing(32)
        panel_lateral.setAlignment(Qt.AlignTop)
        logo = QLabel()
        logo.setFixedSize(48, 48)
        logo.setStyleSheet("border-radius:24px;border:3px solid #0ff;background:rgba(0,255,255,0.08);")
        panel_lateral.addWidget(logo, alignment=Qt.AlignHCenter)
        titulo = QLabel("Asistente de PC")
        titulo.setStyleSheet("color:#0ff;font-size:22px;font-family:'Montserrat', Arial;font-weight:bold;")
        panel_lateral.addWidget(titulo, alignment=Qt.AlignHCenter)
        def menu_btn(text):
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

        # Panel chat
        panel_chat = QVBoxLayout()
        panel_chat.setSpacing(18)
        chat_box = QWidget()
        chat_box.setStyleSheet("background:rgba(10,20,40,0.7);border:2px solid #0ff;border-radius:18px;")
        chat_box.setMinimumWidth(340)
        chat_layout = QVBoxLayout(chat_box)
        chat_layout.setContentsMargins(18, 18, 18, 18)
        chat_layout.setSpacing(12)
        self.chat_layout = chat_layout
        # Mensaje inicial
        msg1 = QLabel("<span style='color:#fff;'>¿En qué puedo ayudarte hoy?</span>")
        msg1.setStyleSheet("background:rgba(0,0,0,0.18);border-radius:12px;padding:10px 16px;font-size:16px;")
        chat_layout.addWidget(msg1)
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setStyleSheet("QScrollArea{border:0;} QScrollBar:vertical{background:transparent;width:8px;} QScrollBar::handle:vertical{background:#0ff;border-radius:4px;}")
        self.chat_scroll.setWidget(chat_box)
        panel_chat.addWidget(self.chat_scroll)

        # Micrófono
        self.btn_micro = QPushButton()
        self.btn_micro.setFixedSize(80, 80)
        self.btn_micro.setStyleSheet("border-radius:40px;background:rgba(0,255,255,0.10);border:3px solid #0ff;")
        self.btn_micro.setText("🎤")
        self.btn_micro.clicked.connect(self.accion_microfono)
        panel_chat.addWidget(self.btn_micro, alignment=Qt.AlignHCenter)
        self.speak_lbl = QLabel("Habla ahora")
        self.speak_lbl.setStyleSheet("color:#0ff;font-size:18px;font-family:'Montserrat', Arial;")
        panel_chat.addWidget(self.speak_lbl, alignment=Qt.AlignHCenter)

        # Entrada escrita
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

        # Panel notas
        panel_notas = QVBoxLayout()
        panel_notas.setSpacing(10)
        notes_box = QWidget()
        notes_box.setStyleSheet("background:rgba(30,0,60,0.7);border:2px solid #a0f;border-radius:18px;")
        notes_box.setMinimumWidth(260)
        notes_layout = QVBoxLayout(notes_box)
        notes_layout.setContentsMargins(12, 12, 12, 12)
        notes_lbl = QLabel("Notas")
        notes_lbl.setStyleSheet("color:#a0f;font-size:18px;font-family:'Montserrat', Arial;font-weight:bold;")
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

        # Wiring UI
        btn_calendario.clicked.connect(self.abrir_calendario)
        btn_crear_carpeta.clicked.connect(self.crear_carpeta_desde_gui)
        self.carpeta_combo.activated.connect(self.cargar_lista_notas)
        self.lista_notas.itemClicked.connect(self.cargar_nota_desde_lista)
        btn_save.clicked.connect(self.guardar_nota_desde_gui)
        btn_del.clicked.connect(self.eliminar_nota_desde_gui)
        btn_enviar.clicked.connect(self.enviar_comando_escrito)
        self.input_cmd.returnPressed.connect(self.enviar_comando_escrito)

        # Inicializar notas
        self.cargar_combo_carpetas()
        self.cargar_lista_notas()

        # Layout maestro
        main_layout.addLayout(panel_lateral, 1)
        main_layout.addLayout(panel_chat, 2)
        main_layout.addLayout(panel_notas, 1)
        self.setCentralWidget(central)

    def mostrar_mensaje_chat(self, texto: str, tipo: str) -> None:
        if not self.chat_layout:
            return
        msg = QLabel(texto)
        if tipo == 'usuario':
            msg.setStyleSheet("background:rgba(0,255,255,0.10);border-radius:12px;padding:10px 16px;font-size:16px;color:#0ff;")
        else:
            msg.setStyleSheet("background:rgba(0,0,0,0.18);border-radius:12px;padding:10px 16px;font-size:16px;color:#fff;")
        self.chat_layout.addWidget(msg)
        self.autoscroll_chat()

    def autoscroll_chat(self) -> None:
        if hasattr(self, 'chat_scroll') and self.chat_scroll is not None:
            try:
                bar = self.chat_scroll.verticalScrollBar()
                bar.setValue(bar.maximum())
            except Exception:
                pass

    # ========= Voz =========
    def accion_microfono(self) -> None:
        self.activar_reconocimiento_voz()

    def activar_reconocimiento_voz(self) -> None:
        import speech_recognition as sr
        if not hasattr(self, '_btn_micro_style'):
            self._btn_micro_style = self.btn_micro.styleSheet()
        self.btn_micro.setEnabled(False)
        self.btn_micro.setStyleSheet("border-radius:40px;background:rgba(255,0,0,0.15);border:3px solid #f55;")
        self.speak_lbl.setText("Escuchando…")
        def reconocer():
            r = sr.Recognizer()
            try:
                with sr.Microphone() as source:
                    self.chat_signal.emit('Habla ahora...', 'sistema')
                    audio = r.listen(source, timeout=5, phrase_time_limit=7)
                texto = r.recognize_google(audio, language='es-ES')
                self.chat_signal.emit(texto, 'usuario')
                self.responder_asistente(texto)
            except Exception:
                self.chat_signal.emit('No se entendió, intenta de nuevo.', 'sistema')
            finally:
                QTimer.singleShot(0, lambda: (
                    self.btn_micro.setEnabled(True),
                    self.btn_micro.setStyleSheet(self._btn_micro_style),
                    self.speak_lbl.setText("Habla ahora")
                ))
        threading.Thread(target=reconocer, daemon=True).start()

    # ========= Comandos =========
    def enviar_comando_escrito(self) -> None:
        texto = (self.input_cmd.text() or "").strip()
        if not texto:
            return
        self.chat_signal.emit(texto, 'usuario')
        self.responder_asistente(texto)
        self.input_cmd.clear()

    def responder_asistente(self, texto: str) -> None:
        t = texto.lower()
        respuesta = ""
        accion_realizada = False

        # Saludo
        if any(s in t for s in ["hola", "buenos días", "buenas tardes", "buenas noches"]):
            respuesta = "¡Hola! ¿En qué puedo ayudarte?"

        # Drive (placeholder)
        elif ("sincroniza" in t or "sube" in t) and "drive" in t:
            self.chat_signal.emit("Subiendo notas a Google Drive...", 'sistema')
            self.sincronizar_con_drive('subir')
            respuesta = "Notas subidas a Drive."
            accion_realizada = True
        elif "descarga" in t and "drive" in t:
            self.chat_signal.emit("Descargando notas de Google Drive...", 'sistema')
            self.sincronizar_con_drive('descargar')
            respuesta = "Notas descargadas de Drive."
            accion_realizada = True

        # Abrir app básicas
        elif "abrir" in t:
            import subprocess
            if "calculadora" in t:
                respuesta = "Abriendo la calculadora."
                accion_realizada = True
                try:
                    subprocess.Popen('calc.exe')
                except Exception:
                    respuesta = "No pude abrir la calculadora."
            elif "bloc de notas" in t or "notas" in t:
                respuesta = "Abriendo el bloc de notas."
                accion_realizada = True
                try:
                    subprocess.Popen('notepad.exe')
                except Exception:
                    respuesta = "No pude abrir el bloc de notas."
            elif any(x in t for x in ["navegador", "chrome", "internet"]):
                respuesta = "Abriendo el navegador."
                accion_realizada = True
                try:
                    subprocess.Popen('start chrome', shell=True)
                except Exception:
                    respuesta = "No pude abrir el navegador."
            else:
                respuesta = "¿Qué aplicación deseas abrir?"

        # Hora
        elif "hora" in t:
            respuesta = f"Son las {datetime.now().strftime('%H:%M')}."

        # Buscar en Google
        elif "busca" in t or "buscar" in t:
            import re, webbrowser
            m = re.search(r"busca(r)? (en google )?(.*)", t)
            if m and m.group(3):
                query = m.group(3).strip()
                url = f"https://www.google.com/search?q={query.replace(' ','+')}"
                webbrowser.open(url)
                respuesta = f"Buscando '{query}' en Google."
            else:
                respuesta = "¿Qué quieres que busque en Google?"

        # Música
        elif "reproduce" in t or "pon música" in t:
            import webbrowser
            respuesta = "Reproduciendo música en YouTube."
            webbrowser.open("https://www.youtube.com/results?search_query=música")

        # Calendario: hoy / semana
        elif ("qué tengo" in t or "que tengo" in t) and "hoy" in t:
            try:
                from src.calendario import consultar_eventos  # type: ignore
                eventos, msg = consultar_eventos('hoy')
                if eventos:
                    lista = ", ".join([f"{ev['evento']} ({ev['fecha']})" for ev in eventos])
                    respuesta = f"Hoy tienes: {lista}."
                else:
                    respuesta = msg
            except Exception as e:
                respuesta = f"No pude consultar el calendario: {e}"
        elif ("qué tengo" in t or "que tengo" in t) and "semana" in t:
            try:
                from src.calendario import consultar_eventos  # type: ignore
                eventos, msg = consultar_eventos('semana')
                if eventos:
                    lista = ", ".join([f"{ev['evento']} ({ev['fecha']})" for ev in eventos])
                    respuesta = f"Esta semana: {lista}."
                else:
                    respuesta = msg
            except Exception as e:
                respuesta = f"No pude consultar el calendario: {e}"

        # Calendario: crear evento
        elif "crear evento" in t:
            import re
            m = re.search(r"crear evento (.+?) (?:el|para) (\d{4}-\d{2}-\d{2})", t)
            if m:
                evento = m.group(1).strip()
                fecha = m.group(2)
                try:
                    from src.calendario import crear_evento  # type: ignore
                    msg = crear_evento(evento, fecha)
                    respuesta = f"{msg} '{evento}' el {fecha}."
                except Exception as e:
                    respuesta = f"No pude crear el evento: {e}"
            else:
                respuesta = "Di: 'crear evento <nombre> el YYYY-MM-DD'."

        # Abrir calendario visual
        elif "calendario" in t and any(x in t for x in ["abre", "abrir", "mostrar"]):
            try:
                self.abrir_calendario()
                respuesta = "Abriendo calendario."
                accion_realizada = True
            except Exception as e:
                respuesta = f"No se pudo abrir el calendario: {e}"

        # Potencia
        elif "apaga" in t or "apagar" in t:
            os.system("shutdown /s /t 1")
            respuesta = "Apagando el equipo."
        elif "reinicia" in t or "reiniciar" in t:
            os.system("shutdown /r /t 1")
            respuesta = "Reiniciando el equipo."

        # Identidad
        elif any(x in t for x in ["quién eres", "quien eres", "tu nombre"]):
            respuesta = "Soy tu asistente inteligente, siempre listo para ayudarte."

        # Notas
        elif "crear nota" in t:
            import re
            m = re.search(r"crear nota (.+?)( en (.+))?$", t)
            if m:
                titulo = m.group(1).strip()
                carpeta = m.group(3).strip() if m.group(3) else None
                self.guardar_nota(titulo, "", carpeta)
                respuesta = f"Nota '{titulo}' creada{(' en ' + carpeta) if carpeta else ''}. ¿Qué contenido quieres guardar?"
            else:
                respuesta = "¿Cómo se llama la nota?"
        elif "editar nota" in t:
            import re
            m = re.search(r"editar nota (.+?)( en (.+))?$", t)
            if m:
                titulo = m.group(1).strip()
                carpeta = m.group(3).strip() if m.group(3) else None
                contenido = self.leer_nota(titulo, carpeta)
                if contenido is not None:
                    respuesta = f"¿Qué nuevo contenido quieres para la nota '{titulo}'?"
                else:
                    respuesta = f"No encontré la nota '{titulo}'."
            else:
                respuesta = "¿Qué nota quieres editar?"
        elif "eliminar nota" in t:
            import re
            m = re.search(r"eliminar nota (.+?)( en (.+))?$", t)
            if m:
                titulo = m.group(1).strip()
                carpeta = m.group(3).strip() if m.group(3) else None
                ok = self.eliminar_nota(titulo, carpeta)
                respuesta = f"Nota '{titulo}' eliminada." if ok else f"No encontré la nota '{titulo}'."
            else:
                respuesta = "¿Qué nota quieres eliminar?"
        elif "buscar nota" in t:
            import re
            m = re.search(r"buscar nota (.+?)( en (.+))?$", t)
            if m:
                palabra = m.group(1).strip()
                carpeta = m.group(3).strip() if m.group(3) else None
                resultados = self.buscar_notas(palabra, carpeta)
                if resultados:
                    respuesta = "Notas encontradas: " + ", ".join([f"'{ti}' (carpeta: {c})" for ti, c in resultados])
                else:
                    respuesta = "No se encontraron notas con ese término."
            else:
                respuesta = "¿Qué palabra quieres buscar en las notas?"
        elif "crear carpeta" in t:
            import re
            m = re.search(r"crear carpeta (.+)$", t)
            if m:
                carpeta = m.group(1).strip()
                os.makedirs(self.ruta_notas(carpeta), exist_ok=True)
                respuesta = f"Carpeta '{carpeta}' creada."
            else:
                respuesta = "¿Cómo se llama la carpeta?"

        else:
            respuesta = 'Comando recibido: ' + texto

        self.chat_signal.emit(respuesta, 'sistema')
        try:
            hablar(respuesta)
        except Exception:
            pass

    # ========= Helpers Notas (GUI) =========
    def carpeta_actual(self) -> Optional[str]:
        if self.carpeta_combo.count() == 0:
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

    # ========= Helpers Notas (FS) =========
    def ruta_notas(self, carpeta: Optional[str] = None) -> str:
        base = os.path.join(PROJECT_DIR, 'notas')
        return os.path.join(base, carpeta) if carpeta else base

    def ruta_nota(self, titulo: str, carpeta: Optional[str] = None) -> str:
        nombre = f"{titulo}.txt"
        return os.path.join(self.ruta_notas(carpeta), nombre)

    def guardar_nota(self, titulo: str, contenido: str, carpeta: Optional[str] = None) -> None:
        ruta = self.ruta_nota(titulo, carpeta)
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write(contenido)

    def leer_nota(self, titulo: str, carpeta: Optional[str] = None) -> Optional[str]:
        ruta = self.ruta_nota(titulo, carpeta)
        if not os.path.exists(ruta):
            return None
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return None

    def eliminar_nota(self, titulo: str, carpeta: Optional[str] = None) -> bool:
        ruta = self.ruta_nota(titulo, carpeta)
        if os.path.exists(ruta):
            try:
                os.remove(ruta)
                return True
            except Exception:
                return False
        return False

    def buscar_notas(self, palabra: str, carpeta: Optional[str] = None):
        resultados = []
        palabra_l = palabra.lower()
        base = self.ruta_notas()
        carpetas = [carpeta] if carpeta else [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))]
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

    # ========= Calendario =========
    def abrir_calendario(self) -> None:
        try:
            from src.calendario_widget import CalendarioEventos  # type: ignore
            eventos_dir = os.path.join(PROJECT_DIR, 'resumenes')
            os.makedirs(eventos_dir, exist_ok=True)
            eventos_path = os.path.join(eventos_dir, 'eventos.json')
            dlg = QDialog(self)
            dlg.setWindowTitle("Calendario de eventos")
            lay = QVBoxLayout(dlg)
            calw = CalendarioEventos(eventos_path, parent=dlg)
            lay.addWidget(calw)
            dlg.setLayout(lay)
            dlg.resize(520, 560)
            dlg.exec_()
        except Exception as e:
            self.chat_signal.emit(f"No se pudo abrir el calendario: {e}", 'sistema')

    # ========= Hotword placeholder =========
    def iniciar_escucha_hey_asistente(self) -> None:
        if self.escuchando:
            return
        self.escuchando = True
        def _loop():
            import time
            while self.escuchando:
                time.sleep(1.0)
        self._escucha_thread = threading.Thread(target=_loop, daemon=True)
        self._escucha_thread.start()

    # ========= Drive placeholder =========
    def sincronizar_con_drive(self, modo: str = 'ambos') -> None:
        try:
            from googleapiclient.discovery import build  # type: ignore
            from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
            self.chat_signal.emit("Sincronización de Drive requiere credenciales; configúralas para activar esta función.", 'sistema')
        except Exception:
            self.chat_signal.emit("Drive no está configurado en este equipo.", 'sistema')


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = AsistenteMain()
    win.show()
    sys.exit(app.exec_())
                
