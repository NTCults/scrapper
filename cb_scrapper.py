import requests
import json
import csv
from lxml import html
import re
from multiprocessing.dummy import Pool as ThreadPool


FILENAME = 'cb_ico_table.csv'
URL = 'https://icosource.io'
PAGINATOR_URL = 'https://icosource.io/wp-admin/admin-ajax.php'

xpath_expressions = {
    'main_page_container_element': '//*[@class="col-md-12 lp-grid-box-contianer list_view card1 lp-grid-box-contianer1 "]',
    'location_img': '//*[@id="page"]/section/div[2]/div/div/div[2]/div/div[1]/div[2]/ul/li[1]/a/span[1]/img',
    'ico_page_container': '//*[@class="lp-grid-box-description "]',
    'ico_page_name': '//*[@id="details"]/div/h3/text()',
    'ico_page_description': '//*[@id="details"]/div/p[1]/text()',
    'ico_page_developer': '//*[@id="page"]/section/div[2]/div/div/div[2]/div/div/div[2]/ul/li[4]/a',
    'ico_page_site': '//*[@id="page"]/section/div[2]/div/div/div[2]/div/div[1]/div[2]/ul/li[2]/a',
    'ico_page_site_secondary': '//*[@id="page"]/section/div[2]/div/div/div[2]/div/div/div/ul/li[1]/a',
    'ico_page_whitepaper_link': '//*[@id="page"]/section/div[2]/div/div/div[2]/div/div[1]/div[2]/ul/li[3]/a',
    'ico_page_whitepaper_link_secondary':'//*[@id="page"]/section/div[2]/div/div/div[2]/div/div/div/ul/li[2]/a'
}

class Scrapper:
    def __init__(self):
        self.data = []

    def save_to_csv(self, data_array, filename):
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['url_source', 'name', 'date', 'descr', 'developer', 'site', 'whitepaper_link']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for item in data_array:
                writer.writerow(item)

    def fetch_content(self, url):
        res = requests.get(url)
        if res.status_code == 200:
            return res.content
        else:
            raise requests.HTTPError

    def convert_to_lxml_tree(self, data):
        data = html.fromstring(data)
        return data

    def get_ico_page_data(self, obj):
        ico_data = self.fetch_content(obj['url_source'])
        additional_fields = self.parse_ico_page_data(ico_data)
        obj.update(additional_fields)
        return obj

    def parse_main_page_ico_data(self, data):
        data = self.convert_to_lxml_tree(data)
        result = []
        container_elements = data.xpath(xpath_expressions['main_page_container_element'])
        for el in container_elements:
            url_source = el.attrib['data-posturl']
            date = el.find('.//li[@class="middle"]').text
            result.append({
                'url_source': url_source,
                'date': date
            })
        return result

    def location_exists(self, page_obj):
        loc = page_obj.xpath(xpath_expressions['location_img'])
        if not loc:
            return False
        return True

    def get_link(self, page_obj, xpath_expr):
        elements = page_obj.xpath(xpath_expr)
        if elements:
            return elements[0].attrib['href']
        return None

    def parse_ico_page_data(self, page):
        page = self.convert_to_lxml_tree(page)

        name = page.xpath(xpath_expressions['ico_page_name'])[0]
        print('processing ', name)

        descr = page.xpath(xpath_expressions['ico_page_description'])[0]
        developer = self.get_link(page, xpath_expressions['ico_page_developer'])

        site_xpath = (xpath_expressions['ico_page_site'] if self.location_exists(page) 
            else xpath_expressions['ico_page_site_secondary'])
        site = self.get_link(page, site_xpath)

        whitepaper_link_xpath = (xpath_expressions['ico_page_whitepaper_link'] 
            if self.location_exists(page) else xpath_expressions['ico_page_whitepaper_link_secondary'])
        whitepaper_link = self.get_link(page, whitepaper_link_xpath)

        return {
            'name': name,
            'descr': descr,
            'developer':developer,
            'site': site,
            'whitepaper_link': whitepaper_link
        }

    def decode_json_data(self, data):
        data = data.content
        data = data.decode('utf-8')
        data = json.loads(data)
        return data

    def get_nodes_from_paginated_page(self, data, key):
        page = self.convert_to_lxml_tree(data['html'][key])
        nodes = page.xpath(xpath_expressions['ico_page_container'])
        return nodes

    def get_data_by_index(self, index):
        res_array = []
        data = {
            'action': 'ico_show_more',
            'ico_paged': index
        }
        response = requests.post(PAGINATOR_URL, data)
        data = self.decode_json_data(response)

        current = self.get_nodes_from_paginated_page(data, 'current')
        res_array += current

        upcoming = self.get_nodes_from_paginated_page(data, 'upcoming')
        res_array += upcoming

        return res_array

    def get_paginated_data(self):
        res_array = []
        index = 1
        while True:
            data = self.get_data_by_index(index)
            res_array += data
            index += 1
            if not data:
                break
        return res_array

    def parse_paginated_page_ico_data(self, page):
        res_array = []
        for el in page:
            source = el.find('.//h4/a').attrib['href']
            date = el.find('.//li[@class="middle"]').text

            res_array.append({
                'url_source': source,
                'date': re.sub(r"[\n\t\r]*", "", date)
            })
        return res_array

    def process_data(self, callback, arr):
        pool = ThreadPool(8)
        data = pool.map(callback, arr)
        pool.close()
        pool.join()
        return data

    def load_data(self):
        main_page_data = self.fetch_content(URL)
        main_page_data = self.parse_main_page_ico_data(main_page_data)
        main_page_data = self.process_data(self.get_ico_page_data, main_page_data)

        paginated_data = self.get_paginated_data()
        paginated_data = self.parse_paginated_page_ico_data(paginated_data)
        self.process_data(self.get_ico_page_data, paginated_data)

        self.data = main_page_data + paginated_data

    def save_data_to_file(self):
        self.save_to_csv(self.data, FILENAME)

if __name__ == '__main__':
    scrapper = Scrapper()
    scrapper.load_data()
    scrapper.save_data_to_file()
