from modules.dni_batch import (
    esta_ejecutando,
    iniciar_lote,
    obtener_estado,
    solicitar_detencion,
)
from modules.dni_repository import (
    contar_por_procesar,
    contar_sin_dni,
)
from modules.chrome_manager import (
    abrir_chrome_grido,
    abrir_club_grido,
)


def obtener_cantidad_pendientes():
    return contar_sin_dni()


def obtener_cantidad_por_procesar():
    return contar_por_procesar()


def iniciar_navegador():
    driver = abrir_chrome_grido()
    abrir_club_grido(driver)
    return driver


def iniciar_procesamiento(cantidad):
    if cantidad == "Todos":
        limite = None
    else:
        limite = int(cantidad)

    return iniciar_lote(limite=limite)


def detener_procesamiento():
    solicitar_detencion()


def obtener_estado_procesamiento():
    return obtener_estado()


def procesamiento_activo():
    return esta_ejecutando()
