import json
import os
import threading
import time
import uuid
from pathlib import Path

from modules.chrome_manager import (
    abrir_chrome_grido,
    abrir_club_grido,
)
from modules.dni_repository import (
    cargar_base,
    contar_por_procesar,
    contar_sin_dni,
    encontrar_columna_email,
    guardar_resultado,
    obtener_indices_por_procesar,
)
from modules.dni_search import buscar_dni_por_email
from modules.socios import crear_backup


RUTA_ESTADO = Path("data/dni_job_status.json")
RUTA_DETENER = Path("data/dni_stop.flag")

_HILO = None
_BLOQUEO = threading.Lock()
_BLOQUEO_ESTADO = threading.RLock()


def _estado_vacio():
    return {
        "job_id": "",
        "estado": "inactivo",
        "mensaje": "",
        "total": 0,
        "procesados": 0,
        "encontrados": 0,
        "sin_dni": 0,
        "errores": 0,
        "pendientes_restantes": contar_sin_dni(),
        "por_procesar": contar_por_procesar(),
        "email_actual": "",
        "inicio": "",
        "fin": "",
        "segundos": 0,
        "log": [],
    }


def _guardar_estado(estado):
    """
    Guarda el estado de forma segura.

    Usa un archivo temporal único para evitar que Streamlit y el hilo
    de procesamiento intenten reemplazar el mismo .tmp al mismo tiempo.
    Además reintenta si Windows o el antivirus bloquean el archivo
    durante una fracción de segundo.
    """
    with _BLOQUEO_ESTADO:
        RUTA_ESTADO.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        contenido = json.dumps(
            estado,
            ensure_ascii=False,
            indent=2,
        )

        temporal = RUTA_ESTADO.parent / (
            f".{RUTA_ESTADO.stem}_"
            f"{threading.get_ident()}_"
            f"{uuid.uuid4().hex}.tmp"
        )

        temporal.write_text(
            contenido,
            encoding="utf-8",
        )

        ultimo_error = None

        for intento in range(10):
            try:
                os.replace(
                    temporal,
                    RUTA_ESTADO,
                )
                return

            except PermissionError as error:
                ultimo_error = error
                time.sleep(0.05 * (intento + 1))

        temporal.unlink(missing_ok=True)

        raise RuntimeError(
            "Windows bloqueó momentáneamente el archivo de estado. "
            "Volvé a iniciar el lote."
        ) from ultimo_error


def obtener_estado():
    global _HILO

    with _BLOQUEO_ESTADO:
        if not RUTA_ESTADO.exists():
            estado = _estado_vacio()
            _guardar_estado(estado)
            return estado

        try:
            estado = json.loads(
                RUTA_ESTADO.read_text(
                    encoding="utf-8"
                )
            )

        except Exception:
            # Puede coincidir con una escritura del hilo.
            # Esperamos brevemente y reintentamos antes de reconstruirlo.
            time.sleep(0.05)

            try:
                estado = json.loads(
                    RUTA_ESTADO.read_text(
                        encoding="utf-8"
                    )
                )

            except Exception:
                estado = _estado_vacio()
                _guardar_estado(estado)
                return estado

    hilo_vivo = (
        _HILO is not None
        and _HILO.is_alive()
    )

    if estado.get("estado") in {
        "ejecutando",
        "deteniendo",
    } and not hilo_vivo:
        estado["estado"] = "detenido"
        estado["mensaje"] = (
            "La ejecución se interrumpió. "
            "Podés continuar desde el siguiente pendiente."
        )
        estado["pendientes_restantes"] = contar_sin_dni()
        estado["por_procesar"] = contar_por_procesar()
        _guardar_estado(estado)

    return estado


def esta_ejecutando():
    estado = obtener_estado()

    return estado.get("estado") in {
        "ejecutando",
        "deteniendo",
    }


def solicitar_detencion():
    RUTA_DETENER.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    RUTA_DETENER.write_text(
        "detener",
        encoding="utf-8",
    )

    estado = obtener_estado()

    if estado.get("estado") == "ejecutando":
        estado["estado"] = "deteniendo"
        estado["mensaje"] = (
            "Detención solicitada. "
            "Se detendrá al terminar el socio actual."
        )
        _guardar_estado(estado)


def _detencion_solicitada():
    return RUTA_DETENER.exists()


def _limpiar_detencion():
    RUTA_DETENER.unlink(
        missing_ok=True
    )


def _agregar_log(estado, item):
    log = estado.get("log", [])
    log.append(item)

    estado["log"] = log[-100:]


def _actualizar_tiempo(
    estado,
    inicio_monotonic,
):
    estado["segundos"] = round(
        time.monotonic() - inicio_monotonic,
        1,
    )


