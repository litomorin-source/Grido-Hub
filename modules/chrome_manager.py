import json
import socket
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


PUERTO_DEBUG = 9222
DIRECCION_DEBUG = f"127.0.0.1:{PUERTO_DEBUG}"

CARPETA_PERFIL = (
    Path.home()
    / "GridoHub"
    / "chrome_profile"
)

URL_CLUB_GRIDO = (
    "https://gestion.clubgrido.com.ar:4430/"
    "Customer/CustomerViewLimited"
)


def encontrar_chrome():
    posibles_rutas = [
        Path(
            r"C:\Program Files\Google\Chrome"
            r"\Application\chrome.exe"
        ),
        Path(
            r"C:\Program Files (x86)\Google\Chrome"
            r"\Application\chrome.exe"
        ),
        Path.home()
        / "AppData"
        / "Local"
        / "Google"
        / "Chrome"
        / "Application"
        / "chrome.exe",
    ]

    for ruta in posibles_rutas:
        if ruta.exists():
            return ruta

    raise FileNotFoundError(
        "No encontré Google Chrome instalado."
    )


def chrome_esta_abierto():
    try:
        with socket.create_connection(
            ("127.0.0.1", PUERTO_DEBUG),
            timeout=1,
        ):
            return True
    except OSError:
        return False


def esperar_chrome(segundos=15):
    limite = time.time() + segundos

    while time.time() < limite:
        try:
            respuesta = urlopen(
                f"http://127.0.0.1:"
                f"{PUERTO_DEBUG}/json/version",
                timeout=1,
            )

            datos = json.loads(
                respuesta.read().decode("utf-8")
            )

            if datos.get("webSocketDebuggerUrl"):
                return True

        except Exception:
            pass

        time.sleep(0.5)

    return False


def abrir_chrome_grido():
    CARPETA_PERFIL.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not chrome_esta_abierto():
        chrome = encontrar_chrome()

        argumentos = [
            str(chrome),
            f"--remote-debugging-port={PUERTO_DEBUG}",
            f"--user-data-dir={CARPETA_PERFIL}",
            "--profile-directory=Default",
            "--start-maximized",
            "--no-first-run",
            "--no-default-browser-check",
            URL_CLUB_GRIDO,
        ]

        subprocess.Popen(
            argumentos,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        if not esperar_chrome():
            raise RuntimeError(
                "Chrome abrió, pero Grido Hub "
                "no pudo conectarse."
            )

    return conectar_chrome_grido()


def conectar_chrome_grido():
    if not chrome_esta_abierto():
        raise RuntimeError(
            "El Chrome de Grido Hub no está abierto."
        )

    options = Options()
    options.debugger_address = DIRECCION_DEBUG

    driver = webdriver.Chrome(
        options=options
    )

    return driver


def abrir_pestana(driver, url):
    driver.switch_to.new_window("tab")
    driver.get(url)


def abrir_club_grido(driver):
    urls_abiertas = []

    for identificador in driver.window_handles:
        driver.switch_to.window(identificador)
        urls_abiertas.append(driver.current_url)

    if not any(
        "gestion.clubgrido.com.ar" in url
        for url in urls_abiertas
    ):
        abrir_pestana(driver, URL_CLUB_GRIDO)

    return driver