"""Capa de acceso a datos SQLite para el asistente.

Crea y gestiona la base de datos local:
 - events (eventos del calendario)
 - notes (notas con carpetas opcionales)

Migra datos legacy desde JSON (eventos.json) y archivos .txt de notas.
"""
from __future__ import annotations
import os, json, sqlite3, threading, time, contextlib, traceback
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / 'data'
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / 'app.db'

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None

EVENTOS_JSON = PROJECT_DIR / 'resumenes' / 'eventos.json'
NOTAS_DIR = PROJECT_DIR / 'notas'
MIGRATION_MSG_FILE = DATA_DIR / 'migration_pending.json'

SCHEMA = [
    # Se usa cadena vacía '' en lugar de NULL para garantizar unicidad simple.
    """CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL DEFAULT '',
        completed INTEGER NOT NULL DEFAULT 0,
        UNIQUE(title, date, time)
    )""",
    """CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        folder TEXT NOT NULL DEFAULT '',
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(title, folder)
    )""",
    # Configuración genérica (clave/valor JSON serializado)
    """CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )""",
    # Meta (versionado del esquema y futuros flags)
    """CREATE TABLE IF NOT EXISTS meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )""",
]

# Índices auxiliares para acelerar consultas por fecha / carpeta.
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_events_date ON events(date)",
    "CREATE INDEX IF NOT EXISTS idx_events_date_time ON events(date,time)",
    "CREATE INDEX IF NOT EXISTS idx_notes_folder ON notes(folder)"
]

LOG_FILE = DATA_DIR / 'db_errors.log'

def _log_error(prefix: str, exc: Exception):
    try:
        with LOG_FILE.open('a', encoding='utf-8') as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {prefix}: {exc}\n")
            f.write(''.join(traceback.format_exception(type(exc), exc, exc.__traceback__)) + '\n')
    except Exception:
        pass

def _init_pragmas(conn: sqlite3.Connection):
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA busy_timeout=5000')
    except Exception as e:
        _log_error('init_pragmas', e)

@contextlib.contextmanager
def transaction():
    """Context manager de transacción (commit/rollback automáticos)."""
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        _log_error('transaction', e)
        raise

def optimize(vacuum: bool = False):
    """Ejecuta ANALYZE y opcional VACUUM para mantenimiento manual."""
    conn = get_conn()
    try:
        conn.execute('ANALYZE')
        if vacuum:
            conn.execute('VACUUM')
    except Exception as e:
        _log_error('optimize', e)

def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is not None:
        return _conn
    with _lock:
        if _conn is None:
            need_migration = not DB_PATH.exists()
            _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, isolation_level=None)
            _conn.row_factory = sqlite3.Row
            _init_pragmas(_conn)
            try:
                for ddl in SCHEMA:
                    _conn.execute(ddl)
                for idx in INDEXES:
                    _conn.execute(idx)
            except sqlite3.OperationalError as e:
                # Si el error es por expresiones prohibidas (versión previa), recrear BD limpia
                if 'expressions prohibited' in str(e).lower():
                    try:
                        _conn.close()
                    except Exception:
                        pass
                    if DB_PATH.exists():
                        DB_PATH.unlink(missing_ok=True)  # type: ignore[arg-type]
                    _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, isolation_level=None)
                    _conn.row_factory = sqlite3.Row
                    _init_pragmas(_conn)
                    for ddl in SCHEMA:
                        _conn.execute(ddl)
                    for idx in INDEXES:
                        _conn.execute(idx)
                else:
                    raise
            if need_migration:
                ev_cnt, note_cnt = _migrate_legacy(_conn)
                try:
                    MIGRATION_MSG_FILE.write_text(json.dumps({
                        'timestamp': int(time.time()),
                        'eventos_migrados': ev_cnt,
                        'notas_migradas': note_cnt,
                        'legacy_renombrado': False
                    }, ensure_ascii=False, indent=2), encoding='utf-8')
                except Exception:
                    pass
            # Migrar config.json si existe y tabla aún vacía
            try:
                _migrate_config_json(_conn)
            except Exception:
                pass
            # Asegurar que todas las tablas existen (por fallos anteriores de creación)
            try:
                for idx in INDEXES:
                    _conn.execute(idx)
            except Exception as e:
                _log_error('indexes_late', e)
            # Aplicar upgrades de esquema (FTS, triggers, etc.)
            try:
                _apply_schema_upgrades(_conn)
            except Exception as e:
                _log_error('schema_upgrade', e)
        return _conn

