"""
CRUD de clientes y verificación de acceso.
"""
from datetime import datetime, timedelta

from db.connection import get_db_connection
from db.nanoid_util import generar_codigo_qr_unico
from db.repo_disciplinas import cliente_tiene_disciplina_activa, obtener_disciplinas_de_cliente


# ========== Crear / actualizar / eliminar ==========
# (sin cambios en estas funciones, se mantienen igual)

def crear_cliente(nombre, apellido=None, telefono=None, vencimiento=None):
    codigo_qr = generar_codigo_qr_unico()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO clientes
               (nombre, apellido, telefono, vencimiento, codigo_qr)
               VALUES (?, ?, ?, ?, ?)""",
            (nombre, apellido, telefono, vencimiento, codigo_qr),
        )
        return cursor.lastrowid


def actualizar_cliente(cliente_id, nombre=None, apellido=None, telefono=None, vencimiento=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        campos, valores = [], []
        if nombre is not None:
            campos.append("nombre = ?")
            valores.append(nombre)
        if apellido is not None:
            campos.append("apellido = ?")
            valores.append(apellido)
        if telefono is not None:
            campos.append("telefono = ?")
            valores.append(telefono)
        if vencimiento is not None:
            campos.append("vencimiento = ?")
            valores.append(vencimiento)
        if campos:
            valores.append(cliente_id)
            cursor.execute(
                f"UPDATE clientes SET {', '.join(campos)} WHERE id = ?", valores
            )
            return True
        return False


def eliminar_cliente(cliente_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
        return cursor.rowcount > 0


# ========== Lookups ==========
def get_all_clientes():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clientes")
        return cursor.fetchall()


def get_cliente_por_id(cliente_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,))
        cliente = cursor.fetchone()
        return dict(cliente) if cliente else None


def get_cliente_por_codigo_qr(codigo_qr):
    if not codigo_qr:
        return None
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM clientes WHERE codigo_qr = ?", (codigo_qr,)
        )
        cliente = cursor.fetchone()
        return dict(cliente) if cliente else None


# ========== Verificación de acceso (original, solo vencimiento) ==========
def cliente_tiene_acceso(cliente_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id FROM clientes
            WHERE id = ?
            AND (vencimiento IS NULL OR vencimiento >= date('now'))
        """,
            (cliente_id,),
        )
        return cursor.fetchone() is not None


def cliente_tiene_acceso_por_codigo(codigo_qr):
    cliente = get_cliente_por_codigo_qr(codigo_qr)
    if not cliente:
        return False, None
    return cliente_tiene_acceso(cliente["id"]), cliente


# ========== NUEVA: Verificación completa (vencimiento + disciplina) ==========
def verificar_acceso_completo(codigo_qr):
    """
    Verifica:
    1. Que el cliente exista.
    2. Que su vencimiento sea hoy o futuro (o NULL).
    3. Si el cliente tiene disciplinas asignadas, que al menos una esté activa
       en el momento actual.
    Si no tiene disciplinas, solo se exige el vencimiento (acceso libre).
    Devuelve: (permitido: bool, mensaje: str, cliente_id: int|None, disciplina_nombre: str|None)
    """
    cliente = get_cliente_por_codigo_qr(codigo_qr)
    if not cliente:
        return False, f"QR no reconocido: {codigo_qr}", None, None

    cliente_id = cliente["id"]
    nombre = cliente["nombre"]
    vencimiento = cliente.get("vencimiento") or "Sin fecha"

    # 1. Verificar vencimiento
    if not cliente_tiene_acceso(cliente_id):
        return False, f"ACCESO DENEGADO — {nombre} (vencido: {vencimiento})", cliente_id, None

    # 2. Obtener disciplinas del cliente
    disciplinas = obtener_disciplinas_de_cliente(cliente_id)
    if not disciplinas:
        # Sin disciplinas: acceso libre (solo vencimiento)
        return True, f"ACCESO PERMITIDO — {nombre} (vence: {vencimiento})", cliente_id, None

    # 3. Verificar si alguna disciplina está activa
    tiene_activa, nombre_disciplina = cliente_tiene_disciplina_activa(cliente_id)
    if tiene_activa:
        return True, f"ACCESO PERMITIDO — {nombre} ({nombre_disciplina})", cliente_id, nombre_disciplina
    else:
        return False, f"ACCESO DENEGADO — {nombre} (ninguna disciplina activa)", cliente_id, None


# ========== Listados de vencimientos ==========
def obtener_vencimientos_proximos(dias=7):
    limite = (datetime.now().date() + timedelta(days=dias)).isoformat()
    hoy = datetime.now().date().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM clientes
            WHERE vencimiento IS NOT NULL
            AND vencimiento BETWEEN ? AND ?
            ORDER BY vencimiento ASC
        """,
            (hoy, limite),
        )
        return [dict(row) for row in cursor.fetchall()]


def obtener_clientes_vencidos():
    hoy = datetime.now().date().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM clientes
            WHERE vencimiento IS NOT NULL
            AND vencimiento < ?
            ORDER BY vencimiento DESC
        """,
            (hoy,),
        )
        return [dict(row) for row in cursor.fetchall()]