from io import BytesIO
from pathlib import Path

import pandas as pd


RUTA_BASE = Path("data/base_maestra.xlsx")

MESES = {
    "Enero": 1,
    "Febrero": 2,
    "Marzo": 3,
    "Abril": 4,
    "Mayo": 5,
    "Junio": 6,
    "Julio": 7,
    "Agosto": 8,
    "Septiembre": 9,
    "Octubre": 10,
    "Noviembre": 11,
    "Diciembre": 12,
}


def _validar_columnas(base):
    requeridas = {
        "CustomerFirstName",
        "CustomerLastName",
        "Email",
        "BirthDate",
        "DNI",
    }

    faltantes = requeridas - set(base.columns)

    if faltantes:
        columnas = ", ".join(sorted(faltantes))

        raise RuntimeError(
            "La Base Maestra no tiene estas columnas: "
            f"{columnas}"
        )


def _leer_fechas_nacimiento(serie):
    """
    BirthDate viene normalmente como mes/día/año.

    También admite celdas que Excel haya convertido
    directamente a fecha.
    """
    fechas = pd.to_datetime(
        serie,
        format="%m/%d/%Y",
        errors="coerce",
    )

    pendientes = fechas.isna()

    if pendientes.any():
        fechas_alternativas = pd.to_datetime(
            serie.loc[pendientes],
            errors="coerce",
            dayfirst=False,
        )

        fechas.loc[pendientes] = fechas_alternativas

    return fechas


def _limpiar_texto(valor):
    return " ".join(
        str(valor or "")
        .strip()
        .split()
    )


def _armar_nombre(nombre, apellido):
    return _limpiar_texto(
        f"{_limpiar_texto(nombre)} "
        f"{_limpiar_texto(apellido)}"
    )


def _dni_para_excel(valor):
    """
    Exporta el identificador como número cuando contiene
    únicamente dígitos, igual que el archivo modelo de Grido.
    """
    texto = "".join(
        caracter
        for caracter in str(valor or "")
        if caracter.isdigit()
    )

    if not texto:
        return None

    return int(texto)


def _crear_excel(segmento):
    salida = BytesIO()

    with pd.ExcelWriter(
        salida,
        engine="openpyxl",
    ) as writer:
        segmento.to_excel(
            writer,
            sheet_name="Hoja1",
            index=False,
        )

        hoja = writer.book["Hoja1"]

        hoja.column_dimensions["A"].width = 14
        hoja.column_dimensions["B"].width = 32
        hoja.column_dimensions["C"].width = 38

        for celda in hoja[1]:
            celda.font = celda.font.copy(bold=True)

    salida.seek(0)

    return salida.getvalue()


def segmentar_cumpleanios(nombre_mes):
    if nombre_mes not in MESES:
        raise ValueError(
            f"Mes inválido: {nombre_mes}"
        )

    if not RUTA_BASE.exists():
        raise RuntimeError(
            "No existe data/base_maestra.xlsx."
        )

    base = (
        pd.read_excel(
            RUTA_BASE,
            dtype=str,
        )
        .fillna("")
    )

    _validar_columnas(base)

    fechas = _leer_fechas_nacimiento(
        base["BirthDate"]
    )

    mes_numero = MESES[nombre_mes]

    seleccion = base.loc[
        fechas.dt.month.eq(mes_numero)
    ].copy()

    segmento = pd.DataFrame(
        {
            "DNI": seleccion["DNI"].apply(
                _dni_para_excel
            ),
            "NOMBRE": [
                _armar_nombre(nombre, apellido)
                for nombre, apellido in zip(
                    seleccion["CustomerFirstName"],
                    seleccion["CustomerLastName"],
                )
            ],
            "EMAIL": (
                seleccion["Email"]
                .astype(str)
                .str.strip()
            ),
        }
    )

    completos = (
        segmento["DNI"].notna()
        & segmento["EMAIL"].ne("")
    )

    exportable = (
        segmento.loc[
            completos,
            ["DNI", "NOMBRE", "EMAIL"],
        ]
        .drop_duplicates(
            subset=["DNI", "EMAIL"],
            keep="first",
        )
        .reset_index(drop=True)
    )

    omitidos = int((~completos).sum())

    return {
        "mes": nombre_mes,
        "encontrados": len(segmento),
        "exportados": len(exportable),
        "omitidos": omitidos,
        "segmento": exportable,
        "excel": _crear_excel(exportable),
        "nombre_archivo": (
            f"Segmento_Cumpleanios_{nombre_mes}.xlsx"
        ),
    }
