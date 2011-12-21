
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

def is_text_present(browser, text):
    return bool(browser.find_elements_by_xpath(
            '//*[contains(text(), "%s")]' % text.replace('"', r'\"')))
