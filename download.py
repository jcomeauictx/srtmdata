#!/usr/bin/python3
'''
download all SRTM3 data from USGS
'''
import sys, logging  # pylint: disable=multiple-imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)

WEBSITE = 'https://earthexplorer.usgs.gov/'

def download(url=WEBSITE, pattern='.*'):
    options = Options()
#   logging.debug('options: %s', options)
#   options.capabilities['browserName'] = 'chromium'  # not "chrome"
#   logging.debug('options.capabilities: %s', options.capabilities)
    service = Service(executable_path='/usr/bin/chromedriver')
    driver = webdriver.Chrome(options=options, service=service)
    driver.get(url)

if __name__ == '__main__':
    download(*sys.argv[1:])

# vim: tabstop=8 expandtab softtabstop=4 shiftwidth=4
