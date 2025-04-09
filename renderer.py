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
import os

load_dotenv()
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH")
CAPTURE_WIDTH = 5000
CAPTURE_HEIGHT = 5000

def render(html_path):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")

    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.get(html_path)
    driver.set_window_size(CAPTURE_WIDTH, CAPTURE_HEIGHT)

    element = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.infographic-container"))
    )

    bytes_ss = element.screenshot_as_png
    infographic_img = Image.open(BytesIO(bytes_ss))
    driver.quit()

    return infographic_img

# Testing-------------------------------------------------------
if __name__ == "__main__":
    html_url = "sample_html.html"
    # html_path = "C:\\Users\\Liu Yijun\\Desktop\\Study\\FYP\\eCaption\\Agent-Model-Infographic-Generator\\test\\" + html_url
    html_path = "C:/Users/Liu Yijun/Desktop/Study/FYP/eCaption/Agent-Model-Infographic-Generator/out/2025_04_08_21_03/layout.html"
    
    infographic_img = render(html_path)
    infographic_img.save("Agent-Model-Infographic-Generator/out/2025_04_08_21_03/init_infographic.png")
