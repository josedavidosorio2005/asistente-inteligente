import sys
import os
import threading
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QDialog, QLineEdit, QComboBox
from PyQt5.QtGui import QPainter, QBrush, QPen, QColor
from PyQt5.QtCore import Qt, QTimer, QRectF, pyqtSignal

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
        # Fondo degradado
        grad = QBrush(QColor(80,0,120), Qt.SolidPattern)
        painter.fillRect(rect, QBrush(QColor(80,0,120)))
        grad2 = QBrush(QColor(180,0,255,120), Qt.RadialGradientPattern)
        painter.setBrush(grad2)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(rect.center(), rect.width()//2, rect.height()//2)
        # Círculo animado
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(255,0,255), 5)
        painter.setPen(pen)
        r = QRectF(rect.center().x()-80, rect.center().y()-80, 160, 160)
        painter.drawArc(r, self.animacion*16, 270*16)
        # Micrófono (simple SVG-like)
        painter.setPen(QPen(QColor(255,255,255), 4))
        painter.setBrush(Qt.NoBrush)
        cx, cy = rect.center().x(), rect.center().y()
        painter.drawEllipse(cx-30, cy-40, 60, 80)
        painter.drawLine(cx, cy+40, cx, cy+70)
        painter.drawArc(cx-25, cy+60, 50, 20, 0, 180*16)


