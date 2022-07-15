import csv

import requests

from typing import Generator
from bs4 import BeautifulSoup
from request_data import URL, HEADERS


# Header fields in CSV file.
CSV_FIELDNAMES = ['id', 'title', 'price', 'promo_price', 'link']

# Session data.
SESSION = requests.Session()
SESSION.headers = HEADERS


def list_to_int(nums: list[str]) -> int:
    '''Utility function to turn lists of individual digits (`str`)
    to integers.
    
    ["2", "3", "0", "1"] -> 2301
    '''
    return int(''.join(nums))

def create_csv(name: str) -> None:
    '''Creates a CSV file with specified headers.
    
    WARNING!
    Everytime you launch the script the data flushes
    and makes the headers anew. If you want to change this
    behaviour, change `w` in `open(...)` to `a`.

    :param name: - name of the CSV file to create.
    '''
    with open(name, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = CSV_FIELDNAMES
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

def write_to_csv(name: str, doll_info: dict[str, str|int]) -> None:
    '''Fills the CSV file with parsed data. Appends to the file.
    
    :param name: - name of the CSV file to append data to.
    :param doll_info: - parsed information about individual dolls.
    '''
    with open(name, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = CSV_FIELDNAMES
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writerow(doll_info)

def get_number_of_pages(soup: BeautifulSoup) -> int:
    '''Returns total count of pages to parse.
    
    This is done by dividing the number of all the dolls
    by 30 (the number of dolls on one page) and ceiling the result.
    As this function is called only once, I've decided to import
    math module inside this function as to not clutter the memory.

    :param soup: - required Beautiful Soup object obtained via
    `requests.get(...).text` method or any other.
    '''
    import math

    # Getting the correct_container
    left_panel_container = soup.find("aside")
    left_panel_buttons = left_panel_container.find_all("button")
    dolls_count_container = left_panel_buttons[-1].span.text

    dolls_count_ = [char for char in dolls_count_container if char.isdigit()]
    dolls_count = list_to_int(dolls_count_)

    # Getting the total number of pages
    dolls_on_one_page = 30
    pages = math.ceil(dolls_count / dolls_on_one_page)
    return pages

def fetch_data(url: str, session: requests.Session,
                parser: str ="html.parser") -> BeautifulSoup:
    '''Returns Beautiful Soup object, required for gathering
    info about the dolls.

    :param url: - dynamically changing URL according to the page
    the parser is processing.
    :param session: - `requests.Session` object which holds
    constant reques data during the parsing session.
    :param parser: - chosen parser for data processing.
    Read more @ https://www.crummy.com/software/BeautifulSoup/bs4/doc/#specifying-the-parser-to-use
    '''
    r = session.get(url)
    html_doc = r.text
    soup = BeautifulSoup(html_doc, parser)
    return soup

def get_dolls_list(soup: BeautifulSoup) -> Generator:
    '''Returns generator with Beautiful Soup's `PageElements`.
    
    This generator contains all the individual
    dolls' containers on the page, which are then
    iterated over to gather data.

    :param soup: - required Beautiful Soup object obtained via
    `requests.get(...).text` method or any other.
    '''
    # Getting the list of individual doll's container.
    dolls_container = soup.find("div", class_="xm")
    dolls_list = dolls_container.children
    return dolls_list

def get_dolls_info(dolls_list: Generator) -> Generator:
    '''Yields dictionary with keys corresponding to CSV headers
    and processed data.
    
    When no more dolls are available for sale via the web-site,
    the parser returns `N/A` instead of prices. The detection
    is done via catching the IndexError exception
    which occurs when trying to parse the price.

    When no promo_price is available, `None` is returned,
    and blank space is inserted into CSV instead, i.e.
    `3985244,Кукла Barbie Безграничные движения  1 GXF04,2599,,https://www.detmir.ru/product/index/id/3985244/`
    '''
    def has_promo() -> bool:
        '''Flag to detect if promo price is present.'''
        return len(doll_price_container.find_all("p")) == 2

    # Getting the id, name, price, promo_price, link.
    for doll in dolls_list:
        # Get doll's link and id.
        doll_link = doll.a["href"]
        doll_id_ = [char for char in doll_link if char.isdigit()]
        doll_id = list_to_int(doll_id_)

        # Get doll's name.
        doll_info_container = doll.find_all("div", class_="RQ")[0]
        doll_name = doll_info_container.p.text

        # Get doll's price and promo_price.
        doll_price_container = doll.find_all("div", class_="RQ")[1]

        try:
            _doll_price_0 = doll_price_container.find_all("p")[0].text
            doll_price_0 = (_doll_price_0
                                .replace('\u2009','')
                                .replace('₽', '')
                                .replace('\xa0',''))
            # Flag to point when we reached end of available dolls to parse.
            # These dolls are either available in shops
            # or they are completely out of stock.
            in_store = True
        except IndexError:
            doll_price_0 = doll_price_1 = "N/A"
            in_store = False

        if in_store:
            try:
                _doll_price_1 = doll_price_container.find_all("p")[1].text
                doll_price_1 = (_doll_price_1
                                    .replace('\u2009','')
                                    .replace('₽', '')
                                    .replace('\xa0',''))
            except IndexError:
                doll_price_1 = None
        
        if has_promo():
            doll_promo_price = doll_price_0
            doll_price = doll_price_1
        else:
            doll_price = doll_price_0
            doll_promo_price = doll_price_1

        doll_info = {
            "id": doll_id,
            "title": doll_name,
            "price": doll_price,
            "promo_price": doll_promo_price,
            "link": doll_link
        }
        yield doll_info

def main():
    # Initial data to start the cycle.
    page = 1
    total_pages = 1
    url = URL

    # Flushing the data and creating headers.
    create_csv('dolls.csv')

    while page < total_pages+1:
        soup = fetch_data(url, SESSION)
        dolls_list = get_dolls_list(soup)
        dolls_info = get_dolls_info(dolls_list)
        # Iterating over the yielded dictionaries.
        for doll in dolls_info:
            write_to_csv('dolls.csv', doll)
        
        if page == 1:
            total_pages = get_number_of_pages(soup)
        page += 1
        url = URL + f"page/{str(page)}"


if __name__ == "__main__":
    main()
