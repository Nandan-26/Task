eCourts Case Scraper
A Python command-line tool to fetch case status and listing information from the Indian eCourts services portal. This script automates the process of looking up a case by its Case Number Record (CNR).

Features

Search by CNR: Fetches the current status and next hearing date for any given CNR.

Listing Check: Automatically checks if the case is listed for today or tomorrow.

CAPTCHA Helper: Opens the CAPTCHA image for you to solve, making the process semi-automated.

Data Export: Saves the fetched case details into a structured JSON file for easy access and record-keeping.

Requirements

Python 3.7+

Google Chrome browser installed on your system.

The script uses the following Python libraries:

selenium

webdriver-manager

beautifulsoup4

Pillow

Installation

Clone the repository or download the app.py script.

Install the required Python packages using pip:

pip install selenium webdriver-manager beautifulsoup4 Pillow


Usage

You can run the script from your terminal. The primary way to use it is with the --cnr flag.

Syntax:

python app.py --cnr <YOUR_CNR_NUMBER>


Example:

Open your terminal or command prompt.

Navigate to the directory where you saved app.py.

Run the script with a sample CNR number:

python app.py --cnr DLCT010000042016


How It Works

When you run the command, a new Chrome browser window will open and navigate to the eCourts website.

The script will automatically enter the CNR number.

A CAPTCHA image file (captcha.png) will be saved in the same directory, and the script will attempt to open it using your default image viewer.

Look at the image and type the characters into the terminal where you are prompted.

The script will submit the information and parse the results page.

Output

The script provides output in two ways:

Console Output: Key details like the court name, next hearing date, and listing status are printed directly to your terminal.

--- Case Status ---
CNR: DLCT010000042016
Court: RADC, DELHI
Next Hearing: 25-11-2025
Status: Not listed in the next 2 days.
Note: The serial number is only available in the official cause list for the day.
Results saved to DLCT010000042016_result.json


JSON File: A detailed JSON file named <CNR_NUMBER>_result.json is created in the same directory. This file contains the structured data that was scraped.

{
    "cnr": "DLCT010000042016",
    "case_type": "Suit",
    "court_name": "RADC, DELHI",
    "next_hearing_date": "25-11-2025",
    "is_listed_soon": false,
    "listing_status": "Not listed in the next 2 days."
}


Note on --causelist

The --causelist feature is currently a placeholder. The structure for cause lists varies significantly between different courts, making a universal downloader complex. The recommended and most reliable method for checking a specific case is by using the --cnr search.
