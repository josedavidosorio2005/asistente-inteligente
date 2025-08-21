# Asistente Inteligente (UI PyQt)

Estructura principal

Para ejecutar
```powershell
python -m pip install -r requirements.txt
python asistente_mic.py
```

Notas
```markdown
Guía rápida de contribución
- Estilo: preferir Python 3.11+, tipado donde sea posible y docstrings.
- Estructura: la UI actual vive en `asistente_mic.py`. Nuevos módulos van en `src/assistant_app/`.
- Calidad: ejecutar un chequeo rápido de sintaxis antes de subir cambios:
```powershell
python -m py_compile asistente_mic.py src/**/**/*.py
```
- Datos locales: `notas/`, `resumenes/` y `pantallazos/` están ignorados; se versiona un `.gitkeep` vacío.
