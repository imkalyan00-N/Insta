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
from selenium.webdriver.support.ui import Select 

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
    chrome_options.add_argument("--no-zygote")
    chrome_options.add_argument("--single-process")
    
    # --- ANTI-BOT STEALTH OPTIONS ---
    # Instagram ki real browser laaga kanipinchadaniki
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # Execute stealth JS script
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    
    driver.set_page_load_timeout(30) 
    return driver

def generate_strong_password(length=12):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(chars) for _ in range(length))

def generate_random_dob():
    year = str(random.randint(1990, 2005))
    month = random.choice(["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"])
    day = str(random.randint(1, 28))
    return year, month, day

# Kotha Function: JS tho force ga type cheyadaniki
def safe_type(driver, wait, name_attr, text, step_name):
    try:
        ele = wait.until(EC.presence_of_element_located((By.NAME, name_attr)))
        # Box munduki scroll chesi JS tho click chestam
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", ele)
        time.sleep(0.5)
        driver.execute_script("arguments[0].focus();", ele)
        ele.send_keys(text)
    except Exception as e:
        raise Exception(f"❌ '{step_name}' field daggara aagipoindi. Idi fill avvatledu.")

async def start_signup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    
    if len(args) < 3:
        await update.message.reply_text("Usage: /create <FullName> <Username> <Email>")
        return ConversationHandler.END

    email = args[-1]
    username = args[-2]
    full_name = " ".join(args[:-2])
    password = generate_strong_password()

    await update.message.reply_text(f"Starting signup process for {email}...")

    try:
        driver = init_driver()
        wait = WebDriverWait(driver, 15) 
        
        context.user_data['driver'] = driver
        context.user_data['username'] = username
        context.user_data['password'] = password 

        driver.get(TARGET_URL)
        time.sleep(5) # JS & React motham load avvadaniki 5 secs wait
        
        # Cookie popups emaina unte JS tho lepestam (to unblock UI)
        try:
            driver.execute_script("document.querySelectorAll('[role=\"dialog\"]').forEach(e => e.remove());")
        except:
            pass
            
        # 1-4 Fields (Force fill)
        safe_type(driver, wait, "emailOrPhone", email, "Email")
        safe_type(driver, wait, "password", password, "Password")

        # Birthday Section
        try:
            year, month, day = generate_random_dob()
            month_box = Select(wait.until(EC.presence_of_element_located((By.XPATH, "//select[@title='Month:']"))))
            month_box.select_by_visible_text(month)
            
            day_box = Select(driver.find_element(By.XPATH, "//select[@title='Day:']"))
            day_box.select_by_visible_text(day)
            
            year_box = Select(driver.find_element(By.XPATH, "//select[@title='Year:']"))
            year_box.select_by_visible_text(year)
        except Exception:
            logging.info("DOB dropdowns kanipinchaledu, next step ki velthondi.")

        safe_type(driver, wait, "fullName", full_name, "Full Name")
        safe_type(driver, wait, "username", username, "Username")
        
        time.sleep(3) 

        # Submit Button Force Click
        submit_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//button[@type='submit']")))
        driver.execute_script("arguments[0].click();", submit_btn)

        wait.until(EC.presence_of_element_located((By.NAME, "email_confirmation_code")))

        await update.message.reply_text("✅ Form submitted successfully! Please check your email and reply with the OTP.")
        return WAITING_FOR_OTP

    except Exception as e:
        error_msg = str(e)
        logging.error(f"Error in start_signup: {error_msg}")
        
        if 'driver' in locals() and driver is not None:
            try:
                driver.save_screenshot("error_form.png")
                with open("error_form.png", "rb") as photo:
                    await update.message.reply_photo(
                        photo=photo, 
                        caption=f"⚠️ **Error!**\n\n`{error_msg[:300]}`",
                        parse_mode="Markdown"
                    )
            except Exception:
                pass
            driver.quit()
        return ConversationHandler.END


async def process_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    otp = update.message.text
    driver = context.user_data.get('driver')
    username = context.user_data.get('username')
    password = context.user_data.get('password') 

    if not driver:
        await update.message.reply_text("Browser session lost. Please start over with /create.")
        return ConversationHandler.END

    await update.message.reply_text("OTP received. Skipping setup steps... Please wait.")

    try:
        wait = WebDriverWait(driver, 15)

        otp_input = wait.until(EC.presence_of_element_located((By.NAME, "email_confirmation_code")))
        driver.execute_script("arguments[0].focus();", otp_input)
        otp_input.send_keys(otp)
        
        confirm_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Next') or contains(text(), 'Confirm')]")))
        driver.execute_script("arguments[0].click();", confirm_btn)

        # Skips (Using JS click to avoid overlap issues)
        time.sleep(4)
        try:
            skip_pic_btn = driver.find_element(By.XPATH, "//button[text()='Skip']")
            driver.execute_script("arguments[0].click();", skip_pic_btn)
        except: pass
        
        time.sleep(3)
        try:
            skip_friends_btn = driver.find_element(By.XPATH, "//button[text()='Skip']")
            driver.execute_script("arguments[0].click();", skip_friends_btn)
        except: pass
        
        time.sleep(3)
        try:
            skip_suggested_btn = driver.find_element(By.XPATH, "//button[text()='Skip' or text()='Next']")
            driver.execute_script("arguments[0].click();", skip_suggested_btn)
        except: pass

        wait.until(EC.presence_of_element_located((By.XPATH, "//*[@aria-label='Home']"))) 
        
        await update.message.reply_text(
            f"✅ **Success!** Account created successfully and setup skipped.\n\n"
            f"👤 **Username:** `{username}`\n"
            f"🔐 **Password:** `{password}`", 
            parse_mode="Markdown"
        )

    except Exception as e:
        logging.error(f"Error in process_otp skips: {e}")
        if driver:
            try:
                driver.save_screenshot("error_skips.png")
                with open("error_skips.png", "rb") as photo:
                    await update.message.reply_photo(
                        photo=photo, 
                        caption=f"⚠️ **Error vachindi!** OTP submission leda Skip steps daggara aagipoindi.\n\n`{str(e)[:300]}`",
                        parse_mode="Markdown"
                    )
            except Exception:
                pass
    finally:
        if driver:
            driver.quit()
            context.user_data.clear()

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    driver = context.user_data.get('driver')
    if driver:
        driver.quit()
        context.user_data.clear()
        
    await update.message.reply_text("Signup process cancelled and browser closed.")
    return ConversationHandler.END

def main():
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN environment variable is not set!")
        return
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("create", start_signup)],
        states={
            WAITING_FOR_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_otp)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv_handler)
    threading.Thread(target=run_dummy_server, daemon=True).start()
    print("Bot and Dummy Server are running...")
    app.run_polling()

if __name__ == '__main__':
    main()
