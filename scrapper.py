import requests
import json
import csv
from lxml import html

URL = 'https://icosource.io'


def get_link(page_obj, xpath_expr):
    elements = page_obj.xpath(xpath_expr)
    if elements:
        return elements[0].attrib['href']
    return None

def save_to_csv(data_array):
    with open('ico_table.csv', 'w', newline='') as csvfile:
        fieldnames = ['url_source', 'name', 'date', 'descr', 'developer', 'site', 'whitepaper_link']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for item in data_array:
            writer.writerow(item)

def check_location(page_obj):
    loc = page_obj.xpath('//*[@id="page"]/section/div[2]/div/div/div[2]/div/div[1]/div[2]/ul/li[1]/a/span[1]/img')
    if not loc:
        return False
    return True

def get_json_data(data):
    data = data.content
    data = data.decode('utf-8')
    data = json.loads(data)
    return data

def get_additional_data():
    res_array = []
    ready = False
    index = 2

    while (not ready):
        data = {
            'action': 'ico_show_more',
            'ico_paged': index
        }
        index += 1

        d = requests.post('https://icosource.io/wp-admin/admin-ajax.php', data)
        data = get_json_data(d)
        # data = d.content
        # data = data.decode('utf-8')
        # data = json.loads(data)

        current = html.fromstring(data['html']['current'])
        current = current.xpath('//*[@class="lp-grid-box-description "]')
        if current:
            current = prepare_additional_data(current)

        upcoming = html.fromstring(data['html']['upcoming'])
        upcoming = upcoming.xpath('//*[@class="lp-grid-box-description "]')
        if upcoming:
            upcoming = prepare_additional_data(upcoming)

        res_array += current
        res_array += upcoming

        if (not current) and (not upcoming):
            ready = True

    return res_array


def prepare_additional_data(page):
    res_array = []
    for el in page:
        source = el[0][0][0].attrib['href']
        date = el[0][1][0].text
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
        if check_location(ico_data) else '//*[@id="page"]/section/div[2]/div/div/div[2]/div/div/div/ul/li[1]/a')
    site = get_link(ico_data, site_xpath)

    whitepaper_link_xpath = ('//*[@id="page"]/section/div[2]/div/div/div[2]/div/div[1]/div[2]/ul/li[3]/a' 
        if check_location(ico_data) else '//*[@id="page"]/section/div[2]/div/div/div[2]/div/div/div/ul/li[2]/a')
    whitepaper_link = get_link(ico_data, whitepaper_link_xpath)

    return {
        'name': name,
        'descr': descr,
        'developer':developer,
        'site': site
    } 


if __name__ == '__main__':
    result_array = []
    res = requests.get(URL)
    data = html.fromstring(res.content)

    container_elements = data.xpath('//*[@class="col-md-12 lp-grid-box-contianer list_view card1 lp-grid-box-contianer1 "]')

    for el in container_elements:
        # main page data
        url_source = el.attrib['data-posturl']
        name = el[0][1][0][0][0].text
        date = el[0][1][0][1][0].text

        data_row = get_ico_page_data(url_source)

        data_row['date'] = date
        data_row['url_source'] = url_source

        result_array.append(data_row)

    print('*' * 80)
    print('Processing additional data.')

    additional_data = get_additional_data()
    
    result_array += additional_data
    print(len(result_array))
    save_to_csv(result_array)
