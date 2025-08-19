from PyQt5.QtWidgets import QWidget, QCalendarWidget, QVBoxLayout, QLabel, QListWidget, QPushButton, QDialog, QLineEdit, QHBoxLayout
from PyQt5.QtCore import QDate
import os
import json

class CalendarioEventos(QWidget):
    def __init__(self, eventos_path, parent=None):
        super().__init__(parent)
        self.eventos_path = eventos_path
        self.setWindowTitle("Calendario de eventos")
        self.setStyleSheet("background:#181a20;color:#e0e0e0;")
        layout = QVBoxLayout()
        self.calendario = QCalendarWidget()
        self.calendario.setStyleSheet("background:#23272f;color:#e0e0e0;border-radius:8px;")
        self.calendario.selectionChanged.connect(self.mostrar_eventos_dia)
        layout.addWidget(self.calendario)
        self.label = QLabel("Eventos del día:")
        layout.addWidget(self.label)
        self.lista = QListWidget()
        self.lista.setStyleSheet("background:#23272f;color:#e0e0e0;")
        layout.addWidget(self.lista)
        # Botón para crear evento en la fecha seleccionada
        btn_crear = QPushButton("Crear evento en este día")
        btn_crear.setStyleSheet("background:#23272f;color:#e0e0e0;font-size:15px;border-radius:8px;padding:6px;margin:4px;")
        btn_crear.clicked.connect(self.crear_evento_en_fecha)
        layout.addWidget(btn_crear)
        self.setLayout(layout)
        self.mostrar_eventos_dia()

    def crear_evento_en_fecha(self):
        fecha = self.calendario.selectedDate().toString('yyyy-MM-dd')
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Nuevo evento para {fecha}")
        dlg.setStyleSheet("background:#23272f;color:#fff;")
        lay = QVBoxLayout()
        label = QLabel(f"Evento para {fecha}:")
        lay.addWidget(label)
        input_ev = QLineEdit()
        input_ev.setPlaceholderText("Descripción del evento")
        lay.addWidget(input_ev)
        btns = QHBoxLayout()
        btn_ok = QPushButton("Crear")
        btn_cancel = QPushButton("Cancelar")
        btns.addWidget(btn_ok)
        btns.addWidget(btn_cancel)
        lay.addLayout(btns)
        dlg.setLayout(lay)
        def crear():
            evento = input_ev.text()
            if evento:
                eventos = self.cargar_eventos()
                eventos.append({'evento': evento, 'fecha': fecha})
                with open(self.eventos_path, 'w', encoding='utf-8') as f:
                    json.dump(eventos, f, ensure_ascii=False, indent=2)
                self.mostrar_eventos_dia()
                dlg.accept()
        btn_ok.clicked.connect(crear)
        btn_cancel.clicked.connect(dlg.reject)
        dlg.exec_()

    def cargar_eventos(self):
        if not os.path.exists(self.eventos_path):
            return []
        with open(self.eventos_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def mostrar_eventos_dia(self):
        fecha = self.calendario.selectedDate().toString('yyyy-MM-dd')
        eventos = self.cargar_eventos()
        self.lista.clear()
        encontrados = [ev for ev in eventos if ev['fecha'] == fecha]
        if encontrados:
            for ev in encontrados:
                self.lista.addItem(ev['evento'])
        else:
            self.lista.addItem("Sin eventos para este día")
