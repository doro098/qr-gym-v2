"""
Registro y consulta de eventos (tabla logs).
"""
from datetime import datetime

from db.connection import get_db_connection


def registrar_evento(tipo, descripcion, resultado, cliente_id=None, usuario_admin=None, disciplina=None):
    """Registra un evento. Ahora acepta disciplina (nombre)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        fecha = datetime.now().isoformat(sep=" ", timespec="seconds")
        cursor.execute(
            """INSERT INTO logs
               (fecha, tipo, descripcion, resultado, cliente_id, usuario_admin, disciplina)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (fecha, tipo, descripcion, resultado, cliente_id, usuario_admin, disciplina),
        )
        return cursor.lastrowid


def obtener_historial(limite=100):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM logs ORDER BY fecha DESC LIMIT ?", (limite,))
        return [dict(row) for row in cursor.fetchall()]