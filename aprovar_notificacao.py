"""Automação web demonstrativa para fluxo de notificações com Selenium.

Por segurança, o modo padrão é simulação: o script não aprova notificações
nem cadastra ordens de serviço sem a opção --execute.
"""
from __future__ import annotations

import argparse
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from utils import load_notification_ids
from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchFrameException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Settings:
    base_url: str
    notifications_url: str
    username: str
    password: str
    ids_file: Path
    municipality_value: str
    occurrence_type_value: str
    headless: bool
    wait_seconds: int

    @classmethod
    def from_environment(cls) -> "Settings":
        base_url = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
        notifications_url = os.getenv("APP_NOTIFICATIONS_URL", "").strip()
        username = os.getenv("APP_USERNAME", "").strip()
        password = os.getenv("APP_PASSWORD", "")
        missing = [
            name for name, value in (
                ("APP_BASE_URL", base_url),
                ("APP_NOTIFICATIONS_URL", notifications_url),
                ("APP_USERNAME", username),
                ("APP_PASSWORD", password),
                ("MUNICIPALITY_VALUE", os.getenv("MUNICIPALITY_VALUE", "").strip()),
                ("OCCURRENCE_TYPE_VALUE", os.getenv("OCCURRENCE_TYPE_VALUE", "").strip()),
            ) if not value
        ]
        if missing:
            raise ValueError(
                "Configure as variáveis obrigatórias no arquivo .env: "
                + ", ".join(missing)
            )

        return cls(
            base_url=base_url,
            notifications_url=notifications_url,
            username=username,
            password=password,
            ids_file=ROOT / os.getenv("IDS_FILE", "sample_ids.txt"),
            municipality_value=os.environ["MUNICIPALITY_VALUE"].strip(),
            occurrence_type_value=os.environ["OCCURRENCE_TYPE_VALUE"].strip(),
            headless=os.getenv("HEADLESS", "false").lower() in {"1", "true", "yes"},
            wait_seconds=int(os.getenv("WAIT_SECONDS", "15")),
        )


def build_driver(settings: Settings) -> webdriver.Chrome:
    options = Options()
    if settings.headless:
        options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-gpu")
    # Selenium Manager tenta localizar/baixar o driver compatível.
    return webdriver.Chrome(options=options)


