#!/usr/bin/python3
'''
download all SRTM3 data from USGS
'''
import sys, logging  # pylint: disable=multiple-imports
from shutil import which
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)

WEBSITE = 'https://earthexplorer.usgs.gov/'
CHROMEDRIVER = which('chromedriver')

def download(url=WEBSITE, pattern='.*'):
    service = Service(executable_path=CHROMEDRIVER)
    driver = webdriver.Chrome(service=service)
    driver.get(url)
    click(driver, 'tab2')  # "Data Sets" tab

def click(driver, identifier, idtype=By.ID):
    element = driver.find_element(identifier, idtype)
    element.click()

if __name__ == '__main__':
    download(*sys.argv[1:])

# vim: tabstop=8 expandtab softtabstop=4 shiftwidth=4
