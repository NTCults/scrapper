import requests
import json
import csv
from lxml import html
import re

FILENAME = 'cb_ico_table.csv'
URL = 'https://icosource.io'
PAGINATOR_URL = 'https://icosource.io/wp-admin/admin-ajax.php'

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
        container_elements = data.xpath('//*[@class="col-md-12 lp-grid-box-contianer list_view card1 lp-grid-box-contianer1 "]')
        for el in container_elements:
            # main page data
            url_source = el.attrib['data-posturl']
            date = el.find('.//li[@class="middle"]').text
            result.append({
                'url_source': url_source,
                'date': date
            })
        return result

    def location_exists(self, page_obj):
        loc = page_obj.xpath('//*[@id="page"]/section/div[2]/div/div/div[2]/div/div[1]/div[2]/ul/li[1]/a/span[1]/img')
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

        name = page.xpath('//*[@id="details"]/div/h3/text()')[0]
        print('processing ', name)

        descr = page.xpath('//*[@id="details"]/div/p[1]/text()')[0]

        dev_xpath ='//*[@id="page"]/section/div[2]/div/div/div[2]/div/div/div[2]/ul/li[4]/a'
        developer = self.get_link(page, dev_xpath)

        site_xpath = ('//*[@id="page"]/section/div[2]/div/div/div[2]/div/div[1]/div[2]/ul/li[2]/a'
            if self.location_exists(page) else '//*[@id="page"]/section/div[2]/div/div/div[2]/div/div/div/ul/li[1]/a')
        site = self.get_link(page, site_xpath)

        whitepaper_link_xpath = ('//*[@id="page"]/section/div[2]/div/div/div[2]/div/div[1]/div[2]/ul/li[3]/a' 
            if self.location_exists(page) else '//*[@id="page"]/section/div[2]/div/div/div[2]/div/div/div/ul/li[2]/a')
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
        nodes = page.xpath('//*[@class="lp-grid-box-description "]')
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
        ready = False
        index = 1
        while (not ready):
            data = self.get_data_by_index(index)
            res_array += data
            index += 1
            if not data:
                ready = True
        return res_array

    def parse_paginated_page_ico_data(self, page):
        res_array = []
        for el in page:
            source = el.find('.//h4/a').attrib['href']
            date = el.find('.//li[@class="middle"]').text

            # data_row = get_ico_page_data(source)
            # data_row['date'] = date
            # data_row['url_source'] = source

            res_array.append({
                'url_source': source,
                'date': re.sub(r"[\n\t\r]*", "", date)
            })
        return res_array  

    def start(self):
        main_page_data = self.fetch_content(URL)
        res = self.parse_main_page_ico_data(main_page_data)

        for i in res:
            self.get_ico_page_data(i)
        print(res)

        paginated_data = self.get_paginated_data()
        res2 = self.parse_paginated_page_ico_data(paginated_data)
        for i in res2:
            self.get_ico_page_data(i)

        print(res2)
        self.data = res + res2
        self.save_to_csv(self.data, FILENAME)

if __name__ == '__main__':
    scrapper = Scrapper()
    scrapper.start()
