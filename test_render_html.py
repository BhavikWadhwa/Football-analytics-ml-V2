from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

url = "https://canadawest.org/sports/msoc/2025-26/teams/ubc?view=lineup"

options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get(url)

# Wait 15 seconds for JavaScript to run
time.sleep(15)

# Get the page source
html = driver.page_source

# Save it for inspection
with open("debug_ubc.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ Saved rendered HTML to debug_ubc.html")
driver.quit()
