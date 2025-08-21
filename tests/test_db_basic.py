import os, sys
from datetime import date, timedelta
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from src import db, calendario  # type: ignore

def test_event_week_cycle():
    hoy = date.today()
    calendario.crear_evento('EvtTest1', hoy.isoformat(), '08:00')
    calendario.crear_evento('EvtTest2', (hoy + timedelta(days=2)).isoformat(), None)
    evs, msg = calendario.consultar_eventos('semana')
    assert any(e['evento']=='EvtTest1' for e in evs)
    assert any(e['evento']=='EvtTest2' for e in evs)
    calendario.eliminar_evento_por_datos('EvtTest1', hoy.isoformat(), '08:00')
    calendario.eliminar_evento_por_datos('EvtTest2', (hoy + timedelta(days=2)).isoformat(), None)

def test_notes_search_cycle():
    db.note_upsert('NotaUnit', 'contenido prueba buscar', None)
    db.note_upsert('NotaCarpeta', 'algo dentro', 'carpetaX')
    res_all = db.note_search('prueba')
    assert any(t=='NotaUnit' for t,_ in res_all)
    res_folder = db.note_list_folders()
    assert 'carpetaX' in res_folder
    assert db.note_get('NotaUnit', None) == 'contenido prueba buscar'
    assert db.note_delete('NotaUnit', None)
    assert db.note_delete('NotaCarpeta', 'carpetaX')
