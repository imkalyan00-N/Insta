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
    
    # Ee sari Images kuda load avvaniddam, appude exact ga page ela undo thelustundi
    # prefs = {"profile.managed_default_content_settings.images": 2} (Removed for debugging)
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    
    driver.set_page_load_timeout(30) 
    return driver


async def start_signup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Page load ayyaka asalu em kanipistondo Full Screenshot theestunnanu. Please wait...")

    try:
        driver = init_driver()
        
        # 1. Open URL
        driver.get(TARGET_URL)
        
        # 2. Wait for a long time to let everything load (Popups, Captchas, etc.)
        time.sleep(8) 
        
        # 3. Take Full Screenshot
        driver.save_screenshot("full_page_debug.png")
        
        with open("full_page_debug.png", "rb") as photo:
            await update.message.reply_photo(
                photo=photo, 
                caption="🔍 **Idiగో Bot ki kanipistunna real Instagram page!**\n\nIkkada emundo chudu, asalu form load ayyinda leka block chesara ani telisipotundi.",
                parse_mode="Markdown"
            )

        # Print Current URL to see if it redirected
        current_url = driver.current_url
        await update.message.reply_text(f"🔗 **Current URL:** `{current_url}`", parse_mode="Markdown")

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
