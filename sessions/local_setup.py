# local_setup.py - Corre esto UNA VEZ localmente para escanear QR y guardar sesión
import pickle
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

chrome_options = Options()
# NO headless para ver QR
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(options=chrome_options)

driver.get("https://web.whatsapp.com")
input("Escanea el QR con tu app de WhatsApp y presiona Enter...")

# Espera carga completa
WebDriverWait(driver, 30).until(
    EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
)
time.sleep(5)

# Guarda cookies
cookies = driver.get_cookies()
with open("sessions/cookies.pkl", "wb") as f:
    pickle.dump(cookies, f)

# Guarda localStorage
local_storage = driver.execute_script("return Object.entries(localStorage);")
with open("sessions/local_storage.pkl", "wb") as f:
    pickle.dump(local_storage, f)

print("Sesión guardada en sessions/ ¡Sube estos archivos al repo!")
driver.quit()
