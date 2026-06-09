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

# Local testing kosam .env load
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

# ==========================================
# 1. URL REPLACE CHEYYI
# ==========================================
TARGET_URL = "https://www.instagram.com/accounts/emailsignup/" # Example: Change to your URL

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
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox") 
    chrome_options.add_argument("--disable-dev-shm-usage") 
    chrome_options.add_argument("--disable-gpu") 
    chrome_options.add_argument("--window-size=1920,1080") 
    
    # --- KOTHA MEMORY-SAVING OPTIONS ---
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--no-zygote")
    chrome_options.add_argument("--single-process")
    
    # Images load avvakunda aapadam (RAM save avtundi, fast ga load avtundi)
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # Page 30 seconds kante ekkuva load aithe, hang avvakunda Error isthundi
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
    password = generate_strong_password() # Password mundey generate chestunnam

    await update.message.reply_text(f"Starting signup process for {email}...")

    try:
        driver = init_driver()
        wait = WebDriverWait(driver, 15) 
        
        context.user_data['driver'] = driver
        context.user_data['full_name'] = full_name
        context.user_data['username'] = username
        context.user_data['password'] = password # Save for final message

        # Open Site
        driver.get(TARGET_URL)
        
        # ==========================================
        # FORM FILLING (Anni oke page lo)
        # Nuvvu ee locators update cheyyali nee site batti
        # ==========================================
        
        # 1. Email
        email_input = wait.until(EC.presence_of_element_located((By.NAME, "emailOrPhone")))
        email_input.send_keys(email)

        # 2. Password
        pass_input = wait.until(EC.presence_of_element_located((By.NAME, "password")))
        pass_input.send_keys(password)

        # 3. Name
        name_input = wait.until(EC.presence_of_element_located((By.NAME, "fullName")))
        name_input.send_keys(full_name)

        # 4. Username
        user_input = wait.until(EC.presence_of_element_located((By.NAME, "username")))
        user_input.send_keys(username)
        
        time.sleep(2) # Chinna pause validation kosam

        # 5. Submit Button
        submit_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
        submit_btn.click()

        # 6. Birthday Section (Idi submit kottaka popup ravachu leda form loney undochu, nee site batti marchu)
        try:
            year, month, day = generate_random_dob()
            
            month_input = wait.until(EC.presence_of_element_located((By.XPATH, "//select[@title='Month:']")))
            month_input.send_keys(month)
            
            day_input = driver.find_element(By.XPATH, "//select[@title='Day:']")
            day_input.send_keys(day)
            
            year_input = driver.find_element(By.XPATH, "//select[@title='Year:']")
            year_input.send_keys(year)
            
            next_btn_dob = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Next')]")))
            next_btn_dob.click()
        except Exception:
            logging.info("DOB section ledu leda skip ayyindi.")

        # --- Wait for OTP input field to appear ---
        wait.until(EC.presence_of_element_located((By.NAME, "email_confirmation_code")))

        await update.message.reply_text("✅ Form submitted successfully! Please check your email and reply with the OTP.")
        return WAITING_FOR_OTP

    except Exception as e:
        logging.error(f"Error in start_signup: {e}")
        
        if 'driver' in locals() and driver is not None:
            try:
                driver.save_screenshot("error_form.png")
                with open("error_form.png", "rb") as photo:
                    await update.message.reply_photo(
                        photo=photo, 
                        caption=f"⚠️ **Error vachindi!** Browser lo form submit aagipoindi.\n\n`{str(e)[:400]}`",
                        parse_mode="Markdown"
                    )
            except Exception:
                await update.message.reply_text("Error vachindi kani screenshot theeyalekapoya.")
            driver.quit()
        return ConversationHandler.END


async def process_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    otp = update.message.text
    driver = context.user_data.get('driver')
    username = context.user_data.get('username')
    password = context.user_data.get('password') # Fetch saved password

    if not driver:
        await update.message.reply_text("Browser session lost. Please start over with /create.")
        return ConversationHandler.END

    await update.message.reply_text("OTP received. Skipping setup steps... Please wait.")

    try:
        wait = WebDriverWait(driver, 15)

        # STEP 1: Enter OTP & Confirm
        otp_input = wait.until(EC.presence_of_element_located((By.NAME, "email_confirmation_code")))
        otp_input.send_keys(otp)
        
        confirm_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Next') or contains(text(), 'Confirm')]")))
        confirm_btn.click()

        # STEP 3: Add Profile Picture -> Skip
        skip_pic_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Skip']")))
        skip_pic_btn.click()
        time.sleep(2)

        # STEP 4: Find Friends -> Skip
        skip_friends_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Skip']")))
        skip_friends_btn.click()
        time.sleep(2)

        # STEP 5: Suggested Accounts -> Skip
        skip_suggested_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Skip' or text()='Next']")))
        skip_suggested_btn.click()

        # STEP 6: Wait for Home Feed to load
        # Nuvvu home icon leda profile icon locator ikkada ivvachu
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
                        caption=f"⚠️ **Error vachindi!** OTP submission leda Skip steps daggara aagipoindi.\n\n`{str(e)[:400]}`",
                        parse_mode="Markdown"
                    )
            except Exception:
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