# ================== SCHEMA VERSIONING & UPGRADES ==================

def _get_schema_version(conn: sqlite3.Connection) -> int:
    try:
        cur = conn.execute("SELECT value FROM meta WHERE key='schema_version'")
        row = cur.fetchone()
        if not row:
            return 0
        return int(row[0])
    except Exception:
        return 0

def _set_schema_version(conn: sqlite3.Connection, version: int):
    try:
        conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version',?)", (str(version),))
    except Exception as e:
        _log_error('set_schema_version', e)

def _apply_schema_upgrades(conn: sqlite3.Connection):
    """Aplica migraciones incrementales. Versión base = 0.

    v1: (implícito) tablas básicas + meta.
    v2: FTS5 para notas (notes_fts) + triggers sincronización.
    """
    version = _get_schema_version(conn)
    target = 2
    if version < 1:
        # Establecer versión inicial si no existía.
        _set_schema_version(conn, 1)
        version = 1
    if version < 2:
        _upgrade_to_v2(conn)
        _set_schema_version(conn, 2)

def _upgrade_to_v2(conn: sqlite3.Connection):
    """Crea FTS5 para notas si está disponible."""
    try:
        # Verificar soporte FTS5
        try:
            conn.execute("SELECT 1 FROM sqlite_master")
            # Intento de crear virtual table (idempotente con IF NOT EXISTS no soportado en FTS5, se captura excepción)
            conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(title, content, folder, content='notes', content_rowid='id')")
        except sqlite3.OperationalError as e:
            if 'fts5' in str(e).lower():
                return  # Sin soporte FTS5, se aborta silenciosamente
            raise
        # Triggers (usar OR REPLACE para evitar duplicados si se recrean)
        conn.execute("CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN INSERT INTO notes_fts(rowid, title, content, folder) VALUES (new.id, new.title, new.content, new.folder); END;")
        conn.execute("CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN INSERT INTO notes_fts(notes_fts, rowid, title, content, folder) VALUES('delete', old.id, old.title, old.content, old.folder); INSERT INTO notes_fts(rowid, title, content, folder) VALUES (new.id, new.title, new.content, new.folder); END;")
        conn.execute("CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN INSERT INTO notes_fts(notes_fts, rowid, title, content, folder) VALUES('delete', old.id, old.title, old.content, old.folder); END;")
    except Exception as e:
        _log_error('upgrade_v2', e)

# ================== UTILIDADES EXTRA ==================

def backup_export(path: str | None = None) -> str | None:
    """Exporta contenido (events, notes, config) a JSON en data/backups.

    Si se provee path, guarda allí; retorna ruta final o None si fallo.
    """
    conn = get_conn()
    try:
        DATA_DIR.mkdir(exist_ok=True)
        backup_dir = DATA_DIR / 'backups'
        backup_dir.mkdir(exist_ok=True)
        if path is None:
            fname = f"backup_{int(time.time())}.json"
            path_obj = backup_dir / fname
        else:
            path_obj = Path(path)
        data = {}
        for tbl in ('events', 'notes', 'config'):
            try:
                cur = conn.execute(f"SELECT * FROM {tbl}")
                cols = [d[0] for d in cur.description]
                data[tbl] = [dict(zip(cols, row)) for row in cur.fetchall()]
            except Exception as e:
                _log_error('backup_export_table_'+tbl, e)
        path_obj.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        return str(path_obj)
    except Exception as e:
        _log_error('backup_export', e)
        return None

