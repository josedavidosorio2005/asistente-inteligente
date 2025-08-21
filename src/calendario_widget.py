"""Widget de calendario con listado/alta de eventos locales.

Persiste en el JSON apuntado por `eventos_path`.
"""
from PyQt5.QtWidgets import (
    QWidget, QCalendarWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QDialog, QLineEdit, QHBoxLayout, QDateEdit, QTimeEdit, QAbstractItemView
)
from PyQt5.QtCore import QDate, Qt, QTime, pyqtSignal
from PyQt5.QtGui import QFont, QColor
import os
import json


class CalendarioEventos(QWidget):
    # Señal: título, fecha, hora (str|None), completado(bool)
    evento_toggle_completado = pyqtSignal(str, str, object, bool)
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
        try:
            self.lista.setSelectionMode(QAbstractItemView.ExtendedSelection)
        except Exception:
            pass
        try:
            self.lista.itemDoubleClicked.connect(self._alternar_completado)
        except Exception:
            pass
        layout.addWidget(self.lista)
        # Acciones de estado
        btn_row = QHBoxLayout()
        btn_hecho = QPushButton("Marcar como completado")
        btn_pend = QPushButton("Marcar como pendiente")
        btn_row.addWidget(btn_hecho)
        btn_row.addWidget(btn_pend)
        layout.addLayout(btn_row)
        try:
            btn_hecho.clicked.connect(lambda: self._cambiar_estado_seleccion(True))
            btn_pend.clicked.connect(lambda: self._cambiar_estado_seleccion(False))
        except Exception:
            pass
        # Botón para crear evento en la fecha seleccionada
        btn_crear = QPushButton("Crear evento en este día")
        btn_crear.clicked.connect(self.crear_evento_en_fecha)
        layout.addWidget(btn_crear)
        self.setLayout(layout)
        self.mostrar_eventos_dia()

    def crear_evento_en_fecha(self) -> None:
        fecha = self.calendario.selectedDate().toString('yyyy-MM-dd')
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Nuevo evento")
        dlg.setStyleSheet("background:#23272f;color:#fff;")
        lay = QVBoxLayout()
        label = QLabel("Descripción del evento:")
        lay.addWidget(label)
        input_ev = QLineEdit()
        input_ev.setPlaceholderText("Descripción del evento")
        lay.addWidget(input_ev)
        # Fecha (día/mes/año)
        lbl_fecha = QLabel("Fecha (día/mes/año):")
        lay.addWidget(lbl_fecha)
        input_fecha = QDateEdit()
        try:
            input_fecha.setCalendarPopup(True)
        except Exception:
            pass
        input_fecha.setDisplayFormat("dd/MM/yyyy")
        input_fecha.setDate(self.calendario.selectedDate())
        lay.addWidget(input_fecha)
        # Hora y minutos
        lbl_hora = QLabel("Hora y minutos:")
        lay.addWidget(lbl_hora)
        input_hora = QTimeEdit()
        input_hora.setDisplayFormat("HH:mm")
        input_hora.setTime(QTime.currentTime())
        lay.addWidget(input_hora)
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
            evento = input_ev.text().strip()
            if not evento:
                return
            d = input_fecha.date().toString('yyyy-MM-dd')
            h = input_hora.time().toString('HH:mm')
            eventos = self.cargar_eventos()
            ev = {'evento': evento, 'fecha': d, 'hora': h, 'completado': False}
            eventos.append(ev)
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
        # Ordenar por hora si existe
        try:
            encontrados.sort(key=lambda e: e.get('hora') or '99:99')
        except Exception:
            pass
        if encontrados:
            for ev in encontrados:
                texto = f"{ev.get('hora','--:--')} - {ev['evento']}" if ev.get('hora') else ev['evento']
                it = QListWidgetItem(texto)
                it.setData(Qt.UserRole, {
                    'evento': ev.get('evento'),
                    'fecha': ev.get('fecha'),
                    'hora': ev.get('hora'),
                    'completado': ev.get('completado', False),
                })
                self._estilizar_item(it, ev.get('completado', False))
                self.lista.addItem(it)
        else:
            self.lista.addItem("Sin eventos para este día")

    def _cambiar_estado_seleccion(self, completado: bool) -> None:
        items = self.lista.selectedItems()
        if not items:
            return
        # Intentar vía API principal por cada ítem; si falla, aplicamos un fallback por lote
        fallbacks: list[tuple[str, str, object]] = []
        for it in items:
            data = it.data(Qt.UserRole) or {}
            titulo = data.get('evento') or ""
            fecha = data.get('fecha') or self.calendario.selectedDate().toString('yyyy-MM-dd')
            hora = data.get('hora')
            try:
                from calendario import marcar_evento_completado
                marcar_evento_completado(titulo, fecha, hora or None, completado)
            except Exception:
                fallbacks.append((titulo, fecha, hora))
            # Emitir señal por cada cambio
            try:
                self.evento_toggle_completado.emit(titulo, fecha, hora, completado)
            except Exception:
                pass
        if fallbacks:
            eventos = self.cargar_eventos()
            for titulo, fecha, hora in fallbacks:
                for ev in eventos:
                    if ev.get('evento') == titulo and ev.get('fecha') == fecha and (ev.get('hora') or None) == (hora or None):
                        ev['completado'] = completado
                        break
            try:
                with open(self.eventos_path, 'w', encoding='utf-8') as f:
                    json.dump(eventos, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
        # Refrescar
        self.mostrar_eventos_dia()

    def _estilizar_item(self, item: QListWidgetItem, completado: bool) -> None:
        f: QFont = item.font()
        f.setStrikeOut(bool(completado))
        item.setFont(f)
        try:
            color = QColor(170, 170, 170) if completado else QColor(230, 232, 255)
            item.setForeground(color)
        except Exception:
            pass

    def _alternar_completado(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.UserRole) or {}
        titulo = data.get('evento')
        fecha = data.get('fecha') or self.calendario.selectedDate().toString('yyyy-MM-dd')
        hora = data.get('hora')
        estado = bool(data.get('completado', False))
        try:
            from calendario import marcar_evento_completado
            marcar_evento_completado(titulo, fecha, hora or None, not estado)
        except Exception:
            # Fallback manual si no existe la función
            eventos = self.cargar_eventos()
            for ev in eventos:
                if ev.get('evento') == titulo and ev.get('fecha') == fecha and (ev.get('hora') or None) == (hora or None):
                    ev['completado'] = not estado
                    break
            try:
                with open(self.eventos_path, 'w', encoding='utf-8') as f:
                    json.dump(eventos, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
        # Emitir señal con el nuevo estado
        try:
            self.evento_toggle_completado.emit(titulo or "", fecha, hora, not estado)
        except Exception:
            pass
        # Refrescar lista
        self.mostrar_eventos_dia()
