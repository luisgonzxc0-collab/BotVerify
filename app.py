import os
import pickle
import time
import concurrent.futures
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode
import asyncio

# Función síncrona para verificar número (con manejo de sesión)
def check_whatsapp_number(phone_number):
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number

    # Configuración de Chrome headless para servidor
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-data-dir=/tmp/chrome-user-data')  # Dir temporal para sesión

    driver = webdriver.Chrome(options=chrome_options)

    session_dir = '/app/sessions'  # Dir para sesiones (persistente? En Render es temporal)
    os.makedirs(session_dir, exist_ok=True)
    cookies_file = os.path.join(session_dir, 'cookies.pkl')
    local_storage_file = os.path.join(session_dir, 'local_storage.pkl')

    try:
        driver.get("https://web.whatsapp.com")

        # Cargar sesión si existe
        if os.path.exists(cookies_file) and os.path.exists(local_storage_file):
            # Cargar cookies
            with open(cookies_file, 'rb') as f:
                cookies = pickle.load(f)
            for cookie in cookies:
                driver.add_cookie(cookie)
            driver.refresh()

            # Cargar localStorage
            with open(local_storage_file, 'rb') as f:
                local_storage = pickle.load(f)
            for key, value in local_storage:
                driver.execute_script(f"localStorage.setItem('{key}', '{value}');")
            driver.refresh()

            time.sleep(5)  # Espera carga
        else:
            # Si no hay sesión, error (debes crearla localmente)
            return f"{phone_number}: Error - Sesión no encontrada. Crea la sesión localmente primero."

        # Espera a que cargue la interfaz (chequeo básico de sesión)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
        )

        # Buscar el número
        search_box = driver.find_element(By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]')
        search_box.clear()
        search_box.send_keys(phone_number)
        time.sleep(3)

        # Chequea si no está registrado
        try:
            not_on_whatsapp = driver.find_element(By.XPATH, "//span[contains(text(), 'no está en WhatsApp')] | //div[contains(text(), 'Número no en WhatsApp')]")
            return f"{phone_number}: No registrado (disponible para registrar)"
        except NoSuchElementException:
            # Intenta abrir chat para confirmar activo o ban
            try:
                chat_link = driver.find_element(By.XPATH, f"//span[@title='{phone_number}']")
                chat_link.click()
                time.sleep(2)
                # Si carga chat sin error, activo
                message_box = driver.find_element(By.XPATH, "//div[@title='Escribir un mensaje']")
                # Intento básico de "envío" para detectar ban (envía vacío, chequea error)
                message_box.send_keys(" ")
                send_button = driver.find_element(By.XPATH, "//span[@data-icon='send']")
                send_button.click()
                time.sleep(1)
                # Si no hay error de ban (e.g., popup), asume activo
                alerts = driver.find_elements(By.XPATH, "//div[contains(@class, 'alert')]")
                if any("baneado" in alert.text.lower() or "bloqueado" in alert.text.lower() for alert in alerts):
                    return f"{phone_number}: Posiblemente baneado"
                else:
                    return f"{phone_number}: Activo/Registrado"
            except Exception as e:
                return f"{phone_number}: Posiblemente baneado o error ({str(e)})"

    except TimeoutException:
        return f"{phone_number}: Error de timeout (sesión inválida o conexión)"
    except Exception as e:
        return f"{phone_number}: Error general ({str(e)})"
    finally:
        driver.quit()

# Handler async para el comando /check
async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.reply_to_message:
        number = update.message.reply_to_message.text.strip()
    else:
        if context.args:
            number = ' '.join(context.args)
        else:
            await update.message.reply_text("Uso: /check +1234567890")
            return

    # Mensaje de espera
    wait_msg = await update.message.reply_text("Verificando... Esto puede tomar 10-30 segundos.")

    # Ejecutar chequeo síncrono en thread pool
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, check_whatsapp_number, number)

    await wait_msg.edit_text(result)

def main() -> None:
    """Inicia el bot con webhook."""
    token = os.environ.get('BOT_TOKEN')
    if not token:
        raise ValueError("BOT_TOKEN no configurado")

    # Crea aplicación
    application = Application.builder().token(token).build()

    # Handlers
    application.add_handler(CommandHandler("check", check_command))
    application.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("Envía /check +número para verificar WhatsApp.")))

    # Configuración webhook
    webhook_url = os.environ.get('WEBHOOK_URL')
    if not webhook_url:
        raise ValueError("WEBHOOK_URL no configurada (e.g., https://tuapp.onrender.com/webhook)")

    port = int(os.environ.get('PORT', 10000))
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path="webhook",
        webhook_url=webhook_url,
    )

if __name__ == '__main__':
    main()
