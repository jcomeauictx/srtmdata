#!/usr/bin/python3
'''
download all SRTM3 data from USGS
'''
import sys
from selenium import webdriver

WEBSITE = 'https://earthexplorer.usgs.gov/'

def download(url=WEBSITE, pattern='.*'):
    driver = webdriver.Chrome()
    driver.get(url)

if __name__ == '__main__':
    download(*sys.argv[1:])

# vim: tabstop=8 expandtab softtabstop=4 shiftwidth=4
