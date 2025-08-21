"""Prueba rápida de creación/listado/eliminación de notas usando la capa SQLite.

No interactúa con el antiguo sistema basado en archivos. Ejecutar:
    python test_notes.py
"""
from PyQt5.QtWidgets import QApplication
from asistente_mic import AsistenteMain
from src import db
import sys

app = QApplication(sys.argv)
win = AsistenteMain()

# Crear nota de prueba (en raíz, sin carpeta)
titulo_prueba = 'nota_test_e2e'
contenido = 'Contenido de prueba para verificación'
win.guardar_nota(titulo_prueba, contenido)

# Recargar lista GUI y mostrar títulos recuperados desde DB
win.cargar_lista_notas()

print('Carpetas existentes (DB):', db.note_list_folders())
print('Notas raíz (DB):', db.note_list_titles(None))
print('Items en QListWidget:', win.lista_notas.count())
for i in range(win.lista_notas.count()):
        print('-', win.lista_notas.item(i).text())

# Verificar lectura directa
contenido_leido = win.leer_nota(titulo_prueba)
print('Contenido leído coincide:', contenido_leido == contenido)

# Eliminar la nota y comprobar
ok = win.eliminar_nota(titulo_prueba)
print('Eliminada nota_test_e2e:', ok)
print('Existe tras borrar (DB get):', db.note_get(titulo_prueba, None) is not None)

app.quit()
