from pathlib import Path

import pandas as pd

from modules.chrome_manager import (
    abrir_chrome_grido,
    abrir_club_grido,
)


RUTA_BASE = Path(
    "data/base_maestra.xlsx"
)


def obtener_pendientes():
    if not RUTA_BASE.exists():
        return pd.DataFrame()

    base = pd.read_excel(
        RUTA_BASE,
        dtype=str,
    ).fillna("")

    if "DNI" not in base.columns:
        base["DNI"] = ""

    dni_limpio = (
        base["DNI"]
        .astype(str)
        .str.replace(
            r"\D",
            "",
            regex=True,
        )
        .str.strip()
    )

    dni_valido = dni_limpio.str.len().isin(
        [7, 8]
    )

    return base.loc[
        ~dni_valido
    ].copy()


def obtener_cantidad_pendientes():
    return len(
        obtener_pendientes()
    )


def iniciar_navegador():
    driver = abrir_chrome_grido()
    abrir_club_grido(driver)

    return driver