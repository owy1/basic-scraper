"""Learning to web scrap."""
from bs4 import BeautifulSoup
from operator import itemgetter, attrgetter
import requests
import sys
import os
import re
import json
import geocoder
import argparse
import pprint


__location__ = os.path.join(os.path.dirname(__file__), 'inspection_page.html')


INSPECTION_DOMAIN = 'http://info.kingcounty.gov'
INSPECTION_PATH = '/health/ehs/foodsafety/inspections/Results.aspx'
INSPECTION_PARAMS = {
    'Output': 'W',
    'Business_Name': '',
    'Business_Address': '',
    'Longitude': '',
    'Latitude': '',
    'City': '',
    'Zip_Code': '',
    'Inspection_Type': 'All',
    'Inspection_Start': '',
    'Inspection_End': '',
    'Inspection_Closed_Business': 'A',
    'Violation_Points': '',
    'Violation_Red_Points': '',
    'Violation_Descr': '',
    'Fuzzy_Search': 'N',
    'Sort': 'H'
}


def get_inspection_page(**kwargs):
    """requests.get(url) doesn't work."""
    url = INSPECTION_DOMAIN + INSPECTION_PATH
    params = INSPECTION_PARAMS.copy()
    for key, val in kwargs.items():
        if key in INSPECTION_PARAMS:
            params[key] = val
    # import pdb; pdb.set_trace()
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    # with open('inspection_page.html', "w") as fo:
    #     fo.write(resp.content.decode("utf-8"))
    return resp.content, resp.encoding


def load_inspection_page():
    """Load inspection_page.html in src directory."""
    with open(__location__, 'r') as f:
        content = f.read()
        encoding = 'utf-8'
    return content, encoding


def parse_source(html, encoding='utf-8'):
    """."""
    parsed = BeautifulSoup(html, 'html5lib', from_encoding=encoding)
    return parsed


def extract_data_listings(html):
    """."""
    id_finder = re.compile(r'PR[\d]+~')
    return html.find_all('div', id=id_finder)


def has_two_tds(elem):
    """Return True if the element is both a <tr> and contains exactly two <td> elements immediately within it."""
    is_tr = elem.name == 'tr'
    td_children = elem.find_all('td', recursive=False)
    has_two = len(td_children) == 2
    return is_tr and has_two


def clean_data(td):
    """."""
    data = td.string
    try:
        return data.strip(" \t\r\n:-")
    except AttributeError:
        return u""


def extract_restaurant_metadata(elem):
    """."""
    metadata_rows = elem.find('tbody').find_all(
        has_two_tds, recursive=False
    )
    rdata = {}
    current_label = ''
    for row in metadata_rows:
        key_cell, val_cell = row.find_all('td', recursive=False)
        new_label = clean_data(key_cell)
        current_label = new_label if new_label else current_label
        rdata.setdefault(current_label, []).append(clean_data(val_cell))
    return rdata


def is_inspection_row(elem):
    """Filter for inspection data."""
    is_tr = elem.name == 'tr'
    if not is_tr:
        return False
    td_children = elem.find_all('td', recursive=False)
    has_four = len(td_children) == 4
    this_text = clean_data(td_children[0]).lower()
    contains_word = 'inspection' in this_text
    does_not_start = not this_text.startswith('inspection')
    return is_tr and has_four and contains_word and does_not_start


def extract_score_data(elem):
    """."""
    inspection_rows = elem.find_all(is_inspection_row)
    samples = len(inspection_rows)
    total = high_score = average = 0
    for row in inspection_rows:
        strval = clean_data(row.find_all('td')[2])
        try:
            intval = int(strval)
        except (ValueError, TypeError):
            samples -= 1
        else:
            total += intval
            high_score = intval if intval > high_score else high_score
    if samples:
        average = total / float(samples)
    data = {
        u'Average Score': average,
        u'High Score': high_score,
        u'Total Inspections': samples
    }
    return data


def generate_results(sort='High Score', count=5, reverse=False, test=False):
    """."""
    kwargs = {
        'Inspection_Start': '2/1/2017',
        'Inspection_End': '6/1/2017',
        'Zip_Code': '98109'
    }
    if test:
        html, encoding = load_inspection_page()
    else:
        html, encoding = get_inspection_page(**kwargs)
    doc = parse_source(html, encoding)
    listings = extract_data_listings(doc)
    data_list = []
    for listing in listings[:count]:
        metadata = extract_restaurant_metadata(listing)
        score_data = extract_score_data(listing)
        metadata.update(score_data)
        data_list.append(metadata)
    if sort == 'High Score':
        sort = u'High Score'
    if sort == 'Average Score':
        sort = u'Average Score'
    if sort == 'Total Inspections':
        sort = u'Total Inspections'
    # import pdb; pdb.set_trace()
    try:
        data_list = sorted(data_list, key=itemgetter(sort),
                           reverse=False)
    except UnboundLocalError:
        pass

    for item in data_list[:count]:
        yield item


def get_geojson(result):
    """."""
    address = " ".join(result.get('Address', ''))
    if not address:
        return None
    # geocoded = geocoder.google(address)
    # return geocoded.geojson
    geocoded = geocoder.google(address)
    geojson = geocoded.geojson
    inspection_data = {}
    use_keys = (
        'Business Name', 'Average Score', 'Total Inspections',
        'High Score', 'Address',
    )
    for key, val in result.items():
        if key not in use_keys:
            continue
        if isinstance(val, list):
            val = " ".join(val)
        inspection_data[key] = val
        new_address = geojson['properties'].get('address')
        if new_address:
            inspection_data['Address'] = new_address
        geojson['properties'] = inspection_data
        return geojson


if __name__ == '__main__':  # pragma: no cover
    # test = len(sys.argv) > 1 and sys.argv[1] == 'test'

    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--sort',
                        help='select: Average Score, High Score, Total Inspections',
                        type=str)
    parser.add_argument('-c', '--count',
                        help="enter number of results",
                        type=int)
    parser.add_argument('-r', '--reverse',
                        help='select: True or False',
                        type=bool)
    args = parser.parse_args()

    total_result = {'type': 'FeatureCollection', 'features': []}
    for result in generate_results(args.sort, args.count, args.reverse):
        geo_result = get_geojson(result)
        pprint.pprint(geo_result)
        total_result['features'].append(geo_result)
    with open('my_map.json', 'w') as fh:
        json.dump(total_result, fh)

    # kwargs = {
    #     'Inspection_Start': '2/1/2017',
    #     'Inspection_End': '6/1/2017',
    #     'Zip_Code': '98109'
    # }
    # if len(sys.argv) > 1 and sys.argv[1] == 'test':
    #     html, encoding = load_inpsection_page()
    # else:
    #     html, encoding = get_inpsection_page(**kwargs)
    # doc = parse_source(html, encoding)
    # listings = extract_data_listings(doc)
    # dct = {}
    # for listing in listings:
    #     metadata = extract_restaurant_metadata(listing)
    #     score_data = extract_score_data(listing)
    #     both = dict(metadata, **score_data)
    #     dct.update({metadata['Business Name'][0]: both})
    #     first5pairs = {k: dct[k] for k in list(dct.keys())[:5]}
    #     for name, dictionary in first5pairs.items():
    #         print(name)
    #         for data, val in dictionary.items():
    #             print(data, val)
    #     print()
