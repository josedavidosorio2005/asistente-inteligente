# Asistente Inteligente

Asistente de escritorio (PyQt5) con chat, voz, calendario y notas. Migrado de almacenamiento JSON/archivos a SQLite para mayor robustez.

## Ejecutar
```powershell
python -m pip install -r requirements.txt
python asistente_mic.py
```

## Componentes
- `asistente_mic.py`: ventana principal (chat, voz, notas, recordatorios, alertas).
- `src/db.py`: capa SQLite (migración + limpieza legacy).
- `src/calendario.py`: API de calendario.
- `src/calendario_widget.py`: widget de gestión de eventos.
- `data/app.db`: base de datos (autocreada).

## Migración a SQLite
Primera ejecución crea `data/app.db` y migra:
1. Eventos de `resumenes/eventos.json`.
2. Notas de la carpeta `notas/` (archivos .txt).
3. Muestra un mensaje único en el chat.
4. Comando `/limpiar_legacy` renombra archivos/carpetas legacy:
	- `resumenes/eventos.json` → `resumenes/eventos.legacy.json`
	- `notas/` → `notas_legacy/`

### Esquema
```
events(id, title, date, time, completed, UNIQUE(title,date,time))
notes(id, title, content, folder, updated_at, UNIQUE(title,folder))
```
`time` y `folder` usan "" para representar vacío (no NULL) y simplificar UNIQUE.

## Backup rápido
Copiar `data/app.db` (suficiente). Ejemplo PowerShell:
```powershell
Copy-Item data/app.db backups/app_$(Get-Date -Format 'yyyyMMdd_HHmmss').db
```

## Comandos relevantes
Ver `/ayuda` dentro de la app. Mantenimiento: `/limpiar_legacy`.

## Pruebas
Pruebas básicas en `tests/test_db_basic.py` (eventos semana, búsqueda y CRUD notas).
Ejecutar (si añades pytest):
```powershell
pytest -q
```

## Contribución rápida
- Python 3.11+, tipado y docstrings.
- Nuevos módulos en `src/`.
- Chequeo sintaxis:
```powershell
python -m py_compile asistente_mic.py src/**/*.py
```

## Próximos pasos sugeridos
- Más pruebas (recordatorios / alertas con mocks de tiempo).
- Exportar/Importar backup desde UI.
- Sincronización nube opcional.
