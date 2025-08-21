"""Widget de calendario con listado/alta de eventos locales.

Persiste en el JSON apuntado por `eventos_path`.
"""
from PyQt5.QtWidgets import QWidget, QCalendarWidget, QVBoxLayout, QLabel, QListWidget, QPushButton, QDialog, QLineEdit, QHBoxLayout
from PyQt5.QtCore import QDate, Qt
import os
import json


class CalendarioEventos(QWidget):
    def __init__(self, eventos_path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.eventos_path = eventos_path
        self.setWindowTitle("Calendario de eventos")
        # Tema neón: fondo oscuro con acentos cian/magenta
        self.setStyleSheet(
            """
            QWidget { background: #0e0f14; color: #e6e8ff; }
            QLabel { color: #b8c1ff; font-weight: 600; }
            QListWidget { background: rgba(10,20,40,0.65); border: 1px solid #6df; border-radius: 12px; padding: 6px; }
            QLineEdit { background: rgba(10,20,40,0.5); color:#fff; border: 1px solid #6df; border-radius:10px; padding:8px; }
            QPushButton { color:#8be9ff; border:1px solid #6df; border-radius:10px; padding:8px 12px; background: transparent; }
            QPushButton:hover { background: rgba(0,255,255,0.08); }
            QPushButton:pressed { background: rgba(255,0,255,0.14); border-color: #f6c; color:#fff; }
            """
        )
        layout = QVBoxLayout()
        self.calendario = QCalendarWidget()
        # Estilos detallados del calendario (cabeceras, celdas, selección)
        self.calendario.setStyleSheet(
            """
            QCalendarWidget { background: rgba(10,20,40,0.55); border: 2px solid #6df; border-radius: 16px; }
            QCalendarWidget QWidget#qt_calendar_navigationbar { background: transparent; }
            QCalendarWidget QToolButton { color:#8be9ff; background: transparent; border:1px solid #6df; border-radius: 8px; padding:4px 8px; }
            QCalendarWidget QToolButton:hover { background: rgba(0,255,255,0.08); }
            QCalendarWidget QToolButton:pressed { background: rgba(255,0,255,0.14); border-color:#f6c; color:#fff; }
            QCalendarWidget QSpinBox { background: rgba(10,20,40,0.5); color:#fff; border:1px solid #6df; border-radius:8px; padding: 2px 6px; }
            QCalendarWidget QAbstractItemView:enabled { color:#e6e8ff; selection-background-color: rgba(102,255,255,0.18); selection-color:#fff; }
            QCalendarWidget QAbstractItemView { outline: 0; }
            QCalendarWidget QWidget { alternate-background-color: rgba(255,0,255,0.06); }
            QCalendarWidget QTableView { gridline-color: rgba(109,223,255,0.25); }
            QCalendarWidget QTableView::item { border-radius: 10px; }
            QCalendarWidget QTableView::item:selected { background: rgba(102,255,255,0.18); color:#fff; }
            QCalendarWidget QTableView::item:hover { background: rgba(255,0,255,0.10); }
            QCalendarWidget QTableView QHeaderView::section { background: transparent; color: #8be9ff; font-weight: 600; border: none; }
            """
        )
        self.calendario.selectionChanged.connect(self.mostrar_eventos_dia)
        layout.addWidget(self.calendario)
        self.label = QLabel("Eventos del día:")
        layout.addWidget(self.label)
        self.lista = QListWidget()
        layout.addWidget(self.lista)
        # Botón para crear evento en la fecha seleccionada
        btn_crear = QPushButton("Crear evento en este día")
        btn_crear.clicked.connect(self.crear_evento_en_fecha)
        layout.addWidget(btn_crear)
        self.setLayout(layout)
        self.mostrar_eventos_dia()

    def crear_evento_en_fecha(self) -> None:
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
        # Mostrar con botones de ventana y maximizado
        try:
            dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
            dlg.showMaximized()
        except Exception:
            dlg.resize(640, 320)
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

    def cargar_eventos(self) -> list[dict]:
        if not os.path.exists(self.eventos_path):
            return []
        with open(self.eventos_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def mostrar_eventos_dia(self) -> None:
        fecha = self.calendario.selectedDate().toString('yyyy-MM-dd')
        eventos = self.cargar_eventos()
        self.lista.clear()
        encontrados = [ev for ev in eventos if ev['fecha'] == fecha]
        if encontrados:
            for ev in encontrados:
                self.lista.addItem(ev['evento'])
        else:
            self.lista.addItem("Sin eventos para este día")
