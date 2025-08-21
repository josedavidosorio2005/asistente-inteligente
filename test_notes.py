"""Prueba e2e opcional y test ligero de notas.

Este archivo ahora contiene:
 - test_notes_basic: prueba rápida sin GUI para pytest.
 - _demo(): flujo completo con GUI (ejecutar manualmente `python test_notes.py`).
"""
from src import db

def test_notes_basic():
    # Prueba CRUD mínima sin inicializar interfaz gráfica pesada.
    db.note_upsert('PyTestNote', 'contenido pytest', None)
    assert db.note_get('PyTestNote', None) == 'contenido pytest'
    assert any('PyTestNote' == t for t in db.note_list_titles(None))
    assert db.note_delete('PyTestNote', None)
    assert db.note_get('PyTestNote', None) is None

def _demo():  # pragma: no cover - demo manual
    from PyQt5.QtWidgets import QApplication
    import sys
    from asistente_mic import AsistenteMain
    app = QApplication(sys.argv)
    win = AsistenteMain()
    titulo_prueba = 'nota_test_e2e'
    contenido = 'Contenido de prueba para verificación'
    win.guardar_nota(titulo_prueba, contenido)
    win.cargar_lista_notas()
    print('Carpetas existentes (DB):', db.note_list_folders())
    print('Notas raíz (DB):', db.note_list_titles(None))
    print('Items en QListWidget:', win.lista_notas.count())
    for i in range(win.lista_notas.count()):
        print('-', win.lista_notas.item(i).text())
    contenido_leido = win.leer_nota(titulo_prueba)
    print('Contenido leído coincide:', contenido_leido == contenido)
    ok = win.eliminar_nota(titulo_prueba)
    print('Eliminada nota_test_e2e:', ok)
    print('Existe tras borrar (DB get):', db.note_get(titulo_prueba, None) is not None)
    win.close()
    app.quit()

if __name__ == '__main__':  # pragma: no cover
    _demo()
