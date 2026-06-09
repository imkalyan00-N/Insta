import os
import asyncio
import logging
import random
import string
import time
import threading
import glob
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update, InputMediaPhoto
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
from selenium.webdriver.common.keys import Keys 

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
    
    # MOBILE PRETENDER
    chrome_options.add_argument("--window-size=400,850") 
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36")
    
    chrome_options.add_argument("--disable-extensions")
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

def generate_random_dob():
    year = str(random.randint(1990, 2005))
    month = str(random.randint(1, 12)) 
    day = str(random.randint(1, 28))
    return year, month, day

# Screenshot helper for debugging
ss_count = [1]
def snap(driver, name):
    try:
        if driver is not None:
            driver.save_screenshot(f"step_{ss_count[0]:02d}_{name}.png")
            ss_count[0] += 1
    except:
        pass

async def start_signup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    
    if len(args) < 3:
        await update.message.reply_text("Usage: /create <FullName> <Username> <Email>")
        return ConversationHandler.END

    email = args[-1]
    username = args[-2]
    full_name = " ".join(args[:-2])
    password = generate_strong_password()

    await update.message.reply_text(f"Starting mobile signup process for {email}...")

    for f in glob.glob("step_*.png"):
        try: os.remove(f)
        except: pass
    ss_count[0] = 1

    try:
        driver = init_driver()
        wait = WebDriverWait(driver, 15) 
        
        context.user_data['driver'] = driver
        context.user_data['full_name'] = full_name
        context.user_data['username'] = username
        context.user_data['password'] = password 

        # STEP 1: Open URL
        driver.get(TARGET_URL)
        time.sleep(5) 
        snap(driver, "Page_Loaded")

        # ==========================================
        # JAVASCRIPT FORCE CLICK FOR "Sign up with email"
        # ==========================================
        try:
            js_click_email = """
            var elements = document.querySelectorAll('button, div[role="button"], a, span, div');
            for (var i = 0; i < elements.length; i++) {
                var text = elements[i].innerText || elements[i].textContent;
                if (text && (text.toLowerCase().includes('sign up with email') || text.toLowerCase().includes('email address'))) {
                    elements[i].click();
                    return true;
                }
            }
            return false;
            """
            clicked = driver.execute_script(js_click_email)
            if clicked:
                time.sleep(3) # Wait for Email box to appear
                snap(driver, "Switched_To_Email")
            else:
                logging.info("JS trick tho email button dorakaledu.")
        except Exception as e:
            logging.info(f"JS click failed: {e}")

        # STEP 2: Enter Email & Click Next
        email_box = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='email' or contains(@name, 'email') or contains(@name, 'emailOrPhone')]")))
        driver.execute_script("arguments[0].focus();", email_box)
        email_box.send_keys(email)
        snap(driver, "Email_Entered")
        
        next_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(translate(text(), 'NEXT', 'next'), 'next')]")))
        driver.execute_script("arguments[0].click();", next_btn)

        # STEP 3: Wait for OTP box
        wait.until(EC.presence_of_element_located((By.NAME, "email_confirmation_code")))
        snap(driver, "Waiting_For_OTP")

        await update.message.reply_text("✅ Email accepted! Please check your email and reply with the OTP.")
        return WAITING_FOR_OTP

    except Exception as e:
        error_msg = str(e)
        logging.error(f"Error in start_signup: {error_msg}")
        
        if 'driver' in locals() and driver is not None:
            snap(driver, "Crash_Start_Signup")
            
            media = []
            files = sorted(glob.glob("step_*.png"))
            for f in files[-10:]:
                media.append(InputMediaPhoto(open(f, 'rb')))
                
            if media:
                try:
                    await update.message.reply_media_group(media=media)
                except Exception as ex:
                    pass
            
            driver.quit()
            
        await update.message.reply_text(f"⚠️ **Error at Start Signup!**\n📸 Screenshots paina pampanu chudu.\n\n`{error_msg[:300]}`", parse_mode="Markdown")
        return ConversationHandler.END


