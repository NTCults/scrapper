import requests
import json
import csv
from lxml import html

FILENAME = 'ico_table.csv'
URL = 'https://icosource.io'
PAGINATOR_URL = 'https://icosource.io/wp-admin/admin-ajax.php'

def get_link(page_obj, xpath_expr):
    elements = page_obj.xpath(xpath_expr)
    if elements:
        return elements[0].attrib['href']
    return None

def save_to_csv(data_array, filename):
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = ['url_source', 'name', 'date', 'descr', 'developer', 'site', 'whitepaper_link']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for item in data_array:
            writer.writerow(item)

def location_exists(page_obj):
    loc = page_obj.xpath('//*[@id="page"]/section/div[2]/div/div/div[2]/div/div[1]/div[2]/ul/li[1]/a/span[1]/img')
    if not loc:
        return False
    return True

def decode_json_data(data):
    data = data.content
    data = data.decode('utf-8')
    data = json.loads(data)
    return data

def get_paginated_nodes(data, key):
    page = html.fromstring(data['html'][key])
    nodes = page.xpath('//*[@class="lp-grid-box-description "]')
    nodes = parse_paginated_nodes(nodes)
    return nodes

def get_paginated_data():
    res_array = []
    ready = False
    index = 2
    while (not ready):
        data = {
            'action': 'ico_show_more',
            'ico_paged': index
        }
        index += 1

        response = requests.post(PAGINATOR_URL, data)
        data = decode_json_data(response)

        current = get_paginated_nodes(data, 'current')
        res_array += current

        upcoming = get_paginated_nodes(data, 'upcoming')
        res_array += upcoming

        if (not current) and (not upcoming):
            ready = True

    return res_array


def parse_paginated_nodes(page):
    res_array = []
    for el in page:
        source = el.find('.//h4/a').attrib['href']
        date = el.find('.//li[@class="middle"]').text

        data_row = get_ico_page_data(source)
        data_row['date'] = date
        data_row['url_source'] = source

        res_array.append(data_row)
    return res_array  

def get_ico_page_data(url_source):
    # ico page data
    ico_page = requests.get(url_source)
    ico_data = html.fromstring(ico_page.content)

    name = ico_data.xpath('//*[@id="details"]/div/h3/text()')[0]
    print('processing ', name)

    descr = ico_data.xpath('//*[@id="details"]/div/p[1]/text()')[0]

    dev_xpath ='//*[@id="page"]/section/div[2]/div/div/div[2]/div/div/div[2]/ul/li[4]/a'
    developer = get_link(ico_data, dev_xpath)

    site_xpath = ('//*[@id="page"]/section/div[2]/div/div/div[2]/div/div[1]/div[2]/ul/li[2]/a'
        if location_exists(ico_data) else '//*[@id="page"]/section/div[2]/div/div/div[2]/div/div/div/ul/li[1]/a')
    site = get_link(ico_data, site_xpath)

    whitepaper_link_xpath = ('//*[@id="page"]/section/div[2]/div/div/div[2]/div/div[1]/div[2]/ul/li[3]/a' 
        if location_exists(ico_data) else '//*[@id="page"]/section/div[2]/div/div/div[2]/div/div/div/ul/li[2]/a')
    whitepaper_link = get_link(ico_data, whitepaper_link_xpath)

    return {
        'name': name,
        'descr': descr,
        'developer':developer,
        'site': site,
        'whitepaper_link': whitepaper_link
    } 


if __name__ == '__main__':
    result_array = []
    res = requests.get(URL)
    data = html.fromstring(res.content)

    container_elements = data.xpath('//*[@class="col-md-12 lp-grid-box-contianer list_view card1 lp-grid-box-contianer1 "]')
    for el in container_elements:
        # main page data
        url_source = el.attrib['data-posturl']
        date = el.find('.//li[@class="middle"]').text

        data_row = get_ico_page_data(url_source)

        data_row['date'] = date
        data_row['url_source'] = url_source

        result_array.append(data_row)

    print('*' * 80)
    print('Processing additional data.')

    paginated_data = get_paginated_data()

    result_array += paginated_data
    print('Number of rows: ', len(result_array))
    save_to_csv(result_array, FILENAME)
