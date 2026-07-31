from pathlib import Path

import pandas as pd


RUTA_BASE = Path("data/base_maestra.xlsx")


def buscar_columna_email(df):
    for columna in df.columns:
        nombre = str(columna).strip().lower()

        if "email" in nombre or "mail" in nombre or "correo" in nombre:
            return columna

    raise ValueError("No encontré una columna de email en el archivo.")


def normalizar_email(serie):
    return (
        serie.fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )


def contar_pendientes_dni(base):
    if "DNI" not in base.columns:
        return len(base)

    dni = (
        base["DNI"]
        .fillna("")
        .astype(str)
        .str.replace(r"\D", "", regex=True)
        .str.strip()
    )

    dni_valido = dni.str.len().isin([7, 8])

    return int((~dni_valido).sum())


def actualizar_base(favoritos):
    favoritos = favoritos.copy()

    columna_email_favoritos = buscar_columna_email(favoritos)

    favoritos["_EMAIL_NORMALIZADO"] = normalizar_email(
        favoritos[columna_email_favoritos]
    )

    favoritos = favoritos[
        favoritos["_EMAIL_NORMALIZADO"].str.contains("@", na=False)
    ].copy()

    favoritos = favoritos.drop_duplicates(
        subset="_EMAIL_NORMALIZADO",
        keep="last"
    )

    ahora = pd.Timestamp.now()

    # Primera carga
    if not RUTA_BASE.exists():
        base = favoritos.copy()

        base["DNI"] = ""
        base["WhatsApp"] = ""
        base["Fecha Alta"] = ahora
        base["Última Actualización"] = ahora

        base = base.drop(
            columns=["_EMAIL_NORMALIZADO"],
            errors="ignore"
        )

        RUTA_BASE.parent.mkdir(parents=True, exist_ok=True)
        base.to_excel(RUTA_BASE, index=False)

        return {
            "socios": len(base),
            "nuevos": len(base),
            "pendientes_dni": len(base),
        }

    # Actualización de base existente
    base = pd.read_excel(
        RUTA_BASE,
        dtype=str
    ).fillna("")

    columna_email_base = buscar_columna_email(base)

    base["_EMAIL_NORMALIZADO"] = normalizar_email(
        base[columna_email_base]
    )

    emails_existentes = set(
        base["_EMAIL_NORMALIZADO"]
    )

    nuevos = favoritos[
        ~favoritos["_EMAIL_NORMALIZADO"].isin(emails_existentes)
    ].copy()

    if not nuevos.empty:
        nuevos["DNI"] = ""
        nuevos["WhatsApp"] = ""
        nuevos["Fecha Alta"] = ahora
        nuevos["Última Actualización"] = ahora

        base = pd.concat(
            [base, nuevos],
            ignore_index=True,
            sort=False
        )

    base["Última Actualización"] = ahora

    pendientes = contar_pendientes_dni(base)

    base = base.drop(
        columns=["_EMAIL_NORMALIZADO"],
        errors="ignore"
    )

    base.to_excel(RUTA_BASE, index=False)

    return {
        "socios": len(base),
        "nuevos": len(nuevos),
        "pendientes_dni": pendientes,
    }