class NotificationAutomation:
    def __init__(self, driver: webdriver.Chrome, settings: Settings) -> None:
        self.driver = driver
        self.settings = settings
        self.wait = WebDriverWait(driver, settings.wait_seconds)

    def safe_click(self, element) -> None:
        try:
            element.click()
        except (ElementClickInterceptedException, StaleElementReferenceException):
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", element
            )
            self.driver.execute_script("arguments[0].click();", element)

    def type_with_events(self, element, value: str) -> None:
        element.click()
        element.send_keys(Keys.CONTROL, "a")
        element.send_keys(value)
        self.driver.execute_script(
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
            element,
        )
        element.send_keys(Keys.TAB)

    def login(self) -> None:
        self.driver.get(self.settings.base_url)
        username = self.wait.until(EC.visibility_of_element_located((By.ID, "Login")))
        password = self.driver.find_element(By.ID, "Senha")
        username.clear()
        username.send_keys(self.settings.username)
        password.clear()
        password.send_keys(self.settings.password)
        self.safe_click(self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(., 'Login')]")
        )))
        self.wait.until(lambda d: d.current_url != self.settings.base_url or
                        d.find_elements(By.ID, "MunicipioId"))
        logger.info("Etapa de login enviada.")

    def open_notifications(self) -> None:
        self.driver.get(self.settings.notifications_url)
        self.wait.until(EC.presence_of_element_located((By.ID, "MunicipioId")))
        select = Select(self.driver.find_element(By.ID, "MunicipioId"))
        if select.first_selected_option.get_attribute("value") != self.settings.municipality_value:
            select.select_by_value(self.settings.municipality_value)
            self.driver.execute_script(
                "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
                select._el,
            )

    def search_notification(self, notification_id: str) -> None:
        field = self.wait.until(EC.visibility_of_element_located((By.ID, "NotificacaoId")))
        self.type_with_events(field, notification_id)
        self.safe_click(self.wait.until(EC.element_to_be_clickable(
            (By.ID, "botao-pesquisar")
        )))
        self.wait.until(EC.presence_of_element_located(
            (By.XPATH, "//table//tr[td] | //table//tbody/tr")
        ))
        logger.info("Pesquisa concluída para o ID informado.")

    def find_approval_link(self, notification_id: str):
        # Usa o ID da notificação recebido; não depende de variável global.
        xpath = (
            f"//table//tr[.//td[contains(normalize-space(.), "
            f"{self._xpath_literal(notification_id)})]]"
            "//a[contains(@class, 'notificacao-aprovar') and contains(., 'Aprovar')]"
        )
        try:
            return WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
        except TimeoutException:
            raise TimeoutException(
                "Link de aprovação não encontrado na linha do ID pesquisado."
            )

    @staticmethod
    def _xpath_literal(value: str) -> str:
        """Cria literal XPath seguro para strings com aspas."""
        if "'" not in value:
            return f"'{value}'"
        if '"' not in value:
            return f'"{value}"'
        parts = value.split("'")
        return "concat(" + ', "\'", '.join(f"'{part}'" for part in parts) + ")"

    def approve_notification(self, notification_id: str) -> tuple[str, str | None]:
        parent = self.driver.current_window_handle
        previous_handles = set(self.driver.window_handles)
        self.safe_click(self.find_approval_link(notification_id))

        new_handle = None
        try:
            self.wait.until(lambda d: len(set(d.window_handles) - previous_handles) > 0)
            new_handle = (set(self.driver.window_handles) - previous_handles).pop()
            self.driver.switch_to.window(new_handle)
        except TimeoutException:
            logger.info("A ação não abriu uma nova aba.")

        try:
            self.wait.until(EC.visibility_of_element_located((By.ID, "modal-aprovar")))
            candidates = (
                "//*[@id='modal-aprovar']//button[contains(., 'Confirmar')]",
                "//*[@id='modal-aprovar']//button[contains(., 'Aprovar')]",
                "//*[@id='modal-aprovar']//button[contains(., 'SIM') or contains(., 'Sim')]",
                "//*[@id='modal-aprovar']//button[contains(@class, 'btn-primary')]",
            )
            for xpath in candidates:
                buttons = self.driver.find_elements(By.XPATH, xpath)
                if buttons and buttons[0].is_displayed() and buttons[0].is_enabled():
                    self.safe_click(buttons[0])
                    break
            self.wait.until(EC.invisibility_of_element_located((By.ID, "modal-aprovar")))
        except TimeoutException:
            logger.info("Modal de confirmação não foi exibido ou já foi fechado.")

        return parent, new_handle

    def find_occurrence_select(self):
        """Procura o seletor de ocorrência na página atual, abas e iframes."""
        original_handle = self.driver.current_window_handle
        handles = list(self.driver.window_handles)

        for handle in handles:
            try:
                self.driver.switch_to.window(handle)
                self.driver.switch_to.default_content()
                try:
                    return self.wait.until(EC.visibility_of_element_located(
                        (By.ID, "tipoOcorrenciaId")
                    ))
                except TimeoutException:
                    pass

                for frame in self.driver.find_elements(By.TAG_NAME, "iframe"):
                    try:
                        self.driver.switch_to.default_content()
                        self.driver.switch_to.frame(frame)
                        return WebDriverWait(self.driver, 3).until(
                            EC.visibility_of_element_located((By.ID, "tipoOcorrenciaId"))
                        )
                    except (TimeoutException, NoSuchFrameException, StaleElementReferenceException):
                        continue
            except WebDriverException:
                continue

        self.driver.switch_to.window(original_handle)
        self.driver.switch_to.default_content()
        raise TimeoutException("Seletor de tipo de ocorrência não encontrado.")

    def select_occurrence_type(self) -> None:
        self.find_occurrence_select()
        select_element = self.driver.find_element(By.ID, "tipoOcorrenciaId")
        select = Select(select_element)
        self.wait.until(lambda _: any(
            option.get_attribute("value") == self.settings.occurrence_type_value
            for option in select.options
        ))
        select.select_by_value(self.settings.occurrence_type_value)
        self.driver.execute_script(
            "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
            select_element,
        )

    def create_service_order(self) -> None:
        button = self.wait.until(EC.element_to_be_clickable((By.ID, "botao-cadastrar-os")))
        self.safe_click(button)
        time.sleep(1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Automação demonstrativa de notificações.")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Executa aprovação e cadastro. Sem esta opção, apenas pesquisa os IDs.",
    )
    args = parser.parse_args()

    try:
        settings = Settings.from_environment()
        notification_ids = load_notification_ids(settings.ids_file)
    except (ValueError, FileNotFoundError) as error:
        logger.error("%s", error)
        return 2

    if not notification_ids:
        logger.warning("Nenhum ID foi encontrado no arquivo configurado.")
        return 0

    if args.execute:
        logger.warning(
            "MODO DE EXECUÇÃO: ações de aprovação e cadastro serão realizadas no sistema configurado."
        )
        confirmation = input("Digite EXECUTAR para confirmar: ")
        if confirmation != "EXECUTAR":
            logger.info("Execução cancelada.")
            return 0

    driver = build_driver(settings)
    try:
        automation = NotificationAutomation(driver, settings)
        automation.login()
        automation.open_notifications()

        for index, notification_id in enumerate(notification_ids, start=1):
            logger.info("[%s/%s] Processando notificação.", index, len(notification_ids))
            automation.open_notifications()
            automation.search_notification(notification_id)

            if not args.execute:
                logger.info("Simulação: nenhuma aprovação ou ordem de serviço foi criada.")
                continue

            parent_handle, new_handle = automation.approve_notification(notification_id)
            automation.select_occurrence_type()
            automation.create_service_order()

            if new_handle and new_handle in driver.window_handles:
                driver.close()
            if parent_handle in driver.window_handles:
                driver.switch_to.window(parent_handle)
            driver.switch_to.default_content()

        logger.info("Processamento finalizado.")
        return 0
    except Exception:
        logger.exception("A automação foi interrompida por um erro.")
        return 1
    finally:
        # Fecha o navegador ao final. Remova esta linha se precisar inspecioná-lo.
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