async def process_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    otp = update.message.text
    driver = context.user_data.get('driver')
    full_name = context.user_data.get('full_name')
    username = context.user_data.get('username')
    password = context.user_data.get('password') 

    if not driver:
        await update.message.reply_text("Browser session lost. Please start over with /create.")
        return ConversationHandler.END

    await update.message.reply_text("OTP received. Processing remaining steps...")

    try:
        wait = WebDriverWait(driver, 15)

        # STEP 3 (Part B): Enter OTP
        otp_box = wait.until(EC.presence_of_element_located((By.NAME, "email_confirmation_code")))
        otp_box.send_keys(otp)
        snap(driver, "OTP_Entered")
        
        next_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(translate(text(), 'NEXT', 'next'), 'next')]")))
        driver.execute_script("arguments[0].click();", next_btn)

        # STEP 4: Password Page
        pass_box = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@name='password' or @type='password']")))
        pass_box.send_keys(password)
        snap(driver, "Password_Entered")
        
        next_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(translate(text(), 'NEXT', 'next'), 'next')]")))
        driver.execute_script("arguments[0].click();", next_btn)

        # STEP 5: Date of Birth Page
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "select")))
        time.sleep(2)
        year, month, day = generate_random_dob()
        selects = driver.find_elements(By.TAG_NAME, "select")
        
        for s in selects:
            try:
                opts = s.find_elements(By.TAG_NAME, "option")
                count = len(opts)
                if 11 <= count <= 13: 
                    s.click()
                    time.sleep(0.5)
                    s.find_element(By.XPATH, f".//option[@value='{month}']").click()
                elif 28 <= count <= 32: 
                    s.click()
                    time.sleep(0.5)
                    s.find_element(By.XPATH, f".//option[@value='{day}']").click()
                elif count >= 50:
                    val = opts[1].get_attribute("value")
                    if val and val.isdigit() and len(val) == 4:
                        s.click()
                        time.sleep(0.5)
                        s.find_element(By.XPATH, f".//option[@value='{year}']").click()
            except:
                pass
                
        snap(driver, "DOB_Selected")
        time.sleep(1)
        next_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(translate(text(), 'NEXT', 'next'), 'next')]")))
        driver.execute_script("arguments[0].click();", next_btn)

        # STEP 6: Name Page
        name_box = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@name='fullName' or contains(@name, 'name')]")))
        name_box.send_keys(full_name)
        snap(driver, "Name_Entered")
        
        next_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(translate(text(), 'NEXT', 'next'), 'next')]")))
        driver.execute_script("arguments[0].click();", next_btn)

        # STEP 7: Username Page
        user_box = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@name='username']")))
        
        user_box.send_keys(Keys.CONTROL + "a")
        user_box.send_keys(Keys.DELETE)
        user_box.send_keys(username)
        
        time.sleep(3)
        snap(driver, "Username_Entered")
        
        next_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(translate(text(), 'NEXT', 'next'), 'next') or contains(text(), 'Sign up')]")))
        driver.execute_script("arguments[0].click();", next_btn)

        # STEP 8: Terms and Policies Page
        try:
            agree_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'I agree') or contains(text(), 'Agree')]")))
            snap(driver, "Terms_Page")
            driver.execute_script("arguments[0].click();", agree_btn)
            time.sleep(5) 
        except Exception as e:
            logging.info("I agree button skip ayyindi.")

        snap(driver, "Final_Success")

        await update.message.reply_text(
            f"✅ **Success!** Mobile Sign up complete.\n\n"
            f"👤 **Username:** `{username}`\n"
            f"🔐 **Password:** `{password}`", 
            parse_mode="Markdown"
        )

    except Exception as e:
        error_msg = str(e)
        logging.error(f"Error in process_otp: {error_msg}")
        
        if driver:
            snap(driver, "Error_OTP_Process")
            
            media = []
            files = sorted(glob.glob("step_*.png"))
            for f in files[-10:]: 
                media.append(InputMediaPhoto(open(f, 'rb')))
                
            if media:
                try:
                    await update.message.reply_media_group(media=media)
                except:
                    pass
                    
            await update.message.reply_text(
                f"⚠️ **Error vachindi!**\n\n📸 Screenshots chudu ekkada fail ayyindo thelustundi.\n\n`{error_msg[:300]}`", 
                parse_mode="Markdown"
            )
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
