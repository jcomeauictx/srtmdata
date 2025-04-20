#!/usr/bin/python3
'''
download all SRTM3 data from USGS
'''
import sys, time, netrc, logging  # pylint: disable=multiple-imports
import os, posixpath, re, zipfile  # pylint: disable=multiple-imports
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
TEMPSTORE = os.path.expanduser('~/Documents/srtm')
STORAGE = '/usr/local/share/gis/srtm'  # subdirectories srtm1 and srtm3

def select(pattern='.*_3arc_', tempstore=TEMPSTORE, url=WEBSITE):
    '''
    select desired SRTM quadrants
    '''
    login(url)
    os.makedirs(tempstore, mode=0o755, exist_ok=True)  # make sure it exists
    click('//div[@id="tab2" and text()="Data Sets"]')  # Data Sets tab
    click('//li[@id="cat_207"]//span/div/strong[text()="Digital Elevation"]')
    click('//li[@id="cat_1103"]//span/div/strong[text()="SRTM"]')
    click('//label[text()="SRTM Void Filled"]/../../div/input')  # check box
    click('//div[@id="tab3" and text()="Additional Criteria"]')
    click('//div/strong[text()="Resolution"]/../../div[2]/*[2]')
    logging.info('resolution selectbox should now be visible')
    select = findonly(
        '//div[@class="col"]/select/option[3][@value="3-ARC"]/..'
    )
    arc = Select(select)
    # preselected default is "All" resolutions
    if '_3arc_' in pattern:
        arc.select_by_value('3-ARC')
    elif '_1arc_' in pattern:
        arc.select_by_value('1-ARC')
    click('//div[@id="tab4" and text()="Results"]')  # Results tab
    logging.info('first page of search results should now be showing')
    pagination = findonly('//input[@class="pageSelector" and @type="number"]')
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
            if glob(os.path.join(tempstore, check + '_bil.zip')):
                logging.info('%s already downloaded, deselecting')
                button.click()
        click('//a[@role="button" and starts-with(text(), "Next ")]')
        while True:
            logging.debug('waiting for next page to load')
            try:
                pagination = findonly(
                    '//input[@class="pageSelector" and @type="number"]'
                )
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
            formfield = findonly(
                '//form[@id="loginForm"]//input[@name="username"]'
            )
            formfield.send_keys(AUTHDATA[0])
            formfield = findonly(
                '//form[@id="loginForm"]//input[@name="password"]'
            )
            formfield.send_keys(AUTHDATA[2])
            click('//input[@id="loginButton"]')
    except TimeoutException:
        logging.info('no login button, assuming already logged in')
    logged_in = findonly('//a[@href="/logout/"]')
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
    try:
        element = WebDriverWait(DRIVER, wait).until(
            # NOTE: presence_of_element_located doesn't mean it's interactable
            expected_conditions.presence_of_element_located(
                (idtype, identifier)
            )
        )
        logging.info('found: %s: tag=%s, text="%s"', element, element.tag_name,
                      element.text)
    except TimeoutException:
        logging.error('`find` timed out')
        element = None
    return element, idtype

def findonly(identifier, idtype=By.ID, wait=ELEMENT_WAIT):
    '''
    like `find` but returns only the element, not the idtype
    '''
    return find(identifier, idtype, wait)[0]

def click(identifier, idtype=By.ID, wait=ELEMENT_WAIT):
    '''
    click specified element
    '''
    try:
        element, idtype = find(identifier, idtype, wait)
        ACTIONS.move_to_element(element).perform()
        WebDriverWait(DRIVER, wait).until(
            expected_conditions.element_to_be_clickable(
                (idtype, identifier)
            )
        )
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
    link = findonly(
        '//a[normalize-space(@class)="nav-link" and @href="/order/index/"]'
    )
    count = int(link.find_element(By.XPATH, './span').text)
    if count > 0:
        link.click()
        click('//button[text()="Start Order"]')
        click('//h4/i[@title="Click to Expand"]')
        time.sleep(7)  # takes a while to expand the list (about 5s)
        buttons = DRIVER.find_elements(By.XPATH, '//button')
        for button in buttons:
            logging.debug(button.get_attribute('outerHTML').replace('\n', ' '))
        page = int(findonly(
            '//button[contains(@class,"currentPage")]'
        ).get_attribute('value'))
        pages = int(findonly(
            '//button[contains(@class, " paginationButton") and'
            ' starts-with(normalize-space(text()), "Last ")]'
        ).get_attribute('page'))
        while page <= pages:
            logging.info('processing download page %d of %d', page, pages)
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
            if page < pages:
                click('//button[contains(@class, " paginationButton") and'
                      ' starts-with(normalize-space(text()), "Next ")]')
                time.sleep(7)  # let next page start loading
                while True:
                    logging.debug('waiting for next page to load')
                    try:
                        newpage = int(findonly(
                            '//button[contains(@class,"currentPage")]'
                        ).get_attribute('value'))
                        if newpage == page:
                            raise StaleElementReferenceException(
                                'Same page number'
                            )
                        page = newpage
                        break
                    except (TimeoutException, StaleElementReferenceException):
                        logging.info('page still stale')
                        time.sleep(1)
        click('//*[normalize-space(text())="Submit Product Selections"]')
    else:
        select(url=url)
    while True:
        time.sleep(600)  # wait until user closes window

def store(zipped, storage=STORAGE):
    '''
    unzip n00_w000_3arc_v2_bil.zip and store as STORAGE/srtm3/N00/N00W000.hgt

    STORAGE should ideally be owned by a user (you). this routine will
    attempt to create a subdirectory, srtm1 or srtm3, appropriate to the
    data being written, and a subsubdir to limit the number of files in each

    return is a *count*! a 1 does not indicate failure.
    '''
    pieces = os.path.splitext(os.path.basename(zipped))[0].split('_')
    logging.debug('pieces: %s', pieces)
    mapping = {'1arc': 'srtm1', '3arc': 'srtm3'}
    logging.debug('mapping: %s, key: "%s"', mapping, pieces[2])
    srtm = mapping[pieces[2]]
    subsubdir = pieces[0].upper()
    infile = '_'.join(pieces[:4]) + '.bil'
    outfile = os.path.join(
        storage, srtm, subsubdir, ''.join(pieces[:2]).upper() + '.hgt'
    )
    if os.path.exists(outfile):
        return 0  # don't overwrite
    os.makedirs(os.path.dirname(outfile), mode=0o755, exist_ok=True)
    with zipfile.ZipFile(zipped) as archive:
        with archive.open(infile) as zipdata, open(outfile, 'wb') as hgtdata:
            logging.debug('writing %s', outfile)
            hgtdata.write(zipdata.read())
    return 1

def store_all(tempstore=TEMPSTORE, storage=STORAGE):
    '''
    save all BIL data in permanent storage location
    '''
    zipfiles = glob(os.path.join(tempstore, '*_v2_bil.zip'))
    stored = 0
    for zipped in zipfiles:
        stored += store(zipped)
    logging.info('stored %d hgt files', stored)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        SUBCOMMAND, ARGS = sys.argv[1], sys.argv[2:]
        eval(SUBCOMMAND)(*ARGS)
    else:
        download()

# vim: tabstop=8 expandtab softtabstop=4 shiftwidth=4