class AsistenteMain(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Asistente Inteligente - Voz")
        self.setGeometry(200, 100, 360, 600)
        self.setStyleSheet("background:#181a20;")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        self.microfono = MicrofonoWidget(self)
        layout.addWidget(self.microfono)
        self.label = QLabel("Pulsa el micrófono para hablar")
        self.label.setStyleSheet("color:#e0e0e0;font-size:18px;")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        self.btn_micro = QPushButton()
        self.btn_micro.setFixedSize(120,120)
        self.btn_micro.setStyleSheet("border-radius:60px;background:#23272f;")
        self.btn_micro.setIconSize(self.btn_micro.size())
        self.btn_micro.setText("")
        self.btn_micro.clicked.connect(self.accion_microfono)
        layout.addWidget(self.btn_micro, alignment=Qt.AlignCenter)
        # Botones de funciones
        btn_style = "background:#23272f;color:#e0e0e0;font-size:16px;border-radius:8px;padding:8px;margin:4px;"
        self.btn_evento = QPushButton("Crear Evento")
        self.btn_evento.setStyleSheet(btn_style)
        self.btn_evento.clicked.connect(self.crear_evento_gui)
        layout.addWidget(self.btn_evento)
        self.btn_editar = QPushButton("Editar Evento")
        self.btn_editar.setStyleSheet(btn_style)
        self.btn_editar.clicked.connect(self.editar_evento_gui)
        layout.addWidget(self.btn_editar)
        self.btn_eliminar = QPushButton("Eliminar Evento")
        self.btn_eliminar.setStyleSheet(btn_style)
        self.btn_eliminar.clicked.connect(self.eliminar_evento_gui)
        layout.addWidget(self.btn_eliminar)
        self.btn_hoy = QPushButton("Ver eventos de hoy")
        self.btn_hoy.setStyleSheet(btn_style)
        self.btn_hoy.clicked.connect(lambda: self.consultar_eventos_gui('hoy'))
        layout.addWidget(self.btn_hoy)
        self.btn_semana = QPushButton("Ver eventos de la semana")
        self.btn_semana.setStyleSheet(btn_style)
        self.btn_semana.clicked.connect(lambda: self.consultar_eventos_gui('semana'))
        layout.addWidget(self.btn_semana)
        self.btn_calendario = QPushButton("Ver Calendario")
        self.btn_calendario.setStyleSheet(btn_style)
        self.btn_calendario.clicked.connect(self.mostrar_calendario)
        layout.addWidget(self.btn_calendario)
        central.setLayout(layout)
        self.setCentralWidget(central)

    def mostrar_calendario(self):
        from src.calendario_widget import CalendarioEventos
        eventos_path = os.path.join(os.path.dirname(__file__), 'resumenes', 'eventos.json')
        self.calendario_win = CalendarioEventos(eventos_path)
        self.calendario_win.show()

    def accion_microfono(self):
        self.label.setText("Escuchando...")
        def run_voz():
            texto = escuchar_comando()
            if texto:
                self.label.setText(f"Comando: {texto}")
                # Procesar comandos por voz
                comando = texto.lower()
                if "crear evento" in comando:
                    self.crear_evento_gui()
                    hablar("¿Qué evento y fecha deseas agregar?")
                elif "ver eventos de hoy" in comando:
                    self.consultar_eventos_gui('hoy')
                    hablar("Mostrando eventos de hoy")
                elif "ver eventos de la semana" in comando:
                    self.consultar_eventos_gui('semana')
                    hablar("Mostrando eventos de la semana")
                elif "editar evento" in comando:
                    self.editar_evento_gui()
                    hablar("¿Qué evento deseas editar?")
                elif "eliminar evento" in comando:
                    self.eliminar_evento_gui()
                    hablar("¿Qué evento deseas eliminar?")
                else:
                    hablar(f"Comando recibido: {texto}")
            else:
                self.label.setText("No se entendió el comando")
        threading.Thread(target=run_voz, daemon=True).start()

    def crear_evento_gui(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Nuevo evento")
        dlg.setStyleSheet("background:#23272f;color:#fff;")
        lay = QVBoxLayout()
        label = QLabel("Describe el evento y la fecha (ej: Reunión 2025-08-15):")
        lay.addWidget(label)
        input_ev = QLineEdit()
        lay.addWidget(input_ev)
        btn_ok = QPushButton("Crear")
        lay.addWidget(btn_ok)
        dlg.setLayout(lay)
        def crear():
            texto = input_ev.text()
            partes = texto.rsplit(' ', 1)
            if len(partes) == 2:
                evento, fecha = partes
                EVENTOS_PATH = os.path.join(os.path.dirname(__file__), 'resumenes', 'eventos.json')
                if os.path.exists(EVENTOS_PATH):
                    with open(EVENTOS_PATH, 'r', encoding='utf-8') as f:
                        eventos = json.load(f)
                else:
                    eventos = []
                eventos.append({'evento': evento, 'fecha': fecha})
                with open(EVENTOS_PATH, 'w', encoding='utf-8') as f:
                    json.dump(eventos, f, ensure_ascii=False, indent=2)
                self.label.setText("Evento creado correctamente")
                # Si el calendario visual está abierto, refrescarlo
                if hasattr(self, 'calendario_win') and self.calendario_win.isVisible():
                    self.calendario_win.mostrar_eventos_dia()
                dlg.accept()
            else:
                self.label.setText("Formato incorrecto. Usa: <evento> <YYYY-MM-DD>")
        btn_ok.clicked.connect(crear)
        dlg.exec_()

    def editar_evento_gui(self):
        EVENTOS_PATH = os.path.join(os.path.dirname(__file__), 'resumenes', 'eventos.json')
        if not os.path.exists(EVENTOS_PATH):
            self.label.setText("No hay eventos para editar.")
            return
        with open(EVENTOS_PATH, 'r', encoding='utf-8') as f:
            eventos = json.load(f)
        if not eventos:
            self.label.setText("No hay eventos para editar.")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Editar evento")
        dlg.setStyleSheet("background:#23272f;color:#fff;")
        lay = QVBoxLayout()
        combo = QComboBox()
        combo.addItems([f"{i+1}. {ev['evento']} - {ev['fecha']}" for i, ev in enumerate(eventos)])
        lay.addWidget(QLabel("Selecciona evento a editar:"))
        lay.addWidget(combo)
        input_ev = QLineEdit()
        input_ev.setPlaceholderText("Nuevo texto del evento")
        lay.addWidget(input_ev)
        input_fecha = QLineEdit()
        input_fecha.setPlaceholderText("Nueva fecha (YYYY-MM-DD)")
        lay.addWidget(input_fecha)
        btn_ok = QPushButton("Guardar cambios")
        lay.addWidget(btn_ok)
        dlg.setLayout(lay)
        def guardar():
            idx = combo.currentIndex()
            nuevo_evento = input_ev.text()
            nueva_fecha = input_fecha.text()
            if nuevo_evento and nueva_fecha:
                eventos[idx]['evento'] = nuevo_evento
                eventos[idx]['fecha'] = nueva_fecha
                with open(EVENTOS_PATH, 'w', encoding='utf-8') as f:
                    json.dump(eventos, f, ensure_ascii=False, indent=2)
                self.label.setText("Evento editado correctamente")
                # Refrescar calendario visual si está abierto
                if hasattr(self, 'calendario_win') and self.calendario_win.isVisible():
                    self.calendario_win.mostrar_eventos_dia()
                dlg.accept()
            else:
                self.label.setText("Edición cancelada o datos incompletos")
        btn_ok.clicked.connect(guardar)
        dlg.exec_()

    def eliminar_evento_gui(self):
        EVENTOS_PATH = os.path.join(os.path.dirname(__file__), 'resumenes', 'eventos.json')
        if not os.path.exists(EVENTOS_PATH):
            self.label.setText("No hay eventos para eliminar.")
            return
        with open(EVENTOS_PATH, 'r', encoding='utf-8') as f:
            eventos = json.load(f)
        if not eventos:
            self.label.setText("No hay eventos para eliminar.")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Eliminar evento")
        dlg.setStyleSheet("background:#23272f;color:#fff;")
        lay = QVBoxLayout()
        combo = QComboBox()
        combo.addItems([f"{i+1}. {ev['evento']} - {ev['fecha']}" for i, ev in enumerate(eventos)])
        lay.addWidget(QLabel("Selecciona evento a eliminar:"))
        lay.addWidget(combo)
        btn_ok = QPushButton("Eliminar")
        lay.addWidget(btn_ok)
        dlg.setLayout(lay)
        def eliminar():
            idx = combo.currentIndex()
            eventos.pop(idx)
            with open(EVENTOS_PATH, 'w', encoding='utf-8') as f:
                json.dump(eventos, f, ensure_ascii=False, indent=2)
            self.label.setText("Evento eliminado correctamente")
            # Refrescar calendario visual si está abierto
            if hasattr(self, 'calendario_win') and self.calendario_win.isVisible():
                self.calendario_win.mostrar_eventos_dia()
            dlg.accept()
        btn_ok.clicked.connect(eliminar)
        dlg.exec_()

    def consultar_eventos_gui(self, modo):
        EVENTOS_PATH = os.path.join(os.path.dirname(__file__), 'resumenes', 'eventos.json')
        if not os.path.exists(EVENTOS_PATH):
            self.label.setText("No hay eventos guardados.")
            return
        with open(EVENTOS_PATH, 'r', encoding='utf-8') as f:
            eventos = json.load(f)
        hoy = datetime.now().date()
        if modo == 'hoy':
            encontrados = [ev for ev in eventos if ev['fecha'] == str(hoy)]
            if encontrados:
                texto = f"Eventos para hoy {hoy}:\n" + '\n'.join([f"- {ev['evento']} ({ev['fecha']})" for ev in encontrados])
                self.label.setText(texto)
            else:
                self.label.setText("No tienes eventos para hoy.")
        elif modo == 'semana':
            fin_semana = hoy + timedelta(days=6-hoy.weekday())
            encontrados = [ev for ev in eventos if hoy <= datetime.strptime(ev['fecha'], '%Y-%m-%d').date() <= fin_semana]
            if encontrados:
                texto = f"Eventos para esta semana ({hoy} a {fin_semana}):\n" + '\n'.join([f"- {ev['evento']} ({ev['fecha']})" for ev in encontrados])
                self.label.setText(texto)
            else:
                self.label.setText("No tienes eventos para esta semana.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = AsistenteMain()
    ventana.show()
    sys.exit(app.exec_())
