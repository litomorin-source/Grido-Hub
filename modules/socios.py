from pathlib import Path

import pandas as pd


RUTA_BASE = Path("data/base_maestra.xlsx")

COLUMNAS_PROTEGIDAS = {
    "DNI",
    "WhatsApp",
    "Fecha Alta",
    "Última Actualización",
    "Activo",
    "Fecha Baja",
}


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


def preparar_favoritos(favoritos):
    favoritos = favoritos.copy().astype(object)

    columna_email = buscar_columna_email(favoritos)

    favoritos["_EMAIL_NORMALIZADO"] = normalizar_email(
        favoritos[columna_email]
    )

    favoritos = favoritos[
        favoritos["_EMAIL_NORMALIZADO"].str.contains("@", na=False)
    ].copy()

    favoritos = favoritos.drop_duplicates(
        subset="_EMAIL_NORMALIZADO",
        keep="last",
    )

    return favoritos


def convertir_activo(serie):
    return (
        serie.fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        .isin(["true", "1", "sí", "si", "activo"])
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

    if "Activo" in base.columns:
        activos = convertir_activo(base["Activo"])
    else:
        activos = pd.Series(True, index=base.index)

    return int((activos & ~dni_valido).sum())


def crear_base_inicial(favoritos):
    ahora = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")

    base = favoritos.copy().astype(object)

    base["DNI"] = ""
    base["WhatsApp"] = ""
    base["Fecha Alta"] = ahora
    base["Última Actualización"] = ahora
    base["Activo"] = True
    base["Fecha Baja"] = ""

    base = base.drop(
        columns=["_EMAIL_NORMALIZADO"],
        errors="ignore",
    )

    RUTA_BASE.parent.mkdir(parents=True, exist_ok=True)
    base.to_excel(RUTA_BASE, index=False)

    return {
        "socios_actuales": len(base),
        "socios_historicos": len(base),
        "nuevos": len(base),
        "retirados": 0,
        "pendientes_dni": len(base),
    }


def actualizar_base(favoritos):
    favoritos = preparar_favoritos(favoritos)

    if not RUTA_BASE.exists():
        return crear_base_inicial(favoritos)

    ahora = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")

    base = pd.read_excel(
        RUTA_BASE,
        dtype=str,
    ).fillna("")

    # Evita errores al mezclar texto, fechas y booleanos
    base = base.astype(object)

    if "Activo" not in base.columns:
        base["Activo"] = True
    else:
        base["Activo"] = convertir_activo(base["Activo"])

    if "Fecha Baja" not in base.columns:
        base["Fecha Baja"] = ""

    if "DNI" not in base.columns:
        base["DNI"] = ""

    if "WhatsApp" not in base.columns:
        base["WhatsApp"] = ""

    columna_email_base = buscar_columna_email(base)

    base["_EMAIL_NORMALIZADO"] = normalizar_email(
        base[columna_email_base]
    )

    emails_base = set(base["_EMAIL_NORMALIZADO"])
    emails_favoritos = set(favoritos["_EMAIL_NORMALIZADO"])

    emails_nuevos = emails_favoritos - emails_base
    emails_retirados = emails_base - emails_favoritos
    emails_existentes = emails_base & emails_favoritos

    nuevos = favoritos[
        favoritos["_EMAIL_NORMALIZADO"].isin(emails_nuevos)
    ].copy().astype(object)

    if not nuevos.empty:
        nuevos["DNI"] = ""
        nuevos["WhatsApp"] = ""
        nuevos["Fecha Alta"] = ahora
        nuevos["Última Actualización"] = ahora
        nuevos["Activo"] = True
        nuevos["Fecha Baja"] = ""

    favoritos_indexado = favoritos.set_index("_EMAIL_NORMALIZADO")
    base_indexada = base.set_index("_EMAIL_NORMALIZADO")

    columnas_actualizables = [
        columna
        for columna in favoritos.columns
        if columna not in COLUMNAS_PROTEGIDAS
        and columna != "_EMAIL_NORMALIZADO"
    ]

    for columna in columnas_actualizables:
        if columna not in base_indexada.columns:
            base_indexada[columna] = ""

        for email in emails_existentes:
            base_indexada.at[email, columna] = (
                favoritos_indexado.at[email, columna]
            )

    for email in emails_existentes:
        base_indexada.at[email, "Activo"] = True
        base_indexada.at[email, "Fecha Baja"] = ""

    retirados_nuevos = 0

    for email in emails_retirados:
        estaba_activo = bool(base_indexada.at[email, "Activo"])

        if estaba_activo:
            retirados_nuevos += 1
            base_indexada.at[email, "Fecha Baja"] = ahora

        base_indexada.at[email, "Activo"] = False

    base = base_indexada.reset_index().astype(object)

    if not nuevos.empty:
        base = pd.concat(
            [base, nuevos],
            ignore_index=True,
            sort=False,
        ).astype(object)

    base["Última Actualización"] = ahora

    pendientes = contar_pendientes_dni(base)

    socios_actuales = int(
        convertir_activo(base["Activo"]).sum()
    )

    base = base.drop(
        columns=["_EMAIL_NORMALIZADO"],
        errors="ignore",
    )

    base.to_excel(RUTA_BASE, index=False)

    return {
        "socios_actuales": socios_actuales,
        "socios_historicos": len(base),
        "nuevos": len(nuevos),
        "retirados": retirados_nuevos,
        "pendientes_dni": pendientes,
    }