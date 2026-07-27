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
    resume = args.resume or os.environ.get("NAUKRI_RESUME_PATH") or "./Resume.pdf"

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
        
    # Spoof a standard Windows desktop browser identity
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    
    # Strip automation indicators
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    # Overwrite the webdriver flag completely in the browser environment
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    
    return driver


def wait_for(driver, by, selector, timeout=20):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, selector))
    )


def wait_for_clickable(driver, by, selector, timeout=20):
    """Wait for element to be clickable (visible and enabled)"""
    return WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((by, selector))
    )


def login(driver, email, password):
    driver.get(LOGIN_URL)
    time.sleep(2)
    
    try:
        email_input = wait_for_clickable(driver, By.ID, "usernameField", timeout=15)
    except TimeoutException:
        try:
            email_input = wait_for_clickable(driver, By.NAME, "email", timeout=15)
        except TimeoutException:
            raise RuntimeError("Could not find the Naukri email field.")

    email_input.clear()
    email_input.send_keys(email)
    time.sleep(1)

    try:
        password_input = wait_for_clickable(driver, By.ID, "passwordField", timeout=15)
    except TimeoutException:
        try:
            password_input = wait_for_clickable(driver, By.NAME, "password", timeout=15)
        except TimeoutException:
            raise RuntimeError("Could not find the Naukri password field.")

    password_input.clear()
    password_input.send_keys(password)
    time.sleep(1)

    try:
        login_button = wait_for_clickable(
            driver, 
            By.XPATH, 
            "//button[@type='submit' or contains(text(),'Login') or contains(text(),'Login Now')]",
            timeout=15
        )
    except TimeoutException:
        raise RuntimeError("Could not find the Naukri login button.")

    # Scroll to ensure button is visible
    driver.execute_script("arguments[0].scrollIntoView(true);", login_button)
    time.sleep(1)
    
    login_button.click()
    
    # Wait until the browser successfully redirects away from the login page
    print("Waiting for login authentication to complete...")
    WebDriverWait(driver, 30).until(
        lambda d: "nlogin" not in d.current_url
    )
    time.sleep(3)
      

def upload_resume(driver, resume_path):
    print("Navigating to profile page...")
    driver.get(PROFILE_URL)
    time.sleep(5)

    driver.execute_script("window.scrollTo(0, 300);")
    time.sleep(2)

    try:
        print("Searching for file input field...")
        file_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((
                By.XPATH, 
                "//input[@type='file']"
            ))
        )
    except TimeoutException:
        try:
            driver.save_screenshot("error_profile_page.png")
        except:
            pass
        raise RuntimeError("Could not find any resume upload field on the profile page.")

    print("Making file input visible and uploading file...")
    driver.execute_script("""
        arguments[0].style.display = 'block';
        arguments[0].style.visibility = 'visible';
        arguments[0].style.opacity = '1';
        arguments[0].setAttribute('class', '');
    """, file_input)
    
    time.sleep(1)
    
    # Scroll to ensure element is in view
    driver.execute_script("arguments[0].scrollIntoView(true);", file_input)
    time.sleep(1)
    
    file_input.send_keys(os.path.abspath(resume_path))
    time.sleep(5)
    print("Resume uploaded successfully!")


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
