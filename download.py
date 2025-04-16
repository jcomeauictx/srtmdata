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
from selenium.webdriver.support.ui import Select
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
    if False:
        find('//label[text()="SRTM Void Filled"]')
        find('//label[text()="SRTM Void Filled"]/..')  # containing div
        find('//label[text()="SRTM Void Filled"]/../..')  # containing span
        find('//label[text()="SRTM Void Filled"]/../../div')  # span's 1st div
        find('//label[text()="SRTM Void Filled"]/../../div/input')  # checkbox
    click('//label[text()="SRTM Void Filled"]/../../div/input')  # check box
    click('//div[@id="tab3" and text()="Additional Criteria"]')
    if False:
        find('//div/strong[text()="Resolution"]')
        find('//div/strong[text()="Resolution"]/..')
        find('//div/strong[text()="Resolution"]/../..')
        find('//div/strong[text()="Resolution"]/../../div[2]')
        find('//div/strong[text()="Resolution"]/../../div[2]/*[2]')
    click('//div/strong[text()="Resolution"]/../../div[2]/*[2]')
    logging.debug('resolution selectbox should now be visible')
    time.sleep(10)  # pause for a moment to check
    select = find('//select/option[3][@value="3-ARC"]/..')[0]
    arc = Select(select)
    # preselected default is "All" resolutions
    if '_3arc_' in pattern:
        arc.select_by_value('3-ARC')
    elif '_1arc_' in pattern:
        arc.select_by_value('1-ARC')
    click('//div[@id="tab4" and text()="Results"]')  # Results tab
    time.sleep(600)  # give developer time to locate problems before closing

def find(identifier, idtype=By.ID):
    '''
    find and return an element
    '''
    if identifier.startswith('/'):
        idtype = By.XPATH
    logging.debug('looking for %s, idtype: %s', identifier, idtype)
    element = WebDriverWait(DRIVER, ELEMENT_WAIT).until(
        expected_conditions.presence_of_element_located(
            (idtype, identifier)
        )
    )
    logging.debug('found: %s: tag=%s, text="%s"', element, element.tag_name,
                  element.text)
    return element, idtype

def click(identifier, idtype=By.ID):
    try:
        element, idtype = find(identifier, idtype)
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