def backup_import(path: str) -> bool:
    """Importa datos desde un JSON exportado. No borra datos existentes (INSERT OR IGNORE / REPLACE según caso)."""
    conn = get_conn()
    try:
        content = Path(path).read_text(encoding='utf-8')
        blob = json.loads(content)
        with transaction() as tx:
            for ev in blob.get('events', []):
                try:
                    tx.execute("INSERT OR IGNORE INTO events(title,date,time,completed) VALUES (?,?,?,?)", (
                        ev.get('title',''), ev.get('date',''), ev.get('time','') or '', ev.get('completed',0)))
                except Exception:
                    pass
            for nt in blob.get('notes', []):
                try:
                    tx.execute("INSERT INTO notes(title,content,folder,updated_at) VALUES (?,?,?,?) ON CONFLICT(title,folder) DO UPDATE SET content=excluded.content, updated_at=CURRENT_TIMESTAMP", (
                        nt.get('title',''), nt.get('content',''), nt.get('folder','') or '', nt.get('updated_at','')))
                except Exception:
                    pass
            for cf in blob.get('config', []):
                try:
                    tx.execute("INSERT OR REPLACE INTO config(key,value) VALUES (?,?)", (cf.get('key'), cf.get('value')))
                except Exception:
                    pass
        return True
    except Exception as e:
        _log_error('backup_import', e)
        return False

def integrity_check() -> bool:
    """Ejecuta PRAGMA integrity_check. True si OK."""
    conn = get_conn()
    try:
        cur = conn.execute("PRAGMA integrity_check")
        row = cur.fetchone()
        return bool(row and row[0] == 'ok')
    except Exception as e:
        _log_error('integrity_check', e)
        return False

# ================== BÚSQUEDA FTS ==================

def note_search_fts(term: str, folder: str | None = None, limit: int = 20) -> list[dict]:
    """Busca usando FTS5 si está disponible; fallback silencioso a note_search.

    Retorna lista de dicts con keys: title, folder.
    """
    conn = get_conn()
    try:
        # Verifica que la tabla virtual exista
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notes_fts'")
        if not cur.fetchone():
            # FTS no disponible → fallback
            results = note_search(term, folder)
            return [{'title': t, 'folder': f} for t, f in results]
        match_expr = term.strip()
        if not match_expr:
            return []
        if folder is not None:
            folder = folder or ''
            q = ("SELECT n.title, n.folder FROM notes_fts f JOIN notes n ON n.id = f.rowid "
                 "WHERE notes_fts MATCH ? AND n.folder=? LIMIT ?")
            cur2 = conn.execute(q, (match_expr, folder, limit))
        else:
            q = ("SELECT n.title, n.folder FROM notes_fts f JOIN notes n ON n.id = f.rowid "
                 "WHERE notes_fts MATCH ? LIMIT ?")
            cur2 = conn.execute(q, (match_expr, limit))
        return [{'title': r[0], 'folder': r[1]} for r in cur2.fetchall()]
    except Exception as e:
        _log_error('note_search_fts', e)
        try:
            results = note_search(term, folder)
            return [{'title': t, 'folder': f} for t, f in results]
        except Exception:
            return []

def _migrate_legacy(conn: sqlite3.Connection) -> tuple[int,int]:
    # Migrar eventos
    ev_cnt = 0
    try:
        if EVENTOS_JSON.exists():
            with EVENTOS_JSON.open('r', encoding='utf-8') as f:
                eventos = json.load(f)
            if isinstance(eventos, list):
                for ev in eventos:
                    title = ev.get('evento') or ''
                    date = ev.get('fecha') or ''
                    if not title or not date:
                        continue
                    time = ev.get('hora') or ''
                    completed = 1 if ev.get('completado') else 0
                    try:
                        conn.execute(
                            "INSERT OR IGNORE INTO events(title,date,time,completed) VALUES (?,?,?,?)",
                            (title, date, time, completed)
                        )
                        ev_cnt += 1
                    except Exception:
                        pass
                conn.commit()
    except Exception:
        pass
    # Migrar notas
    note_cnt = 0
    try:
        if NOTAS_DIR.exists():
            for root, _, files in os.walk(NOTAS_DIR):
                for fname in files:
                    if not fname.endswith('.txt'):
                        continue
                    full = Path(root) / fname
                    try:
                        content = full.read_text(encoding='utf-8', errors='ignore')
                    except Exception:
                        continue
                    title = fname[:-4]
                    rel_parent = Path(root).relative_to(NOTAS_DIR)
                    folder = None if str(rel_parent) == '.' else str(rel_parent).replace('\\', '/')
                    try:
                        conn.execute(
                            "INSERT OR IGNORE INTO notes(title, content, folder) VALUES (?,?,?)",
                            (title, content, folder or '')
                        )
                        note_cnt += 1
                    except Exception:
                        pass
            conn.commit()
    except Exception:
        pass
    return ev_cnt, note_cnt

