#!/usr/bin/python3
'''
download all SRTM3 data from USGS
'''
import sys, time, netrc, logging  # pylint: disable=multiple-imports
import posixpath, re  # pylint: disable=multiple-imports
from shutil import which
from urllib.parse import urlparse
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
HOSTNAME = urlparse(WEBSITE).netloc
try:
    AUTHDATA = netrc.netrc().authenticators(HOSTNAME)
    if AUTHDATA is None:
        raise ValueError('no authentication data found for %s', HOSTNAME)
except (FileNotFoundError, ValueError) as noauth:
    AUTHDATA = None
    logging.error('netrc failed, must log in via browser to download data: %s',
                  noauth)
CHROMEDRIVER = which('chromedriver')
SERVICE = Service(executable_path=CHROMEDRIVER)
DRIVER = webdriver.Chrome(service=SERVICE)
ELEMENT_WAIT = 10  # default time to wait for element to appear
DRIVER.implicitly_wait(ELEMENT_WAIT)  # for DRIVER.find_elements
ACTIONS = ActionChains(DRIVER)

def download(url=WEBSITE, pattern='.*_3arc_'):
    DRIVER.get(url)
    try:
        click('//a[@href="/login"]', By.XPATH, 0)
        if not AUTHDATA:
            logging.info('waiting a bit for you to login manually')
            time.sleep(60)
        else:
            formfield = find('//form[@id="loginForm"]//input[@name="username"]')
            formfield[0].send_keys(AUTHDATA[0])
            formfield = find('//form[@id="loginForm"]//input[@name="password"]')
            formfield[0].send_keys(AUTHDATA[2])
            click('//input[@id="loginButton"]')
    except TimeoutException:
        logging.info('no login button, assuming already logged in')
    logged_in = find('//a[@href="/logout/"]')
    if not logged_in:
        logging.error('cannot download SRTM data without logging in')
        sys.exit(1)
    click('//div[@id="tab2" and text()="Data Sets"]')  # Data Sets tab
    click('//li[@id="cat_207"]//span/div/strong[text()="Digital Elevation"]')
    click('//li[@id="cat_1103"]//span/div/strong[text()="SRTM"]')
    click('//label[text()="SRTM Void Filled"]/../../div/input')  # check box
    click('//div[@id="tab3" and text()="Additional Criteria"]')
    click('//div/strong[text()="Resolution"]/../../div[2]/*[2]')
    logging.debug('resolution selectbox should now be visible')
    select = find('//div[@class="col"]/select/option[3][@value="3-ARC"]/..')[0]
    arc = Select(select)
    # preselected default is "All" resolutions
    if '_3arc_' in pattern:
        arc.select_by_value('3-ARC')
    elif '_1arc_' in pattern:
        arc.select_by_value('1-ARC')
    click('//div[@id="tab4" and text()="Results"]')  # Results tab
    logging.debug('first page of search results should now be showing')
    rows = DRIVER.find_elements(
        By.XPATH, '//tr[starts-with(@id, "resultRow_")]'
    )
    for row in rows:
        logging.debug('row found: %s: %s', row.get_attribute('id'),
                      row.get_attribute('outerHTML'))
        img = row.find_element(
            By.XPATH,
            './td[@class="resultRowBrowse"]/a/img'
        )
        src = img.get_attribute('src')
        check = posixpath.splitext(posixpath.split(src)[1])[0]
        if re.compile(pattern).match(check):
            options = row.find_element(
                By.XPATH,
                './/a[@class="download"]/div'
            )
            logging.debug('downloading %s', check)
            ACTIONS.move_to_element(options).perform()
            time.sleep(10)  # FIXME: artificial delay for debugging
            logging.debug('bringing up download options')
            options.click()
            # this brings up a popup window which is a page unto itself
            # download button is in the sibling div preceding "BIL 3 Arc-..."
            logging.debug('choosing BIL (same as .hgt format)')
            click(
                '//div[@class="name px-0"]'
                '[starts-with(normalize-space(text()), "BIL ")]/'
                '../div[1]/button'
            )
    time.sleep(600)  # give developer time to locate problems before closing

def find(identifier, idtype=By.ID, wait=ELEMENT_WAIT):
    '''
    find and return an element
    '''
    if identifier.startswith('/'):
        idtype = By.XPATH
    logging.debug('looking for %s, idtype: %s', identifier, idtype)
    element = WebDriverWait(DRIVER, wait).until(
        # presence_of_element_located True doesn't mean it's interactable
        expected_conditions.element_to_be_clickable(
            (idtype, identifier)
        )
    )
    logging.debug('found: %s: tag=%s, text="%s"', element, element.tag_name,
                  element.text)
    return element, idtype

def click(identifier, idtype=By.ID, wait=ELEMENT_WAIT):
    try:
        element, idtype = find(identifier, idtype, wait)
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
