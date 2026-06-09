import os
import asyncio
import logging
import random
import string
import time
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes
)

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

WAITING_FOR_OTP = 1
TARGET_URL = "https://www.instagram.com/accounts/emailsignup/" 

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is running successfully on Render Free Tier!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

def init_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox") 
    chrome_options.add_argument("--disable-dev-shm-usage") 
    chrome_options.add_argument("--disable-gpu") 
    chrome_options.add_argument("--window-size=1920,1080") 
    chrome_options.add_argument("--disable-extensions")
    
    # Anti-bot
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    
    driver.set_page_load_timeout(30) 
    return driver

def generate_strong_password(length=12):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(chars) for _ in range(length))

async def start_signup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("Usage: /create <FullName> <Username> <Email>")
        return ConversationHandler.END

    email = args[-1]
    username = args[-2]
    full_name = " ".join(args[:-2])
    password = generate_strong_password()

    await update.message.reply_text("🔍 Debugging started... Extracting dropdown info.")

    try:
        driver = init_driver()
        wait = WebDriverWait(driver, 15) 
        
        driver.get(TARGET_URL)
        time.sleep(6) 
        
        try:
            driver.execute_script("document.querySelectorAll('[role=\"dialog\"]').forEach(e => e.remove());")
        except:
            pass

        inputs = wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "input")))
        visible_inputs = [inp for inp in inputs if inp.is_displayed() and inp.get_attribute("type") != "hidden"]

        email_box = visible_inputs[0]
        pass_box = visible_inputs[1]
        name_box = visible_inputs[2]
        user_box = visible_inputs[3]

        email_box.click()
        email_box.send_keys(email)
        pass_box.click()
        pass_box.send_keys(password)
        name_box.click()
        name_box.send_keys(full_name)
        user_box.click()
        user_box.send_keys(username)
        
        time.sleep(2)

        # ==========================================
        # DEBUGGING: EXTRACTING DROPDOWN DATA
        # ==========================================
        debug_msg = "⚙️ **DROPDOWN ANALYSIS:**\n\n"
        
        try:
            selects = driver.find_elements(By.TAG_NAME, "select")
            
            for i, select_box in enumerate(selects):
                title = select_box.get_attribute("title")
                debug_msg += f"**Box {i+1} (Title: '{title}'):**\n"
                
                # Get first 4 options from this box
                options = select_box.find_elements(By.TAG_NAME, "option")
                for opt in options[:4]:
                    debug_msg += f" - Text: `{opt.text}` | Value: `{opt.get_attribute('value')}`\n"
                debug_msg += "...\n\n"
                
            await update.message.reply_text(debug_msg, parse_mode="Markdown")

            # Click the Month box and take a photo just in case
            month_box = driver.find_element(By.XPATH, "//select[contains(@title, 'Month')]")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", month_box)
            month_box.click()
            time.sleep(1)
            
            driver.save_screenshot("debug_open.png")
            with open("debug_open.png", "rb") as photo:
                await update.message.reply_photo(
                    photo=photo, 
                    caption="📸 Month dropdown click chesina tharvatha screenshot idi."
                )

        except Exception as dbg_err:
            await update.message.reply_text(f"Dropdown data theeyadam lo error: {dbg_err}")

        driver.quit()
        return ConversationHandler.END

    except Exception as e:
        error_msg = str(e)
        if 'driver' in locals() and driver is not None:
            try:
                driver.save_screenshot("error_form.png")
                with open("error_form.png", "rb") as photo:
                    await update.message.reply_photo(photo=photo, caption=f"Error!\n`{error_msg[:300]}`", parse_mode="Markdown")
            except: pass
            driver.quit()
        return ConversationHandler.END

def main():
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN: return
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(ConversationHandler(entry_points=[CommandHandler("create", start_signup)], states={}, fallbacks=[]))
    threading.Thread(target=run_dummy_server, daemon=True).start()
    app.run_polling()

if __name__ == '__main__':
    main()
