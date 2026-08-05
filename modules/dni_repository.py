from pathlib import Path

import pandas as pd

RUTA_BASE = Path("data/base_maestra.xlsx")


def encontrar_columna_email(base):
    for columna in base.columns:
        nombre = str(columna).strip().lower()

        if "email" in nombre or "mail" in nombre or "correo" in nombre:
            return columna

    raise RuntimeError("No encontré la columna de email.")


def limpiar_dni(valor):
    return "".join(caracter for caracter in str(valor) if caracter.isdigit())


def cargar_base():
    if not RUTA_BASE.exists():
        return pd.DataFrame()

    return pd.read_excel(RUTA_BASE, dtype=str).fillna("").astype(object)


def preparar_columnas_robot(base):
    for columna in ["DNI", "RobotEstado", "RobotDetalle", "Última búsqueda DNI"]:
        if columna not in base.columns:
            base[columna] = ""

    return base


def mascara_dni_encontrado(base):
    if "DNI" not in base.columns:
        return pd.Series(False, index=base.index)

    dni_limpio = base["DNI"].apply(limpiar_dni)
    return dni_limpio.str.len().gt(0)


def obtener_indices_por_procesar(base, limite=None):
    base = preparar_columnas_robot(base)
    dni_encontrado = mascara_dni_encontrado(base)

    estado = (
        base["RobotEstado"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    indices = base.index[
        (~dni_encontrado)
        & (~estado.isin(["OK", "SIN_DNI"]))
    ].tolist()

    if limite is not None:
        indices = indices[: int(limite)]

    return indices


def contar_sin_dni():
    base = cargar_base()

    if base.empty:
        return 0

    return int((~mascara_dni_encontrado(base)).sum())


def contar_por_procesar():
    base = cargar_base()

    if base.empty:
        return 0

    return len(obtener_indices_por_procesar(base))


def guardar_resultado(base, indice, estado, detalle, dni=""):
    base = preparar_columnas_robot(base)

    if dni:
        dni_limpio = limpiar_dni(dni)

        if not dni_limpio:
            raise ValueError("El identificador encontrado no contiene números.")

        base.at[indice, "DNI"] = dni_limpio

    base.at[indice, "RobotEstado"] = estado
    base.at[indice, "RobotDetalle"] = str(detalle)[:500]
    base.at[indice, "Última búsqueda DNI"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")

    base.to_excel(RUTA_BASE, index=False)
