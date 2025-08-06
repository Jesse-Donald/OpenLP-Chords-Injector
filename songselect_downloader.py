# songselect.py

import re
import requests
import os
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def create_browser(cookies=None):
    options = Options()
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => false})"
    })

    driver.get("https://songselect.ccli.com/")

    if cookies:
        for cookie in cookies:
            try:
                driver.add_cookie({
                    "name": cookie["name"],
                    "value": cookie["value"],
                    "domain": cookie["domain"],
                    "path": "/"
                })
            except Exception as e:
                print(f"⚠️ Error adding cookie {cookie['name']}: {e}")
        print("✅ Cookies injected. Reloading page...")
        driver.get("https://songselect.ccli.com/")  # Refresh after injecting

    return driver


def search_song(title, artist=None, cookies=None):
    driver = create_browser(cookies=cookies)
    query = f"{title} {artist}" if artist else title
    query = query.strip().replace(" ", "+")
    url = f"https://songselect.ccli.com/search/results?search={query}"

    driver.get(url)

    print("🔐 If prompted, log in manually to SongSelect in the browser...")
    try:
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CLASS_NAME, "song-item"))
        )
    except:
        print("⚠️ Timeout or no results.")
        return None

    time.sleep(1)

    try:
        results = driver.find_elements(By.CSS_SELECTOR, "a.song-item")
        for r in results:
            href = r.get_attribute("href")
            title_element = r.find_element(By.CLASS_NAME, "title")
            song_title = title_element.text.strip()

            authors_element = r.find_element(By.CLASS_NAME, "authors")
            authors = authors_element.text.strip()

            print(f"🎵 Found: {song_title} — {authors}")
            print(f"🔗 Link: {href}")
            return {
                "title": song_title,
                "authors": authors,
                "url": f"{href}"
            }
        print("❌ No valid song entries found.")
    except Exception as e:
        print("⚠️ Error scraping results:", e)

    return None

def download_chordpro(song_url, cookies=None):
    driver = create_browser(cookies=cookies)
    wait = WebDriverWait(driver, 10)
    song_url = song_url + "/viewchordsheet"

    print(f"🌐 Opening song page: {song_url}")
    driver.get(song_url)

    wait = WebDriverWait(driver, 15)

    try:
        # Wait for the download button to appear
        btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn[title='Download']")))
        print("🎯 Found download button, clicking...")
        btn.click()
    except Exception as e:
        print(f"❌ Could not find or click download button: {e}")
        return None

    try:
        # Wait for the download button to appear
        btn = wait.until(EC.element_to_be_clickable((By.ID, "chordSheetDownloadChordProButton")))
        print("🎯 Found ChordPro download button, clicking...")
        btn.click()
    except Exception as e:
        print(f"❌ Could not find or click chordPro button: {e}")
        return None

    try:
        # Wait until the ChordPro text appears, usually inside a <pre> tag
        pre = wait.until(EC.presence_of_element_located((By.TAG_NAME, "pre")))
        chordpro_text = pre.text
        print("✅ ChordPro text captured successfully.")
    except Exception as e:
        print(f"⚠️ Failed to capture ChordPro text: {e}")
        return None
    driver.quit()
    return chordpro_text

def get_latest_chordpro_file(download_dir=None):
    if download_dir is None:
        download_dir = str(Path.home() / "Downloads")

    # Check for .cho or .chordpro files, sorted by modification time (newest first)
    files = [f for f in Path(download_dir).glob("*.txt")] + [f for f in Path(download_dir).glob("*.chordpro")]
    if not files:
        raise FileNotFoundError("No ChordPro files found in Downloads folder.")

    latest_file = max(files, key=os.path.getmtime)
    print(f"🎯 Found latest ChordPro file: {latest_file}")
    return latest_file

def read_chordpro_contents(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()