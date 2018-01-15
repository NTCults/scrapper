import requests
from lxml import html
import csv

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

def get_full_data():
    s = requests.session()

    data = {
        'action': 'ico_show_more',
        'ico_paged': 5
    }
    d = s.post('https://icosource.io/wp-admin/admin-ajax.php', data)
    data = html.fromstring(d.content)
    print('*' * 80)
    print(data[0].attrib)

    d = s.get(URL)
    return d

if __name__ == '__main__':
    get_full_data()

    result_array = []

    res = requests.get(URL)
    # res = get_full_data()
    data = html.fromstring(res.content)

    container_elements = data.xpath('//*[@class="col-md-12 lp-grid-box-contianer list_view card1 lp-grid-box-contianer1 "]')
    print(container_elements)
    for el in container_elements:
        # main page data
        url_source = el.attrib['data-posturl']
        name = el[0][1][0][0][0].text
        date = el[0][1][0][1][0].text

        # ico_page data
        ico_page = requests.get(url_source)
        ico_data = html.fromstring(ico_page.content)

        descr = ico_data.xpath('//*[@id="details"]/div/p[1]/text()')[0]

        dev_xpath ='//*[@id="page"]/section/div[2]/div/div/div[2]/div/div/div[2]/ul/li[4]/a'
        developer = get_link(ico_data, dev_xpath)

        site_xpath = ('//*[@id="page"]/section/div[2]/div/div/div[2]/div/div[1]/div[2]/ul/li[2]/a'
            if check_location(ico_data) else '//*[@id="page"]/section/div[2]/div/div/div[2]/div/div/div/ul/li[1]/a')
        site = get_link(ico_data, site_xpath)

        whitepaper_link_xpath = ('//*[@id="page"]/section/div[2]/div/div/div[2]/div/div[1]/div[2]/ul/li[3]/a' 
            if check_location(ico_data) else '//*[@id="page"]/section/div[2]/div/div/div[2]/div/div/div/ul/li[2]/a')
        whitepaper_link = get_link(ico_data, whitepaper_link_xpath)

        data_row = {
            'url_source': url_source,
            'name': name,
            'date': date,
            'descr': descr,
            'developer': developer,
            'site': site,
            'whitepaper_link': whitepaper_link
        }
        result_array.append(data_row)
        print(data_row)

    save_to_csv(result_array)
