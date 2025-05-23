#!/usr/bin/python3
'''
download all SRTM3 data from USGS
'''
import sys, time, netrc, logging  # pylint: disable=multiple-imports
import os, posixpath, re, zipfile  # pylint: disable=multiple-imports
from shutil import which
from collections import defaultdict
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
        raise ValueError(f'no authentication data found for {HOSTNAME}')
except (FileNotFoundError, ValueError) as noauth:
    AUTHDATA = None
    logging.error('netrc failed, must log in via browser to download data: %s',
                  noauth)
CHROMEDRIVER = which('chromedriver')
ELEMENT_WAIT = 10  # default time to wait for element to appear
TEMPSTORE = os.path.expanduser('~/Documents/srtm')
STORAGE = '/usr/local/share/gis/srtm'  # subdirectories srtm1 and srtm3
PATTERN = os.getenv('SRTM_PATTERN') or '.*_3arc_'
# the following will be redefined in driver_init()
SERVICE = None
DRIVER = None
ACTIONS = None

def select(pattern=PATTERN, tempstore=TEMPSTORE, url=WEBSITE):
    '''
    select desired SRTM quadrants
    '''
    driver_init()
    login(url)
    os.makedirs(tempstore, mode=0o755, exist_ok=True)  # make sure it exists
    click('//div[@id="tab2" and text()="Data Sets"]')  # Data Sets tab
    click('//li[@id="cat_207"]//span/div/strong[text()="Digital Elevation"]')
    click('//li[@id="cat_1103"]//span/div/strong[text()="SRTM"]')
    click('//label[text()="SRTM Void Filled"]/../../div/input')  # check box
    click('//div[@id="tab3" and text()="Additional Criteria"]')
    click('//div/strong[text()="Resolution"]/../../div[2]/*[2]')
    logging.info('resolution selectbox should now be visible')
    selector = findonly(
        '//div[@class="col"]/select/option[3][@value="3-ARC"]/..'
    )
    arc = Select(selector)
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
        logging.info('processing selection page %d of %d', page, pages)
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
                logging.info('%s matches SRTM pattern', check)
                link = row.find_element(
                    By.XPATH,
                    './/a[starts-with(@class,"bulk")]'
                )
                button = link.find_element(By.XPATH, './div')
                logging.info('link class: %s', link.get_attribute('class'))
                zipglob = os.path.join(tempstore, check + '_bil.zip')
                if glob(zipglob):
                    logging.info(
                        '%s already saved, not adding to cart', zipglob
                    )
                else:
                    logging.info(
                        'verified %s not already downloaded', zipglob
                    )
                    ACTIONS.move_to_element(button).perform()
                    if 'selected' not in link.get_attribute('class').split():
                        button.click()
                        logging.info('%s added to cart', check)
                    else:
                        logging.info('%s was already in cart', check)
            else:
                logging.info('%s does not match pattern "%s"', check, pattern)
        if not nextpage(
            page,
            pages,
            '//a[@role="button" and starts-with(text(), "Next ")]',
            '//input[@class="pageSelector" and @type="number"]',
        ):
            break
        page += 1
    click('//div/input[@title="View Item Basket"]')

def login(url=WEBSITE):
    '''
    login to earthexplorer.usgs.gov
    '''
    driver_init()
    if findonly('//a[@href="/logout/"]', wait=0):
        return  # already logged in
    logging.debug('not logged in, attempting login now')
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

def nextpage(page, pages, button, text_element):
    '''
    advance to next page of web application
    '''
    if page < pages:
        click(button)
        while True:
            logging.debug('waiting for next page to load')
            try:
                newpage = int(findonly(text_element).get_attribute('value'))
                if newpage == page:
                    raise StaleElementReferenceException('Same page number')
                page = newpage
                break
            except StaleElementReferenceException:
                logging.info('page still stale')
                time.sleep(1)
        return True
    return False  # don't keep looping over final page

def download(url=WEBSITE):
    '''
    download selected SRTM files
    '''
    driver_init()
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
        try:
            pages = int(findonly(
                '//button[contains(@class, " paginationButton") and'
                ' starts-with(normalize-space(text()), "Last ")]'
            ).get_attribute('page'))
        except AttributeError:
            pages = 1  # no "Last" button when only one page of results
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
            if not nextpage(
                page,
                pages,
                '//button[contains(@class, " paginationButton") and'
                ' starts-with(normalize-space(text()), "Next ")]',
                '//button[contains(@class,"currentPage")]'
            ):
                break
            page += 1
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
    '''
    pieces = os.path.splitext(os.path.basename(zipped))[0].split('_')
    #logging.debug('pieces: %s', pieces)
    mapping = {'1arc': 'srtm1', '3arc': 'srtm3'}
    #logging.debug('mapping: %s, key: "%s"', mapping, pieces[2])
    srtm = mapping[pieces[2]]
    subsubdir = pieces[0].upper()
    infile = '_'.join(pieces[:4]) + '.bil'
    outfile = os.path.join(
        storage, srtm, subsubdir, ''.join(pieces[:2]).upper() + '.hgt'
    )
    if os.path.exists(outfile):
        logging.info('skipping existing %s', outfile)
        return 'skipped'  # don't overwrite
    os.makedirs(os.path.dirname(outfile), mode=0o755, exist_ok=True)
    with zipfile.ZipFile(zipped) as archive:
        with archive.open(infile) as zipdata, open(outfile, 'wb') as hgtdata:
            logging.info('writing %s', outfile)
            hgtdata.write(zipdata.read())
    return 'stored'

def store_all(tempstore=TEMPSTORE, storage=STORAGE, url=WEBSITE):
    '''
    save all BIL data in permanent storage location
    '''
    zipfiles = glob(os.path.join(tempstore, '*_v2_bil.zip'))
    count = defaultdict(int)
    for zipped in zipfiles:
        count[store(zipped, storage)] += 1
    logging.info('stored %d hgt files', count['stored'])
    logging.info('skipped %d pre-existing hgt files', count['skipped'])
    logging.info('total SRTM zip files examined: %d', sum(count.values()))
    if count['stored'] == 0:
        download(url)

def driver_init():
    '''
    redefine SERVICE, DRIVER, and ACTIONS globals and start Selenium driver
    '''
    global SERVICE, DRIVER, ACTIONS  # pylint: disable=global-statement
    if SERVICE is None:
        logging.info('reinitializing globals')
        SERVICE = Service(executable_path=CHROMEDRIVER)
        DRIVER = webdriver.Chrome(service=SERVICE)
        DRIVER.implicitly_wait(ELEMENT_WAIT)  # for DRIVER.find_elements
        ACTIONS = ActionChains(DRIVER)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        SUBCOMMAND, ARGS = sys.argv[1], sys.argv[2:]
        eval(SUBCOMMAND)(*ARGS)  # pylint: disable=eval-used
    else:
        store_all()

# vim: tabstop=8 expandtab softtabstop=4 shiftwidth=4
