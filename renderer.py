from datetime import datetime
from dotenv import load_dotenv
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
import base64
import os

load_dotenv()
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH")
CAPTURE_WIDTH = 3000
CAPTURE_HEIGHT = 3000
DEVICE_SCALE_FACTOR = 3

def render(html_path):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")

    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.get(html_path)
    driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
        "mobile": False,
        "width": CAPTURE_WIDTH,
        "height": CAPTURE_HEIGHT,
        "deviceScaleFactor": DEVICE_SCALE_FACTOR
    })

    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.infographic-container"))
    )

    element = driver.find_element(By.CSS_SELECTOR, "div.infographic-container")
    location = element.location_once_scrolled_into_view
    size = element.size

    screenshot_data = driver.get_screenshot_as_base64()
    driver.quit()

    full_img = Image.open(BytesIO(base64.b64decode(screenshot_data)))

    left = int(location["x"] * DEVICE_SCALE_FACTOR)
    top = int(location["y"] * DEVICE_SCALE_FACTOR)
    right = int((location["x"] + size["width"]) * DEVICE_SCALE_FACTOR)
    bottom = int((location["y"] + size["height"]) * DEVICE_SCALE_FACTOR)

    cropped = full_img.crop((left, top, right, bottom))
    return cropped

# Testing-------------------------------------------------------
if __name__ == "__main__":
    html_url = "sample_html.html"
    html_path = "" # full path
    
    infographic_img = render(html_path)
    infographic_img.save("enh_news_info/test/test_infographic.png")