def cleanup_legacy() -> bool:
    """Renombra eventos.json y carpeta notas para evitar confusión post-migración."""
    changed = False
    try:
        if EVENTOS_JSON.exists():
            legacy = EVENTOS_JSON.with_suffix('.legacy.json')
            if not legacy.exists():
                EVENTOS_JSON.rename(legacy)
                changed = True
    except Exception:
        pass
    try:
        if NOTAS_DIR.exists() and NOTAS_DIR.is_dir():
            legacy_dir = PROJECT_DIR / 'notas_legacy'
            if not legacy_dir.exists():
                os.replace(NOTAS_DIR, legacy_dir)
                changed = True
    except Exception:
        pass
    if changed:
        try:
            if MIGRATION_MSG_FILE.exists():
                data = json.loads(MIGRATION_MSG_FILE.read_text(encoding='utf-8'))
            else:
                data = {}
            data['legacy_renombrado'] = True
            MIGRATION_MSG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            pass
    return changed

def consume_migration_message() -> str | None:
    if not MIGRATION_MSG_FILE.exists():
        return None
    try:
        data = json.loads(MIGRATION_MSG_FILE.read_text(encoding='utf-8'))
    except Exception:
        return None
    msg = (f"Migración completada: {data.get('eventos_migrados',0)} eventos y "
           f"{data.get('notas_migradas',0)} notas importados. "
           + ("Legacy renombrado." if data.get('legacy_renombrado') else "Puedes limpiar los archivos legacy."))
    try:
        MIGRATION_MSG_FILE.unlink()
    except Exception:
        pass
    return msg

# === Configuración (clave/valor) ===

CONFIG_JSON_PATH = DATA_DIR / 'config.json'

def _migrate_config_json(conn: sqlite3.Connection) -> None:
    """Migra config.json (si existe) a la tabla config.

    Se realiza solo si la tabla config está vacía.
    Luego renombra el archivo a config.legacy.json para no re‑migrar.
    """
    try:
        cur = conn.execute("SELECT COUNT(*) FROM config")
        if cur.fetchone()[0] > 0:
            return  # Ya hay datos
    except Exception:
        return
    if not CONFIG_JSON_PATH.exists():
        return
    try:
        data = json.loads(CONFIG_JSON_PATH.read_text(encoding='utf-8'))
        if isinstance(data, dict):
            for k, v in data.items():
                try:
                    conn.execute("INSERT OR REPLACE INTO config(key,value) VALUES (?,?)", (k, json.dumps(v, ensure_ascii=False)))
                except Exception:
                    continue
            conn.commit()
        # Renombrar
        legacy = CONFIG_JSON_PATH.with_suffix('.legacy.json')
        if not legacy.exists():
            try:
                CONFIG_JSON_PATH.rename(legacy)
            except Exception:
                pass
    except Exception:
        pass

def config_set(key: str, value) -> bool:
    conn = get_conn()
    try:
        conn.execute("INSERT OR REPLACE INTO config(key,value) VALUES (?,?)", (key, json.dumps(value, ensure_ascii=False)))
        conn.commit()
        return True
    except Exception:
        return False

def config_get(key: str, default=None):
    conn = get_conn()
    try:
        cur = conn.execute("SELECT value FROM config WHERE key=?", (key,))
        row = cur.fetchone()
        if not row:
            return default
        try:
            return json.loads(row[0])
        except Exception:
            return row[0]
    except Exception:
        return default

def config_load_all() -> dict:
    conn = get_conn()
    result = {}
    try:
        cur = conn.execute("SELECT key, value FROM config")
        for k, v in cur.fetchall():
            try:
                result[k] = json.loads(v)
            except Exception:
                result[k] = v
    except Exception:
        pass
    return result

