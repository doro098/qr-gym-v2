"""
Bucle principal del control de acceso del gimnasio.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time

from config import DEBOUNCE_SEGUNDOS, PIN_CERRADURA, TIEMPO_CERRADURA
from db.repo_clientes import verificar_acceso_completo
from db.repo_logs import registrar_evento
from hardware.cerradura import ControlCerradura
from hardware.scanner import ScannerQR

LONGITUD_NANOID = 6


def codigo_es_valido(codigo):
    if not codigo:
        return False
    codigo = codigo.strip()
    if len(codigo) != LONGITUD_NANOID:
        return False
    return all(c.isalnum() or c in "_-" for c in codigo)


def procesar_qr(codigo, cerradura):
    if not codigo_es_valido(codigo):
        print(f"❌ QR inválido (no es un NanoId de {LONGITUD_NANOID} chars): {codigo[:60]!r}")
        registrar_evento(
            tipo="ACCESO",
            descripcion=f"QR inválido: {codigo[:60]}",
            resultado="ERROR",
        )
        return

    permitido, mensaje, cliente_id, disciplina = verificar_acceso_completo(codigo.strip())
    print(f"{'✅' if permitido else '⛔'} {mensaje}")
    registrar_evento(
        tipo="ACCESO",
        descripcion=mensaje,
        resultado="EXITO" if permitido else "DENEGADO",
        cliente_id=cliente_id,
        disciplina=disciplina,   # puede ser None
    )
    if permitido:
        cerradura.abrir_cerradura()


def main():
    # (el resto igual)
    print("=" * 50)
    print("  CONTROL DE ACCESO - GIMNASIO (GPIO / HEADLESS)")
    print("  QR basado en NanoId de 6 chars + disciplinas")
    print("=" * 50)
    print(f"GPIO cerradura : {PIN_CERRADURA}")
    print("Para salir presiona Ctrl+C")
    print("-" * 50)

    scanner = ScannerQR()
    cerradura = ControlCerradura(pin=PIN_CERRADURA, tiempo_activacion=TIEMPO_CERRADURA)

    if not scanner.iniciar():
        print("❌ Error con cámara")
        return

    cerradura.conectar()

    ultimo_codigo = ""
    ultimo_tiempo = 0
    escaneos = 0

    try:
        while True:
            codigo = scanner.escanear()
            if codigo:
                ahora = time.time()
                if codigo == ultimo_codigo and ahora - ultimo_tiempo < DEBOUNCE_SEGUNDOS:
                    continue
                ultimo_codigo = codigo
                ultimo_tiempo = ahora
                escaneos += 1
                print(f"\n🎯 Escaneo #{escaneos}")
                procesar_qr(codigo, cerradura)
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n⚠️ Interrumpido")
    finally:
        scanner.cerrar()
        cerradura.desconectar()
        print("✅ Sistema cerrado")


if __name__ == "__main__":
    main()