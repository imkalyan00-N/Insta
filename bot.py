import os
import asyncio
import logging
import time
import threading
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

async def start_signup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scanning Instagram form for Dropdowns... Please wait.")

    try:
        driver = init_driver()
        wait = WebDriverWait(driver, 15) 
        
        driver.get(TARGET_URL)
        time.sleep(6) # Page Load
        
        try:
            driver.execute_script("document.querySelectorAll('[role=\"dialog\"]').forEach(e => e.remove());")
        except:
            pass

        # Email isthe kani DOB options load avvavu konnisarlu, so dummy ga isthunnam
        try:
            inputs = wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "input")))
            visible_inputs = [inp for inp in inputs if inp.is_displayed() and inp.get_attribute("type") != "hidden"]
            visible_inputs[0].send_keys("test_debug@gmail.com")
            visible_inputs[1].send_keys("TestPass@123")
            time.sleep(2)
        except:
            pass

        # Extract all Select elements
        selects = driver.find_elements(By.TAG_NAME, "select")
        
        if not selects:
            await update.message.reply_text("⚠️ Asalu page lo ye okka dropdown kanipinchaledu!")
            driver.quit()
            return ConversationHandler.END

        report = f"✅ **Found {len(selects)} Dropdown boxes on the page:**\n\n"

        for i, s in enumerate(selects):
            try:
                title = s.get_attribute("title")
                name = s.get_attribute("name")
                opts = s.find_elements(By.TAG_NAME, "option")
                
                report += f"**Box {i+1}:** Title: `'{title}'` | Name: `'{name}'` | Total Options: {len(opts)}\n"
                
                # First 5 options ni extract chestunnam
                for opt in opts[:5]:
                    report += f"  🔹 Text: `{opt.text}` | Value: `{opt.get_attribute('value')}`\n"
                report += "  ...\n\n"
            except Exception as box_e:
                report += f"**Box {i+1}:** Error reading this box.\n\n"

        await update.message.reply_text(report, parse_mode="Markdown")

        driver.quit()
        return ConversationHandler.END

    except Exception as e:
        error_msg = str(e)
        logging.error(f"Error: {error_msg}")
        await update.message.reply_text(f"⚠️ **Error!**\n\n`{error_msg[:300]}`", parse_mode="Markdown")
        if 'driver' in locals() and driver is not None:
            driver.quit()
        return ConversationHandler.END

def main():
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN environment variable is not set!")
        return
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("create", start_signup)],
        states={},
        fallbacks=[]
    )

    app.add_handler(conv_handler)
    threading.Thread(target=run_dummy_server, daemon=True).start()
    print("Bot and Dummy Server are running...")
    app.run_polling()

if __name__ == '__main__':
    main()
