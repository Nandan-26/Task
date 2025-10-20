import argparse
import json
import logging
import os
import re
import time
from datetime import date, datetime, timedelta
from PIL import Image

# --- Selenium Imports ---
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
BASE_URL = "https://services.ecourts.gov.in/ecourtindia_v6/"

# --- Helper Functions ---

def setup_driver():
    """Initializes and returns a Selenium WebDriver instance."""
    chrome_options = Options()
    # For CAPTCHA, it's often more reliable to run with a visible browser.
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1280,720")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36")
    
    logging.info("Setting up Chrome driver...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

def handle_captcha(driver, captcha_id='captcha_image'):
    """
    Saves the CAPTCHA image, prompts the user for input, and returns it.
    Handles StaleElementReferenceException by retrying the screenshot.
    """
    screenshot_path = 'captcha.png'
    for i in range(3): # Try up to 3 times
        try:
            # Wait for the element to be present and locate it
            captcha_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, captcha_id))
            )
            # Take the screenshot immediately after locating
            captcha_element.screenshot(screenshot_path)

            # If screenshot is successful, proceed
            try:
                Image.open(screenshot_path).show()
                logging.info("CAPTCHA image opened in your default image viewer.")
            except Exception:
                logging.warning(f"Could not open image automatically. Please open '{screenshot_path}' manually.")

            # Prompt user for input
            captcha_text = input("Please enter the CAPTCHA text from the image: ")
            os.remove(screenshot_path) # Clean up the image file
            return captcha_text

        except StaleElementReferenceException:
            logging.warning(f"CAPTCHA element became stale. Retrying ({i+1}/3)...")
            time.sleep(1) # Short delay before retrying
        except TimeoutException:
            logging.error("Could not find the CAPTCHA image on the page.")
            return None
    
    logging.error("Failed to capture CAPTCHA after multiple attempts.")
    return None


def search_by_cnr(cnr):
    """
    Searches eCourts by CNR number and checks for recent listings.
    """
    driver = setup_driver()
    try:
        logging.info(f"Navigating to eCourts CNR search page for CNR: {cnr}")
        driver.get(BASE_URL)

        # Wait for the CNR input field to be clickable and enter the CNR
        cnr_input = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, 'cino'))
        )
        cnr_input.send_keys(cnr)
        
        # Handle the CAPTCHA
        captcha_text = handle_captcha(driver)
        if not captcha_text:
            return

        driver.find_element(By.ID, 'fcaptcha_code').send_keys(captcha_text)
        
        # Find and click the search button, waiting for it to be clickable
        logging.info("Submitting CNR and CAPTCHA...")
        search_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'search-btn'))
        )
        search_button.click()
        
        # --- Parse the result page ---
        try:
            # Wait for the case status details table to appear
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, 'case_status_details'))
            )
            logging.info("Successfully fetched case details.")
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Extract key information
            case_type_element = soup.find('label', class_='case_type_cls')
            court_name_element = soup.find('label', class_='court_name_cls')
            
            case_type = case_type_element.text.strip() if case_type_element else "N/A"
            court_name = court_name_element.text.strip() if court_name_element else "N/A"
            
            # Find the "Next Hearing Date"
            next_hearing_date_str = "Not listed"
            history_table = soup.find('table', class_='history_table')
            if history_table:
                # The hearing date is usually in the first row of the history table
                tbody = history_table.find('tbody')
                if tbody:
                    first_row = tbody.find('tr')
                    if first_row:
                        columns = first_row.find_all('td')
                        if len(columns) > 2:
                            next_hearing_date_str = columns[2].text.strip()
            
            result = {
                'cnr': cnr,
                'case_type': case_type,
                'court_name': court_name,
                'next_hearing_date': next_hearing_date_str,
                'is_listed_soon': False,
                'listing_status': 'Not listed in the next 2 days.'
            }

            # Check if the case is listed for today or tomorrow
            if next_hearing_date_str != "Not listed":
                try:
                    listing_date = datetime.strptime(next_hearing_date_str, '%d-%m-%Y').date()
                    today = date.today()
                    tomorrow = today + timedelta(days=1)
                    
                    if listing_date == today:
                        result['is_listed_soon'] = True
                        result['listing_status'] = f"Case is listed TODAY ({today.strftime('%d-%m-%Y')}) in {court_name}."
                    elif listing_date == tomorrow:
                        result['is_listed_soon'] = True
                        result['listing_status'] = f"Case is listed TOMORROW ({tomorrow.strftime('%d-%m-%Y')}) in {court_name}."
                
                except ValueError:
                    logging.warning(f"Could not parse date: {next_hearing_date_str}")
            
            # Print and save results
            logging.info("--- Case Status ---")
            logging.info(f"CNR: {result['cnr']}")
            logging.info(f"Court: {result['court_name']}")
            logging.info(f"Next Hearing: {result['next_hearing_date']}")
            logging.info(f"Status: {result['listing_status']}")
            logging.info("Note: The serial number is only available in the official cause list for the day.")

            # Save result to a JSON file
            output_filename = f"{cnr}_result.json"
            with open(output_filename, 'w') as f:
                json.dump(result, f, indent=4)
            logging.info(f"Results saved to {output_filename}")

        except TimeoutException:
            logging.error("Could not find case details. The CNR might be invalid, or the CAPTCHA failed.")

    finally:
        if 'driver' in locals() and driver:
            driver.quit()

def download_cause_list():
    """
    Navigates the cause list section and downloads PDFs for today.
    """
    logging.error("This feature is highly dependent on the specific court's website structure and is currently a placeholder.")
    logging.info("The CNR search feature is the recommended way to check for listings.")
    # NOTE: The cause list structure on the main portal is complex and varies greatly.
    # A robust implementation would require a more targeted approach for a specific state/district.
    # The previous attempt on the Delhi District Court site demonstrated the complexity.
    # For this script, we focus on the more reliable CNR search.

# --- Main Execution ---
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Scrape eCourts website for case listings.",
        epilog="Example: python app.py --cnr MHHC010000012023"
    )
    parser.add_argument("--cnr", type=str, help="Case Number Record (CNR) of the case.")
    parser.add_argument("--causelist", action="store_true", help="Download the cause list for today. (Feature placeholder)")
    
    args = parser.parse_args()
    
    if args.cnr:
        search_by_cnr(args.cnr)
    elif args.causelist:
        download_cause_list()
    else:
        parser.print_help()