# === API Eventos ===

def event_create(title: str, date: str, time: str | None) -> bool:
    try:
        with transaction() as conn:
            time = time or ''
            conn.execute(
                "INSERT OR IGNORE INTO events(title,date,time,completed) VALUES (?,?,?,0)",
                (title, date, time)
            )
        return True
    except Exception as e:
        _log_error('event_create', e)
        return False

def event_list_day(date: str) -> list[dict]:
    conn = get_conn()
    cur = conn.execute(
        "SELECT * FROM events WHERE date=? ORDER BY IFNULL(time,'99:99'), title", (date,)
    )
    return [dict(r) for r in cur.fetchall()]

def event_list_week(start_date: str, end_date: str) -> list[dict]:
    conn = get_conn()
    cur = conn.execute(
        "SELECT * FROM events WHERE date BETWEEN ? AND ? ORDER BY date, IFNULL(time,'99:99'), title",
        (start_date, end_date)
    )
    return [dict(r) for r in cur.fetchall()]

def event_toggle_complete(title: str, date: str, time: str | None, completed: bool) -> bool:
    try:
        with transaction() as conn:
            time = time or ''
            conn.execute(
                "UPDATE events SET completed=? WHERE title=? AND date=? AND time=?",
                (1 if completed else 0, title, date, time)
            )
        return True
    except Exception as e:
        _log_error('event_toggle_complete', e)
        return False

def event_delete(title: str, date: str, time: str | None) -> int:
    try:
        with transaction() as conn:
            time = time or ''
            cur = conn.execute(
                "DELETE FROM events WHERE title=? AND date=? AND time=?",
                (title, date, time)
            )
            return cur.rowcount
    except Exception as e:
        _log_error('event_delete', e)
        return 0

# === API Notas ===

def note_upsert(title: str, content: str, folder: str | None) -> bool:
    try:
        with transaction() as conn:
            folder = folder or ''
            conn.execute(
                "INSERT INTO notes(title, content, folder) VALUES (?,?,?) ON CONFLICT(title, folder) "
                "DO UPDATE SET content=excluded.content, updated_at=CURRENT_TIMESTAMP",
                (title, content, folder)
            )
        return True
    except Exception as e:
        _log_error('note_upsert', e)
        return False

def note_get(title: str, folder: str | None) -> str | None:
    conn = get_conn()
    folder = folder or ''
    cur = conn.execute(
        "SELECT content FROM notes WHERE title=? AND folder=?",
        (title, folder)
    )
    row = cur.fetchone()
    return row[0] if row else None

def note_delete(title: str, folder: str | None) -> bool:
    folder = folder or ''
    with transaction() as conn:
        cur = conn.execute(
            "DELETE FROM notes WHERE title=? AND folder=?",
            (title, folder)
        )
        return cur.rowcount > 0

def note_search(term: str, folder: str | None = None) -> list[tuple[str, str | None]]:
    conn = get_conn()
    like = f"%{term.lower()}%"
    if folder is not None:
        folder = folder or ''
        cur = conn.execute(
            "SELECT title, folder FROM notes WHERE (LOWER(content) LIKE ? OR LOWER(title) LIKE ?) AND folder=?",
            (like, like, folder)
        )
    else:
        cur = conn.execute(
            "SELECT title, folder FROM notes WHERE LOWER(content) LIKE ? OR LOWER(title) LIKE ?",
            (like, like)
        )
    return [(r[0], r[1]) for r in cur.fetchall()]

def note_list_folders() -> list[str]:
    conn = get_conn()
    cur = conn.execute("SELECT DISTINCT folder FROM notes WHERE folder<>'' ORDER BY folder")
    return [r[0] for r in cur.fetchall()]

def note_list_titles(folder: str | None) -> list[str]:
    conn = get_conn()
    if folder is None:
        cur = conn.execute("SELECT title FROM notes WHERE folder='' ORDER BY title")
    else:
        folder = folder or ''
        cur = conn.execute("SELECT title FROM notes WHERE folder=? ORDER BY title", (folder,))
    return [r[0] for r in cur.fetchall()]
