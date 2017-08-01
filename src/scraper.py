"""Learning to web scrap."""
from bs4 import BeautifulSoup
import requests
import sys
import os
import re


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
    'Inspection_Closed_Establishment': 'A',
    'Violation_Points': '',
    'Violation_Red_Points': '',
    'Violation_Descr': '',
    'Fuzzy_Search': 'N',
    'Sort': 'H'
}


def get_inpsection_page(**kwargs):
    """requests.get(url) doesn't work."""
    url = INSPECTION_DOMAIN + INSPECTION_PATH
    params = INSPECTION_PARAMS.copy()
    for key, val in kwargs.items():
        if key in INSPECTION_PARAMS:
            params[key] = val
    # import pdb; pdb.set_trace()
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.content, resp.encoding


def load_inpsection_page():
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
        u'Total Inspecitons': samples
    }
    return data


if __name__ == '__main__':  # pragma: no cover
    kwargs = {
        'Inspection_Start': '2/1/2017',
        'Inspection_End': '6/1/2017',
        'Zip_Code': '98109'
    }
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        html, encoding = load_inpsection_page()
    else:
        html, encoding = get_inpsection_page(**kwargs)
    doc = parse_source(html, encoding)
    listings = extract_data_listings(doc)
    dct = {}
    for listing in listings:
        metadata = extract_restaurant_metadata(listing)
        score_data = extract_score_data(listing)
        both = dict(metadata, **score_data)
        dct.update({metadata['Business Name'][0]: both})
        first5pairs = {k: dct[k] for k in list(dct.keys())[:5]}
        for name, dictionary in first5pairs.items():
            print(name)
            for data, val in dictionary.items():
                print(data, val)
        print()
