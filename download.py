#!/usr/bin/python3
'''
download all SRTM3 data from USGS
'''
import sys, time, logging  # pylint: disable=multiple-imports
from shutil import which
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions
logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)

WEBSITE = 'https://earthexplorer.usgs.gov/'
CHROMEDRIVER = which('chromedriver')

def download(url=WEBSITE, pattern='.*'):
    service = Service(executable_path=CHROMEDRIVER)
    driver = webdriver.Chrome(service=service)
    driver.get(url)
    click(driver, 'Data Sets', By.LINK_TEXT)
    time.sleep(600)  # give developer time to locate problems before closing

def click(driver, identifier, idtype=By.ID):
    try:
        element = WebDriverWait(driver, 10).until(
            expected_conditions.presence_of_element_located(
                (idtype, identifier)
            )
        )
        element.click()
    finally:
        pass
    
if __name__ == '__main__':
    download(*sys.argv[1:])

# vim: tabstop=8 expandtab softtabstop=4 shiftwidth=4
