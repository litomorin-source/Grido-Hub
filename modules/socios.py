from pathlib import Path

import pandas as pd


RUTA_BASE = Path("data/base_maestra.xlsx")

COLUMNAS_PROTEGIDAS = {
    "DNI",
    "WhatsApp",
    "Fecha Alta",
    "Última Actualización",
    "En Favoritos Actual",
    "Última vez en Favoritos",
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


def convertir_booleano(serie):
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

    return int((~dni_valido).sum())


def obtener_ultima_actualizacion(base):
    if "Última Actualización" not in base.columns:
        return "-"

    fechas = pd.to_datetime(
        base["Última Actualización"],
        errors="coerce",
    ).dropna()

    if fechas.empty:
        return "-"

    return fechas.max().strftime("%d/%m/%Y %H:%M")


def obtener_resumen_base():
    if not RUTA_BASE.exists():
        return {
            "existe": False,
            "socios_historicos": 0,
            "en_favoritos_actual": 0,
            "pendientes_dni": 0,
            "ultima_actualizacion": "-",
        }

    base = pd.read_excel(
        RUTA_BASE,
        dtype=str,
    ).fillna("")

    historicos = len(base)

    if "En Favoritos Actual" in base.columns:
        en_favoritos = int(
            convertir_booleano(base["En Favoritos Actual"]).sum()
        )
    elif "Activo" in base.columns:
        en_favoritos = int(
            convertir_booleano(base["Activo"]).sum()
        )
    else:
        en_favoritos = historicos

    return {
        "existe": True,
        "socios_historicos": historicos,
        "en_favoritos_actual": en_favoritos,
        "pendientes_dni": contar_pendientes_dni(base),
        "ultima_actualizacion": obtener_ultima_actualizacion(base),
    }


def crear_base_inicial(favoritos):
    ahora = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")

    base = favoritos.copy().astype(object)

    base["DNI"] = ""
    base["WhatsApp"] = ""
    base["Fecha Alta"] = ahora
    base["Última Actualización"] = ahora
    base["En Favoritos Actual"] = True
    base["Última vez en Favoritos"] = ahora

    base = base.drop(
        columns=["_EMAIL_NORMALIZADO"],
        errors="ignore",
    )

    RUTA_BASE.parent.mkdir(parents=True, exist_ok=True)
    base.to_excel(RUTA_BASE, index=False)

    return {
        "socios_historicos": len(base),
        "en_favoritos_actual": len(base),
        "nuevos": len(base),
        "ya_no_aparecen": 0,
        "pendientes_dni": len(base),
        "ultima_actualizacion": obtener_ultima_actualizacion(base),
    }


def actualizar_base(favoritos):
    favoritos = preparar_favoritos(favoritos)

    if not RUTA_BASE.exists():
        return crear_base_inicial(favoritos)

    ahora = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")

    base = pd.read_excel(
        RUTA_BASE,
        dtype=str,
    ).fillna("").astype(object)

    if "En Favoritos Actual" not in base.columns:
        if "Activo" in base.columns:
            base["En Favoritos Actual"] = convertir_booleano(
                base["Activo"]
            )
        else:
            base["En Favoritos Actual"] = True

    if "Última vez en Favoritos" not in base.columns:
        base["Última vez en Favoritos"] = ""

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
    emails_existentes = emails_base & emails_favoritos
    emails_que_ya_no_aparecen = emails_base - emails_favoritos

    nuevos = favoritos[
        favoritos["_EMAIL_NORMALIZADO"].isin(emails_nuevos)
    ].copy().astype(object)

    if not nuevos.empty:
        nuevos["DNI"] = ""
        nuevos["WhatsApp"] = ""
        nuevos["Fecha Alta"] = ahora
        nuevos["Última Actualización"] = ahora
        nuevos["En Favoritos Actual"] = True
        nuevos["Última vez en Favoritos"] = ahora

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
        base_indexada.at[email, "En Favoritos Actual"] = True
        base_indexada.at[email, "Última vez en Favoritos"] = ahora

    for email in emails_que_ya_no_aparecen:
        base_indexada.at[email, "En Favoritos Actual"] = False

    base = base_indexada.reset_index().astype(object)

    if not nuevos.empty:
        base = pd.concat(
            [base, nuevos],
            ignore_index=True,
            sort=False,
        ).astype(object)

    base["Última Actualización"] = ahora

    base = base.drop(
        columns=[
            "_EMAIL_NORMALIZADO",
            "Activo",
            "Fecha Baja",
        ],
        errors="ignore",
    )

    base.to_excel(RUTA_BASE, index=False)

    return {
        "socios_historicos": len(base),
        "en_favoritos_actual": int(
            convertir_booleano(base["En Favoritos Actual"]).sum()
        ),
        "nuevos": len(nuevos),
        "ya_no_aparecen": len(emails_que_ya_no_aparecen),
        "pendientes_dni": contar_pendientes_dni(base),
        "ultima_actualizacion": obtener_ultima_actualizacion(base),
    }