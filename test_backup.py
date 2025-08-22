from src import db
from pathlib import Path

def test_backup_and_integrity(tmp_path):
    # Crear datos
    db.note_upsert('BKNote','contenido','')
    db.event_create('BKEvt','2099-01-01','08:00')
    assert db.integrity_check() is True
    # Exportar
    path = db.backup_export(str(tmp_path / 'export.json'))
    assert path and Path(path).exists()
    # Modificar y luego reimportar (debería mantener o fusionar sin error)
    db.note_upsert('BKNote','contenido mod','')
    assert db.backup_import(path) is True
    # Búsqueda FTS (puede fallback)
    res = db.note_search_fts('BKNote')
    assert any(r['title']=='BKNote' for r in res)
