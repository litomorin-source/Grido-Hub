from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


URL_CLUB_GRIDO = (
    "https://gestion.clubgrido.com.ar:4430/"
    "Customer/CustomerViewLimited"
)


def abrir_chrome():
    """
    Abre un Chrome controlado por Selenium usando un perfil persistente.

    El perfil conserva las cookies y el inicio de sesión de Club Grido.
    """

    profile_dir = (
        Path.home()
        / "ClubGridoRobot"
        / "chrome_profile"
    )

    profile_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    options = Options()

    options.add_argument(
        f"--user-data-dir={profile_dir}"
    )

    options.add_argument(
        "--profile-directory=Default"
    )

    options.add_argument(
        "--start-maximized"
    )

    driver = webdriver.Chrome(
        options=options
    )

    driver.get(URL_CLUB_GRIDO)

    return driver