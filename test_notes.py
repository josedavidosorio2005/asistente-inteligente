from PyQt5.QtWidgets import QApplication
from asistente_mic import AsistenteMain
import os
import sys

app = QApplication(sys.argv)
win = AsistenteMain()
# Crear nota de prueba
win.guardar_nota('nota_test_e2e', 'Contenido de prueba para verificación')
# Cargar lista en la GUI
win.cargar_lista_notas()
# Mostrar resultados en stdout
print('Notas en carpeta:', os.listdir(os.path.join(os.path.dirname(__file__), 'notas')))
print('Items en QListWidget:', win.notes_list.count())
for i in range(win.notes_list.count()):
    print('-', win.notes_list.item(i).text())
# Borrar nota creada para limpieza
ok = win.eliminar_nota('nota_test_e2e')
print('Eliminada nota_test_e2e:', ok)
# Salir
app.quit()
