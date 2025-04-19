#!/usr/bin/python3
'''
download all SRTM3 data from USGS
'''
import sys, time, netrc, logging  # pylint: disable=multiple-imports
import os, posixpath, re  # pylint: disable=multiple-imports
from shutil import which
from urllib.parse import urlparse
from glob import glob
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import InvalidArgumentException, \
    TimeoutException, ElementClickInterceptedException, \
    StaleElementReferenceException, WebDriverException
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
STORAGE = os.path.expanduser('~/Documents/srtm')

def select(pattern='.*_3arc_', storage=STORAGE, url=WEBSITE):
    '''
    select desired SRTM quadrants
    '''
    login(url)
    os.makedirs(storage, mode=0o755, exist_ok=True)  # make sure it exists
    click('//div[@id="tab2" and text()="Data Sets"]')  # Data Sets tab
    click('//li[@id="cat_207"]//span/div/strong[text()="Digital Elevation"]')
    click('//li[@id="cat_1103"]//span/div/strong[text()="SRTM"]')
    click('//label[text()="SRTM Void Filled"]/../../div/input')  # check box
    click('//div[@id="tab3" and text()="Additional Criteria"]')
    click('//div/strong[text()="Resolution"]/../../div[2]/*[2]')
    logging.info('resolution selectbox should now be visible')
    select = find('//div[@class="col"]/select/option[3][@value="3-ARC"]/..')[0]
    arc = Select(select)
    # preselected default is "All" resolutions
    if '_3arc_' in pattern:
        arc.select_by_value('3-ARC')
    elif '_1arc_' in pattern:
        arc.select_by_value('1-ARC')
    click('//div[@id="tab4" and text()="Results"]')  # Results tab
    logging.info('first page of search results should now be showing')
    pagination = find('//input[@class="pageSelector" and @type="number"]')[0]
    page = int(pagination.get_attribute('min'))
    pages = int(pagination.get_attribute('max'))
    while page <= pages:
        logging.info('processing page %d of %d', page, pages)
        for row in get_rows():
            logging.info('row found: %s', row.get_attribute('id'))
            logging.debug(
                'row: %s',
                row.get_attribute('outerHTML').replace('\n', ' ')
            )
            img = row.find_element(
                By.XPATH,
                './td[@class="resultRowBrowse"]/a/img'
            )
            src = img.get_attribute('src')
            check = posixpath.splitext(posixpath.split(src)[1])[0]
            if re.compile(pattern).match(check):
                logging.info('adding %s to bulk download list', check)
                link = row.find_element(
                    By.XPATH,
                    './/a[starts-with(@class,"bulk")]'
                )
                button = link.find_element(By.XPATH, './div')
                logging.info('link class: %s', link.get_attribute('class'))
                ACTIONS.move_to_element(button).perform()
                if 'selected' not in link.get_attribute('class').split():
                    button.click()
                    logging.info('%s added to cart', check)
                else:
                    logging.info('%s was already in cart', check)
            if glob(os.path.join(storage, check + '_bil.zip')):
                logging.info('%s already downloaded, deselecting')
                button.click()
        click('//a[@role="button" and starts-with(text(), "Next ")]')
        while True:
            logging.debug('waiting for next page to load')
            try:
                pagination = find(
                    '//input[@class="pageSelector" and @type="number"]'
                )[0]
                newpage = int(pagination.get_attribute('value'))
                if newpage == page:
                    raise StaleElementReferenceException('Same page number')
                page = newpage
                break
            except StaleElementReferenceException:
                logging.info('page still stale')
                time.sleep(1)
    click('//div/input[@title="View Item Basket"]')

def login(url=WEBSITE):
    '''
    login to earthexplorer.usgs.gov
    '''
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

def find(identifier, idtype=By.ID, wait=ELEMENT_WAIT):
    '''
    find and return an element
    '''
    if identifier.startswith('/'):
        idtype = By.XPATH
    logging.info('looking for %s, idtype: %s', identifier, idtype)
    element = WebDriverWait(DRIVER, wait).until(
        # presence_of_element_located True doesn't mean it's interactable
        expected_conditions.element_to_be_clickable(
            (idtype, identifier)
        )
    )
    logging.info('found: %s: tag=%s, text="%s"', element, element.tag_name,
                  element.text)
    return element, idtype

def click(identifier, idtype=By.ID, wait=ELEMENT_WAIT):
    '''
    click specified element
    '''
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
    except StaleElementReferenceException:
        logging.error('element "%s", %s stale', identifier, idtype)
    except WebDriverException:
        logging.error('generic exception for element "%s", %s',
                      identifier, idtype)

def get_rows():
    '''
    load result rows into array
    '''
    rows = DRIVER.find_elements(
        By.XPATH, '//tr[starts-with(@id, "resultRow_")]'
    )
    return rows

def download(url=WEBSITE):
    '''
    download selected SRTM files
    '''
    login(url)
    time.sleep(3)  # give website a chance to update count after login
    link = find('//a[normalize-space(@class)="nav-link" and'
                ' @href="/order/index/"]'
               )[0]
    count = int(link.find_element(By.XPATH, './span').text)
    if count > 0:
        link.click()
        click('//button[text()="Start Order"]')
        click('//h4/i[@title="Click to Expand"]')
        time.sleep(7)  # takes a while to expand the list (about 5s)
        buttons = DRIVER.find_elements(By.XPATH, '//button')
        for button in buttons:
            logging.debug(button.get_attribute('outerHTML').replace('\n', ' '))
        page = int(find(
            '//button[contains(@class,"currentPage")]'
        )[0].get_attribute('value'))
        pages = int(find(
            '//button[contains(@class, " paginationButton") and'
            ' starts-with(normalize-space(text()), "Last ")]'
        )[0].get_attribute('page'))
        while page <= pages:
            rows = DRIVER.find_elements(
                By.XPATH,
                '//div[@class="sceneContainer row"]'
            )
            for row in rows:
                logging.debug(
                    'row: %s',
                    row.get_attribute('outerHTML').replace('\n', ' ')
                )
                selector = row.find_element(
                    By.XPATH,
                    './/select/option[contains(text(), "BIL")]'
                )
                ACTIONS.move_to_element(selector).perform()
                selector.click()
            click('//button[contains(@class, " paginationButton") and'
                  ' starts-with(normalize-space(text()), "Next ")]')
            time.sleep(7)  # let next page start loading
            while True:
                logging.debug('waiting for next page to load')
                try:
                    newpage = int(find(
                        '//button[contains(@class,"currentPage")]'
                    )[0].get_attribute('value'))
                    if newpage == page:
                        raise StaleElementReferenceException('Same page number')
                    page = newpage
                    break
                except (TimeoutException, StaleElementReferenceException):
                    logging.info('page still stale')
                    time.sleep(1)
    else:
        select(url=url)
    time.sleep(600)  # give developer time to locate problems before closing

if __name__ == '__main__':
    if len(sys.argv) > 1:
        SUBCOMMAND, ARGS = sys.argv[1], sys.argv[2:]
        eval(SUBCOMMAND)(*ARGS)
    else:
        download()

# vim: tabstop=8 expandtab softtabstop=4 shiftwidth=4
