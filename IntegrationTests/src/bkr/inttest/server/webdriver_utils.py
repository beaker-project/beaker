
from selenium import webdriver
from bkr.inttest import data_setup, get_server_base

def login(browser, user=None, password=None):
    if user is None and password is None:
        user = data_setup.ADMIN_USER
        password = data_setup.ADMIN_PASSWORD
    browser.get(get_server_base())
    browser.find_element_by_link_text('Login').click()
    browser.find_element_by_name('user_name').send_keys(user)
    browser.find_element_by_name('password').send_keys(password)
    browser.find_element_by_name('login').click()

def click_submenu_item(browser, menu_item, submenu_item):
    """
    Clicks on an item within a submenu, such as Reports -> CSV.
    WebDriver makes this trickier than you might think...
    """
    webdriver.ActionChains(browser).move_to_element(browser.find_element_by_xpath(
            '//ul[@id="menu"]/li[normalize-space(text())="%s"]' % menu_item)).perform()
    browser.find_element_by_link_text(submenu_item).click()

def is_text_present(browser, text):
    return bool(browser.find_elements_by_xpath(
            '//*[contains(text(), "%s")]' % text.replace('"', r'\"')))
