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
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Local testing kosam .env file load chestundi
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Conversation states
WAITING_FOR_OTP = 1

# ==========================================
# 1. IKKADA NEE WEBSITE URL REPLACE CHEYYI
# (Mukhyamaina gurtu: Render lo localhost panicheyyadu!)
# ==========================================
TARGET_URL = "https://www.instagram.com/accounts/emailsignup"
# --- DUMMY WEB SERVER FOR RENDER FREE TIER ---
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
# ---------------------------------------------

def init_driver():
    """Initializes Chrome WebDriver."""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox") 
    chrome_options.add_argument("--disable-dev-shm-usage") 
    chrome_options.add_argument("--disable-gpu") 
    chrome_options.add_argument("--window-size=1920,1080") 
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def generate_strong_password(length=12):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(chars) for _ in range(length))

def generate_random_dob():
    year = str(random.randint(1990, 2005))
    month = str(random.randint(1, 12)).zfill(2)
    day = str(random.randint(1, 28)).zfill(2)
    return year, month, day

async def start_signup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    
    if len(args) < 3:
        await update.message.reply_text(
            "Usage: /create <FullName> <Username> <Email>\n"
            "Example: /create John Doe johndoe jd@example.com"
        )
        return ConversationHandler.END

    email = args[-1]
    username = args[-2]
    full_name = " ".join(args[:-2])

    await update.message.reply_text(f"Starting signup process for {email}...")

    try:
        driver = init_driver()
        wait = WebDriverWait(driver, 15) 
        
        context.user_data['driver'] = driver
        context.user_data['full_name'] = full_name
        context.user_data['username'] = username

        # STEP 1
        driver.get(TARGET_URL)
        
        # ==========================================
        # 2. IKKADA NUNDI NEE LOCATORS REPLACE CHEYYI
        # ==========================================
        signup_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Sign up with email address')]")))
        signup_btn.click()

        # STEP 2
        email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
        email_input.send_keys(email)
        
        next_btn_1 = wait.until(EC.element_to_be_clickable((By.ID, "next_button_1")))
        next_btn_1.click()

        # STEP 3 (Pause for OTP)
        await update.message.reply_text("Email submitted. Please check your inbox and reply with the OTP.")
        return WAITING_FOR_OTP

    except Exception as e:
        logging.error(f"Error in start_signup: {e}")
        
        # --- SCREENSHOT LOGIC ADDED HERE ---
        if 'driver' in locals() and driver is not None:
            try:
                driver.save_screenshot("error_step1.png")
                with open("error_step1.png", "rb") as photo:
                    await update.message.reply_photo(
                        photo=photo, 
                        caption=f"⚠️ **Error vachindi!** Browser lo ee screen daggara aagipoindi.\n\n`{str(e)[:400]}`",
                        parse_mode="Markdown"
                    )
            except Exception as ss_error:
                logging.error(f"Screenshot theeyadam lo error: {ss_error}")
                await update.message.reply_text(f"Error vachindi kani screenshot theeyalekapoya.\n\n`{str(e)[:400]}`", parse_mode="Markdown")
            
            driver.quit()
        else:
            await update.message.reply_text(f"Browser start avvakamunde error vachindi. \n\n`{str(e)[:400]}`", parse_mode="Markdown")
            
        return ConversationHandler.END


async def process_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    otp = update.message.text
    driver = context.user_data.get('driver')
    full_name = context.user_data.get('full_name')
    username = context.user_data.get('username')

    if not driver:
        await update.message.reply_text("Browser session lost. Please start over with /create.")
        return ConversationHandler.END

    await update.message.reply_text("OTP received. Continuing automation... Please wait.")

    try:
        wait = WebDriverWait(driver, 15)

        # STEP 3 (Resume)
        otp_input = wait.until(EC.presence_of_element_located((By.NAME, "otp_code")))
        otp_input.send_keys(otp)
        
        next_btn_2 = wait.until(EC.element_to_be_clickable((By.ID, "next_button_2")))
        next_btn_2.click()

        # STEP 4
        password = generate_strong_password()
        pass_input = wait.until(EC.presence_of_element_located((By.NAME, "password")))
        pass_input.send_keys(password)
        
        next_btn_3 = wait.until(EC.element_to_be_clickable((By.ID, "next_button_3")))
        next_btn_3.click()

        # STEP 5
        year, month, day = generate_random_dob()
        
        year_input = wait.until(EC.presence_of_element_located((By.NAME, "dob_year")))
        year_input.send_keys(year)
        month_input = driver.find_element(By.NAME, "dob_month")
        month_input.send_keys(month)
        day_input = driver.find_element(By.NAME, "dob_day")
        day_input.send_keys(day)

        next_btn_4 = wait.until(EC.element_to_be_clickable((By.ID, "next_button_4")))
        next_btn_4.click()

        # STEP 6
        name_input = wait.until(EC.presence_of_element_located((By.NAME, "fullname")))
        name_input.send_keys(full_name)
        
        next_btn_5 = wait.until(EC.element_to_be_clickable((By.ID, "next_button_5")))
        next_btn_5.click()

        # STEP 7
        user_input = wait.until(EC.presence_of_element_located((By.NAME, "username")))
        user_input.send_keys(username)
        
        time.sleep(2.5) 
        
        next_btn_6 = wait.until(EC.element_to_be_clickable((By.ID, "next_button_6")))
        next_btn_6.click()

        # STEP 8
        agree_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'I agree')]")))
        agree_btn.click()

        # FINAL
        time.sleep(3) 
        
        await update.message.reply_text(
            f"✅ **Success!** Account created successfully.\n\n"
            f"👤 **Username:** {username}\n"
            f"🔐 **Password:** `{password}`", 
            parse_mode="Markdown"
        )

    except Exception as e:
        logging.error(f"Error in process_otp: {e}")
        
        # --- SCREENSHOT LOGIC ADDED HERE ---
        if driver:
            try:
                driver.save_screenshot("error_final.png")
                with open("error_final.png", "rb") as photo:
                    await update.message.reply_photo(
                        photo=photo, 
                        caption=f"⚠️ **Error vachindi (Final steps)!** Browser lo ee screen daggara aagipoindi.\n\n`{str(e)[:400]}`",
                        parse_mode="Markdown"
                    )
            except Exception as ss_error:
                logging.error(f"Screenshot error: {ss_error}")
                await update.message.reply_text("An error occurred during final steps.")
                
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
