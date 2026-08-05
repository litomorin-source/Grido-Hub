import re
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

WAIT_SECONDS = 20
DELAY_AFTER_SEARCH = 2.0
NUMERO_SOCIOS_GLOBAL = "6219864"


def es_visible(elemento):
    try:
        return elemento.is_displayed() and elemento.size.get("width", 0) > 5 and elemento.size.get("height", 0) > 5
    except Exception:
        return False


def obtener_campo_busqueda(driver):
    espera = WebDriverWait(driver, WAIT_SECONDS)
    espera.until(lambda navegador: len(navegador.find_elements(By.XPATH, "//input")) > 0)

    rutas = [
        "//input[contains(@placeholder,'Buscar') or contains(@placeholder,'buscar')]",
        "//input[@type='search']",
        "//input[@type='text' and not(@disabled)]",
    ]

    for ruta in rutas:
        for elemento in driver.find_elements(By.XPATH, ruta):
            if es_visible(elemento):
                return elemento

    raise RuntimeError("No encontré el campo visible de búsqueda.")


def preparar_pagina(driver):
    obtener_campo_busqueda(driver)
    time.sleep(0.5)


def escribir_email(driver, campo, email):
    email = str(email).strip()
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", campo)
    campo.click()
    campo.send_keys(Keys.CONTROL, "a")
    campo.send_keys(Keys.BACKSPACE)
    campo.send_keys(email)

    driver.execute_script("""
        const campo = arguments[0];
        const valor = arguments[1];
        campo.focus();
        campo.value = valor;
        campo.dispatchEvent(new Event('input', {bubbles: true}));
        campo.dispatchEvent(new Event('change', {bubbles: true}));
    """, campo, email)


def texto_tabla(driver):
    partes = []

    for fila in driver.find_elements(By.XPATH, "//table//tbody/tr"):
        if not es_visible(fila):
            continue

        texto = fila.text.strip()

        if texto:
            partes.append(texto)

    return "\n".join(partes)


def apretar_lupa(driver, campo):
    texto_anterior = texto_tabla(driver)

    rutas = [
        "//input[contains(@placeholder,'Buscar') or contains(@placeholder,'buscar')]/following::button[1]",
        "//input[contains(@placeholder,'Buscar') or contains(@placeholder,'buscar')]/following::*[contains(@class,'input-group-addon')][1]",
        "//*[self::button or self::a or self::span or self::div][.//i[contains(@class,'search') or contains(@class,'glyphicon-search') or contains(@class,'fa-search')]]",
    ]

    for ruta in rutas:
        for elemento in driver.find_elements(By.XPATH, ruta):
            if not es_visible(elemento):
                continue

            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", elemento)
                time.sleep(DELAY_AFTER_SEARCH)

                if texto_tabla(driver) != texto_anterior:
                    return
            except Exception:
                pass

    campo.send_keys(Keys.ENTER)
    time.sleep(DELAY_AFTER_SEARCH)


def normalizar_email(valor):
    return str(valor or "").strip().lower()


def extraer_dni_celdas(textos):
    for texto in textos:
        coincidencia = re.search(
            r"(?:DNI|Documento|Nro\.?\s*Documento|Número\s*de\s*documento|Numero\s*de\s*documento)\D{0,80}(\d+)",
            str(texto),
            flags=re.IGNORECASE,
        )

        if coincidencia:
            numero = coincidencia.group(1)

            if numero != NUMERO_SOCIOS_GLOBAL:
                return numero

    for texto in textos:
        coincidencia = re.fullmatch(r"\D*(\d+)\D*", str(texto or "").strip())

        if coincidencia:
            numero = coincidencia.group(1)

            if numero != NUMERO_SOCIOS_GLOBAL:
                return numero

    return ""


def extraer_dni_tabla(driver, email):
    email_buscado = normalizar_email(email)
    filas_visibles = []

    for fila in driver.find_elements(By.XPATH, "//table//tbody/tr"):
        if not es_visible(fila):
            continue

        celdas = fila.find_elements(By.XPATH, "./td")
        textos = [celda.text.strip() for celda in celdas]
        fila_completa = " | ".join(textos)

        if not fila_completa:
            continue

        filas_visibles.append(textos)

        if email_buscado in normalizar_email(fila_completa):
            return extraer_dni_celdas(textos)

    if len(filas_visibles) == 1:
        return extraer_dni_celdas(filas_visibles[0])

    return ""


def esperar_resultado(driver, email, tabla_anterior):
    email_buscado = normalizar_email(email)
    limite = time.time() + WAIT_SECONDS
    mensajes_vacios = ["no se encontraron", "ningún dato", "ningun dato", "no hay datos", "0 registros"]

    while time.time() < limite:
        cuerpo = driver.find_element(By.TAG_NAME, "body").text
        cuerpo_normalizado = normalizar_email(cuerpo)
        tabla_actual = texto_tabla(driver)

        if email_buscado in cuerpo_normalizado:
            return

        if any(mensaje in cuerpo_normalizado for mensaje in mensajes_vacios):
            return

        if tabla_actual != tabla_anterior:
            return

        time.sleep(0.3)


def buscar_dni_por_email(driver, email):
    preparar_pagina(driver)
    campo = obtener_campo_busqueda(driver)
    tabla_anterior = texto_tabla(driver)

    escribir_email(driver, campo, email)
    apretar_lupa(driver, campo)
    esperar_resultado(driver, email, tabla_anterior)

    dni = extraer_dni_tabla(driver, email)

    return {
        "email": email,
        "encontrado": bool(dni),
        "dni": dni,
    }
