import argparse
import os
import sys
import time
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

LOGIN_URL = "https://www.naukri.com/nlogin/login"
PROFILE_URL = "https://www.naukri.com/mnjuser/profile"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Update Naukri resume by logging in and uploading a new CV file."
    )
    parser.add_argument("--email", help="Naukri login email or username")
    parser.add_argument("--password", help="Naukri login password")
    parser.add_argument(
        "--resume",
        help="Path to the resume file to upload",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode",
    )
    parser.add_argument(
        "--browser",
        choices=["chrome"],
        default="chrome",
        help="Browser to use for automation",
    )
    return parser.parse_args()


def get_credentials(args):
    email = args.email or os.environ.get("NAUKRI_EMAIL") or "aanshr.2000@gmail.com"
    password = args.password or os.environ.get("NAUKRI_PASSWORD") or "Aansh@123"
    resume = args.resume or os.environ.get("NAUKRI_RESUME_PATH") or "C:/Users/DELL/Downloads/Resume.pdf"

    if not email or not password or not resume:
        print("Error: email, password, and resume path are required.")
        print("Provide them via arguments or environment variables:")
        print("  NAUKRI_EMAIL, NAUKRI_PASSWORD, NAUKRI_RESUME_PATH")
        sys.exit(1)

    resume = os.path.expanduser(resume)
    if not os.path.isfile(resume):
        print(f"Error: resume file does not exist: {resume}")
        sys.exit(1)

    return email, password, resume


def create_driver(headless: bool):
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1600,1200")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = ChromeService(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def wait_for(driver, by, selector, timeout=20):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, selector))
    )


def login(driver, email, password):
    driver.get(LOGIN_URL)
    try:
        email_input = wait_for(driver, By.ID, "usernameField")
    except TimeoutException:
        try:
            email_input = wait_for(driver, By.NAME, "email")
        except TimeoutException:
            raise RuntimeError("Could not find the Naukri email field.")

    email_input.clear()
    email_input.send_keys(email)

    try:
        password_input = driver.find_element(By.ID, "passwordField")
    except NoSuchElementException:
        try:
            password_input = driver.find_element(By.NAME, "password")
        except NoSuchElementException:
            raise RuntimeError("Could not find the Naukri password field.")

    password_input.clear()
    password_input.send_keys(password)

    try:
        login_button = driver.find_element(By.XPATH, "//button[@type='submit' or contains(text(),'Login') or contains(text(),'Login Now')]")
    except NoSuchElementException:
        raise RuntimeError("Could not find the Naukri login button.")

    login_button.click()
    time.sleep(3)

    if "login" in driver.current_url.lower() or "otp" in driver.current_url.lower():
        print("Login may require additional input or OTP. Please complete login manually in the browser.")
        input("Press Enter after you have successfully logged in...")


def upload_resume(driver, resume_path):
    driver.get(PROFILE_URL)
    time.sleep(3)

    try:
        file_input = wait_for(
            driver,
            By.XPATH,
            "//input[@type='file' and (contains(@id,'attachCV') or contains(@name,'resume') or contains(@name,'cv'))]",
            timeout=15,
        )
    except TimeoutException:
        raise RuntimeError("Could not find the resume upload field on the profile page.")

    file_input.send_keys(resume_path)
    time.sleep(2)

    try:
        upload_button = driver.find_element(
            By.XPATH,
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'upload') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'save')]")
        
    except NoSuchElementException:
        print("Resume selected. If Naukri requires manual confirmation, please confirm in the browser.")
        return

    try:
        upload_button.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", upload_button)

    time.sleep(5)


def main():
    args = parse_args()
    email, password, resume_path = get_credentials(args)

    print("Starting Naukri resume update...")
    driver = create_driver(args.headless)
    try:
        login(driver, email, password)
        upload_resume(driver, resume_path)
        print("Resume update process finished. Verify on Naukri manually if needed.")
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
