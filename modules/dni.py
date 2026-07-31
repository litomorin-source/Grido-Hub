from pathlib import Path

import pandas as pd

from modules.chrome_manager import abrir_chrome_grido, abrir_club_grido
from modules.dni_search import buscar_dni_por_email
from modules.socios import crear_backup


RUTA_BASE = Path("data/base_maestra.xlsx")


def encontrar_columna_email(base):
    for columna in base.columns:
        nombre = str(columna).strip().lower()

        if "email" in nombre or "mail" in nombre or "correo" in nombre:
            return columna

    raise RuntimeError("No encontré la columna de email.")


def limpiar_dni(valor):
    return "".join(
        caracter
        for caracter in str(valor)
        if caracter.isdigit()
    )


def obtener_base():
    if not RUTA_BASE.exists():
        return pd.DataFrame()

    return (
        pd.read_excel(RUTA_BASE, dtype=str)
        .fillna("")
        .astype(object)
    )


def obtener_pendientes():
    base = obtener_base()

    if base.empty:
        return base

    if "DNI" not in base.columns:
        base["DNI"] = ""

    dni_limpio = base["DNI"].apply(limpiar_dni)
    dni_valido = dni_limpio.str.len().isin([7, 8])

    return base.loc[~dni_valido].copy()


def obtener_pendientes_para_buscar():
    pendientes = obtener_pendientes()

    if pendientes.empty:
        return pendientes

    if "RobotEstado" not in pendientes.columns:
        pendientes["RobotEstado"] = ""

    estado = (
        pendientes["RobotEstado"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # Los SIN_DNI quedan registrados, pero no se repiten
    # automáticamente en el siguiente lote.
    return pendientes.loc[
        ~estado.isin(["OK", "SIN_DNI"])
    ].copy()


def obtener_cantidad_pendientes():
    return len(obtener_pendientes())


def obtener_cantidad_por_procesar():
    return len(obtener_pendientes_para_buscar())


def iniciar_navegador():
    driver = abrir_chrome_grido()
    abrir_club_grido(driver)
    return driver


def preparar_columnas_robot(base):
    for columna in [
        "DNI",
        "RobotEstado",
        "RobotDetalle",
        "Última búsqueda DNI",
    ]:
        if columna not in base.columns:
            base[columna] = ""

    return base


def guardar_resultado(base, indice, estado, detalle, dni=""):
    base = preparar_columnas_robot(base)

    if dni:
        dni_limpio = limpiar_dni(dni)

        if len(dni_limpio) not in (7, 8):
            raise ValueError(
                "El DNI encontrado no tiene 7 u 8 dígitos."
            )

        base.at[indice, "DNI"] = dni_limpio

    base.at[indice, "RobotEstado"] = estado
    base.at[indice, "RobotDetalle"] = str(detalle)[:500]
    base.at[
        indice,
        "Última búsqueda DNI",
    ] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")

    base.to_excel(RUTA_BASE, index=False)


def procesar_lote(cantidad, callback=None):
    cantidad = max(1, int(cantidad))

    base = obtener_base()

    if base.empty:
        raise RuntimeError("No existe la Base Maestra.")

    base = preparar_columnas_robot(base)
    columna_email = encontrar_columna_email(base)

    dni_limpio = base["DNI"].apply(limpiar_dni)
    dni_valido = dni_limpio.str.len().isin([7, 8])

    estado = (
        base["RobotEstado"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    indices = base.index[
        (~dni_valido)
        & (~estado.isin(["OK", "SIN_DNI"]))
    ].tolist()[:cantidad]

    if not indices:
        return {
            "procesados": 0,
            "encontrados": 0,
            "sin_dni": 0,
            "errores": 0,
            "pendientes_restantes": obtener_cantidad_pendientes(),
            "por_procesar": obtener_cantidad_por_procesar(),
            "resultados": [],
        }

    crear_backup()
    driver = iniciar_navegador()

    resultados = []
    encontrados = 0
    sin_dni = 0
    errores = 0

    total = len(indices)

    for posicion, indice in enumerate(indices, start=1):
        email = str(base.at[indice, columna_email]).strip()

        resultado_fila = {
            "posicion": posicion,
            "total": total,
            "email": email,
            "estado": "",
            "dni": "",
            "detalle": "",
        }

        try:
            if "@" not in email:
                raise RuntimeError("Email inválido.")

            resultado = buscar_dni_por_email(driver, email)

            if resultado["encontrado"]:
                dni_encontrado = limpiar_dni(resultado["dni"])

                guardar_resultado(
                    base,
                    indice,
                    "OK",
                    "DNI encontrado por Grido Hub",
                    dni_encontrado,
                )

                resultado_fila["estado"] = "OK"
                resultado_fila["dni"] = dni_encontrado
                resultado_fila["detalle"] = "DNI encontrado"
                encontrados += 1

            else:
                guardar_resultado(
                    base,
                    indice,
                    "SIN_DNI",
                    "No se encontró DNI para este email",
                )

                resultado_fila["estado"] = "SIN_DNI"
                resultado_fila["detalle"] = "No se encontró DNI"
                sin_dni += 1

        except Exception as error:
            guardar_resultado(
                base,
                indice,
                "ERROR",
                str(error),
            )

            resultado_fila["estado"] = "ERROR"
            resultado_fila["detalle"] = str(error)
            errores += 1

        resultados.append(resultado_fila)

        if callback:
            callback(resultado_fila)

    return {
        "procesados": len(resultados),
        "encontrados": encontrados,
        "sin_dni": sin_dni,
        "errores": errores,
        "pendientes_restantes": obtener_cantidad_pendientes(),
        "por_procesar": obtener_cantidad_por_procesar(),
        "resultados": resultados,
    }
