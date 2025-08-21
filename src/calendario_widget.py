"""Widget de calendario con listado/alta de eventos usando SQLite (db.py).

Se mantiene compatibilidad superficial con la antigua interfaz pero ya no
escribe en JSON; si existe el JSON se migra por `db.get_conn()`.
"""
from PyQt5.QtWidgets import (
    QWidget, QCalendarWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QDialog, QLineEdit, QHBoxLayout, QDateEdit, QTimeEdit, QAbstractItemView
)
from PyQt5.QtCore import QDate, Qt, QTime, pyqtSignal
from PyQt5.QtGui import QFont, QColor
import os
try:
    from . import db  # type: ignore
except ImportError:
    import db  # type: ignore


class CalendarioEventos(QWidget):
    # Señales:
    # evento_toggle_completado(titulo, fecha, hora, completado)
    # evento_eliminado(titulo, fecha, hora)
    evento_toggle_completado = pyqtSignal(str, str, object, bool)
    evento_eliminado = pyqtSignal(str, str, object)
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
        btn_eliminar = QPushButton("Eliminar seleccionado(s)")
        layout.addWidget(btn_eliminar)
        try:
            btn_eliminar.clicked.connect(self.eliminar_eventos_seleccion)
        except Exception:
            pass
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
            try:
                from calendario import crear_evento
                crear_evento(evento, d, h)
            except Exception:
                try:
                    db.event_create(evento, d, h)
                except Exception:
                    pass
            self.mostrar_eventos_dia()
            dlg.accept()
        btn_ok.clicked.connect(crear)
        btn_cancel.clicked.connect(dlg.reject)
        dlg.exec_()

    def cargar_eventos(self) -> list[dict]:
        # Devuelve eventos de toda la base (año corriente). Optimizable si hiciera falta.
        from datetime import date, timedelta
        hoy = date.today()
        fin = hoy + timedelta(days=365)
        try:
            rows = db.event_list_week(str(hoy), str(fin))
            return [
                {
                    'evento': r['title'],
                    'fecha': r['date'],
                    'hora': r['time'],
                    'completado': bool(r['completed'])
                } for r in rows
            ]
        except Exception:
            return []

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
            try:
                self.evento_toggle_completado.emit(titulo, fecha, hora, completado)
            except Exception:
                pass
        if fallbacks:
            for titulo, fecha, hora in fallbacks:
                try:
                    db.event_toggle_complete(titulo, fecha, hora, completado)
                except Exception:
                    pass
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
            try:
                db.event_toggle_complete(titulo, fecha, hora, not estado)
            except Exception:
                pass
        # Emitir señal con el nuevo estado
        try:
            self.evento_toggle_completado.emit(titulo or "", fecha, hora, not estado)
        except Exception:
            pass
        # Refrescar lista
        self.mostrar_eventos_dia()

    def eliminar_eventos_seleccion(self) -> None:
        """Elimina todos los eventos seleccionados (multi‑selección) y actualiza la lista al instante."""
        items = [it for it in self.lista.selectedItems() if it.data(Qt.UserRole)]
        if not items:
            return
        # Recolectar claves a eliminar
        claves = []  # list[tuple(titulo, fecha, hora|None)]
        for it in items:
            data = it.data(Qt.UserRole) or {}
            titulo = (data.get('evento') or '').strip()
            fecha = (data.get('fecha') or '').strip()
            hora = data.get('hora') or None
            if titulo and fecha:
                claves.append((titulo, fecha, hora))
        if not claves:
            return
        # Cargar todos los eventos
        # Eliminar cada clave vía API/DB
        for (t, f, h) in claves:
            try:
                from calendario import eliminar_evento_por_datos
                eliminar_evento_por_datos(t, f, h)
            except Exception:
                try:
                    db.event_delete(t, f, h)
                except Exception:
                    pass
        # Emitir señal por cada eliminado
        for (t, f, h) in claves:
            try:
                self.evento_eliminado.emit(t, f, h)
            except Exception:
                pass
        # Actualizar UI: eliminar ítems seleccionados sin recargar todo para feedback inmediato
        for it in items:
            row = self.lista.row(it)
            self.lista.takeItem(row)
        # Si quedó vacía, mostrar mensaje
        if self.lista.count() == 0:
            self.lista.addItem("Sin eventos para este día")
