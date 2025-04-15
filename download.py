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
from selenium.common.exceptions import InvalidArgumentException, \
    TimeoutException, ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains
logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)

WEBSITE = 'https://earthexplorer.usgs.gov/'
CHROMEDRIVER = which('chromedriver')
SERVICE = Service(executable_path=CHROMEDRIVER)
DRIVER = webdriver.Chrome(service=SERVICE)
ELEMENT_WAIT = 10  # default time to wait for element to appear
ACTIONS = ActionChains(DRIVER)

def download(url=WEBSITE, pattern='.*_3arc_'):
    DRIVER.get(url)
    click('//div[@id="tab2" and text()="Data Sets"]')  # Data Sets tab
    click('//li[@id="cat_207"]//span/div/strong[text()="Digital Elevation"]')
    click('//li[@id="cat_1103"]//span/div/strong[text()="SRTM"]')
    click('//input[@id="coll_5e83a43c37d31d83"]')  # SRTM Void Filled
    click('//div[@id="tab3" and text()="Additional Criteria"]')
    click('//a[@title="Resolution"]/following-sibling::i')
    click('//select[@id="5e83a43cde24c7d0_1"]')
    if '_3arc_' in pattern:
        click('//option[@value="3-ARC"]')
    elif '_1arc_' in pattern:
        click('//option[@value="1-ARC"]')
    else:
        click('//option[@value=""]')  # default, all resolutions
    click('//div[@id="tab4" and text()="Results"]')  # Results tab
    time.sleep(600)  # give developer time to locate problems before closing

def click(identifier, idtype=By.ID):
    if identifier.startswith('/'):
        idtype = By.XPATH
    try:
        element = WebDriverWait(DRIVER, ELEMENT_WAIT).until(
            expected_conditions.presence_of_element_located(
                (idtype, identifier)
            )
        )
        ACTIONS.move_to_element(element).perform()
        element.click()
    except InvalidArgumentException:
        logging.error('invalid argument "%s", %s', identifier, idtype)
    except TimeoutException:
        logging.error('timed out waiting for "%s", %s', identifier, idtype)
    except ElementClickInterceptedException:
        logging.error('element "%s", %s not clickable', identifier, idtype)

if __name__ == '__main__':
    download(*sys.argv[1:])

# vim: tabstop=8 expandtab softtabstop=4 shiftwidth=4