def _procesar(limite, job_id):
    inicio_monotonic = time.monotonic()
    inicio_texto = time.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    try:
        base = cargar_base()

        if base.empty:
            raise RuntimeError(
                "No existe la Base Maestra."
            )

        base = base.copy()
        columna_email = encontrar_columna_email(base)

        indices = obtener_indices_por_procesar(
            base,
            limite=limite,
        )

        estado = _estado_vacio()
        estado.update(
            {
                "job_id": job_id,
                "estado": "ejecutando",
                "mensaje": "Procesando DNI...",
                "total": len(indices),
                "inicio": inicio_texto,
            }
        )
        _guardar_estado(estado)

        if not indices:
            estado["estado"] = "finalizado"
            estado["mensaje"] = (
                "No hay socios pendientes para procesar."
            )
            estado["fin"] = time.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            _guardar_estado(estado)
            return

        crear_backup()

        driver = abrir_chrome_grido()
        abrir_club_grido(driver)

        for indice in indices:
            if _detencion_solicitada():
                estado["estado"] = "detenido"
                estado["mensaje"] = (
                    "Proceso detenido. "
                    "Podés continuar cuando quieras."
                )
                break

            email = str(
                base.at[indice, columna_email]
            ).strip()

            estado["email_actual"] = email
            estado["mensaje"] = (
                f"Procesando {estado['procesados'] + 1} "
                f"de {estado['total']}"
            )
            _actualizar_tiempo(
                estado,
                inicio_monotonic,
            )
            _guardar_estado(estado)

            item_log = {
                "email": email,
                "estado": "",
                "dni": "",
                "detalle": "",
            }

            try:
                if "@" not in email:
                    raise RuntimeError(
                        "Email inválido."
                    )

                resultado = buscar_dni_por_email(
                    driver,
                    email,
                )

                if resultado["encontrado"]:
                    dni_encontrado = resultado["dni"]

                    guardar_resultado(
                        base,
                        indice,
                        "OK",
                        "DNI encontrado por Grido Hub",
                        dni_encontrado,
                    )

                    item_log["estado"] = "OK"
                    item_log["dni"] = str(
                        dni_encontrado
                    )
                    item_log["detalle"] = (
                        "DNI encontrado"
                    )
                    estado["encontrados"] += 1

                else:
                    guardar_resultado(
                        base,
                        indice,
                        "SIN_DNI",
                        "No se encontró DNI para este email",
                    )

                    item_log["estado"] = "SIN_DNI"
                    item_log["detalle"] = (
                        "No se encontró DNI"
                    )
                    estado["sin_dni"] += 1

            except Exception as error:
                guardar_resultado(
                    base,
                    indice,
                    "ERROR",
                    str(error),
                )

                item_log["estado"] = "ERROR"
                item_log["detalle"] = str(error)
                estado["errores"] += 1

            estado["procesados"] += 1
            estado["pendientes_restantes"] = (
                contar_sin_dni()
            )
            estado["por_procesar"] = (
                contar_por_procesar()
            )

            _agregar_log(
                estado,
                item_log,
            )
            _actualizar_tiempo(
                estado,
                inicio_monotonic,
            )
            _guardar_estado(estado)

        else:
            estado["estado"] = "finalizado"
            estado["mensaje"] = (
                "Lote finalizado correctamente."
            )

        estado["email_actual"] = ""
        estado["fin"] = time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        estado["pendientes_restantes"] = (
            contar_sin_dni()
        )
        estado["por_procesar"] = (
            contar_por_procesar()
        )

        _actualizar_tiempo(
            estado,
            inicio_monotonic,
        )
        _guardar_estado(estado)

    except Exception as error:
        estado = obtener_estado()
        estado["job_id"] = job_id
        estado["estado"] = "error"
        estado["mensaje"] = str(error)
        estado["fin"] = time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        estado["pendientes_restantes"] = (
            contar_sin_dni()
        )
        estado["por_procesar"] = (
            contar_por_procesar()
        )

        _actualizar_tiempo(
            estado,
            inicio_monotonic,
        )

        try:
            _guardar_estado(estado)
        except Exception:
            # Los resultados de la Base Maestra ya fueron guardados.
            # Evitamos que falle todo por no poder actualizar el panel.
            pass

    finally:
        _limpiar_detencion()


def iniciar_lote(limite=None):
    global _HILO

    with _BLOQUEO:
        if (
            _HILO is not None
            and _HILO.is_alive()
        ):
            raise RuntimeError(
                "Ya hay un lote de DNI en ejecución."
            )

        _limpiar_detencion()
        job_id = uuid.uuid4().hex

        _HILO = threading.Thread(
            target=_procesar,
            args=(limite, job_id),
            daemon=True,
            name="grido-hub-dni-batch",
        )
        _HILO.start()

    return job_id
