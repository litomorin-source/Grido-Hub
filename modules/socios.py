import os
import pandas as pd

RUTA_BASE = "data/base_maestra.xlsx"


def actualizar_base(favoritos):

    # Primera vez
    if not os.path.exists(RUTA_BASE):

        base = favoritos.copy()

        base["DNI"] = ""
        base["WhatsApp"] = ""
        base["Fecha Alta"] = pd.Timestamp.now()
        base["Última Actualización"] = pd.Timestamp.now()

        os.makedirs("data", exist_ok=True)
        base.to_excel(RUTA_BASE, index=False)

        return {
            "socios": len(base),
            "nuevos": len(base),
            "pendientes_dni": len(base)
        }

    # Si ya existe

    base = pd.read_excel(RUTA_BASE)

    # Buscar la columna Email automáticamente

    col_base = next(c for c in base.columns if "mail" in c.lower() or "email" in c.lower())
    col_fav = next(c for c in favoritos.columns if "mail" in c.lower() or "email" in c.lower())

    emails_base = set(
        base[col_base]
        .astype(str)
        .str.lower()
        .str.strip()
    )

    nuevos = favoritos[
        ~favoritos[col_fav]
        .astype(str)
        .str.lower()
        .str.strip()
        .isin(emails_base)
    ].copy()

    if len(nuevos) > 0:

        nuevos["DNI"] = ""
        nuevos["WhatsApp"] = ""
        nuevos["Fecha Alta"] = pd.Timestamp.now()
        nuevos["Última Actualización"] = pd.Timestamp.now()

        base = pd.concat(
            [base, nuevos],
            ignore_index=True
        )

    base["Última Actualización"] = pd.Timestamp.now()

    base.to_excel(RUTA_BASE, index=False)

    pendientes = (base["DNI"] == "").sum()

    return {
        "socios": len(base),
        "nuevos": len(nuevos),
        "pendientes_dni": int(pendientes)
    }