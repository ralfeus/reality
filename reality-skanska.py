#!/usr/bin/env python3
from reality_importer import BaseImporter 

from datetime import datetime
import json
import pymongo
import re
import urllib.request
import requests
import lxml.html
from lxml.cssselect import CSSSelector
import math

selItems = CSSSelector('div.entry')
selLastPage = CSSSelector('li.pagination-link>a')
selIdentification = CSSSelector('h3.entry-title')
selLayout = CSSSelector('div[class="entry-meta meta"]>div.meta-value')
selTotalFloorArea = CSSSelector('div.meta-area>div.meta-value')
#selProject = CSSSelector('div.tile div.grid div.g-9.m-12.s-12.xs-12 div.grid div.g-6.m-12.s-12.xs-12 div.grid div.g-6')
selLocation = CSSSelector('div.entry-subheader>p')
selFloor = CSSSelector('div.meta-floor>div.meta-value')
selOrientation = CSSSelector('div[class="entry-meta meta"]>div.meta-value')
selPrice = CSSSelector('div.meta-price>div.meta-value')
selURL = CSSSelector('a.entry-link')

def get_document_from_url(url, headers=None):
    with requests.get(url, headers={'X-Requested-With': 'XMLHttpRequest'}) as request:
#     with urllib.request.urlopen(url) as request:
#         content = request.read().decode()
        doc = lxml.html.fromstring(request.json()['content'])
        return doc

def get_pages(url):
    with requests.get(url, headers={'X-Requested-With': 'XMLHttpRequest'}) as response:
        items = response.json()['apartments_count']
        entries_per_page = 12
        pages = math.ceil(items / entries_per_page)
        return pages

#mongo_client = pymongo.MongoClient("mongodb+srv://dbuser:PqUSHv9MdYDGYC4Zil62@test-ytcpu.mongodb.net/test?retryWrites=true&w=majority")
mongo_client = pymongo.MongoClient()

db = mongo_client['reality']
collection = db['product']
raw_collection = db['skanska']
print("Connected to DB")
page = 1
pages = 1000
skanska_url = 'https://reality.skanska.cz/byty'
while page <= pages:
    doc = get_document_from_url(f'{skanska_url}?p1000={page}')
    items = selItems(doc) 
    print(len(items))
    for item in items:
        json_doc = {
            "url": selURL(item)[0].get('href'),
            "identification": selIdentification(item)[0].text.strip(),
            "layout": selLayout(item)[0].text.strip(),
            "totalFloorArea": float(re.search('[0-9\.]+', selTotalFloorArea(item)[0].text, re.MULTILINE).group()),
            "location": selLocation(item)[0].text.strip(),
            #"project": selProject(item)[1].text,
            "floor": selFloor(item)[0].text.strip(),
            "orientation":selOrientation(item)[1].text.strip(),
            "priceWithVAT": int(re.sub('\D', '', selPrice(item)[0].text)),
            "timeAdded": datetime.now()
        }
        raw_collection.insert_one(json_doc)
#         collection.insert_one({
#            "vendor": "Skanska",
#            "id": json_doc['identification'],
#            "timeAdded": json_doc['timeAdded'],
#            "layout": json_doc['layout'],
#            "totalFloorArea": json_doc['totalFloorArea'],
#            "priceWithVAT": json_doc['priceWithVAT']
#         })
        BaseImporter.add_product({
            'vendor': "Skanska",
            'id': json_doc['identification'],
            'layout': json_doc['layout'],
            'total_floor_area': json_doc['totalFloorArea'],
            'price': json_doc['priceWithVAT'],
            'latitude': 0,
            'longitude': 0,
            'type': 1,
            'closest_public_transport_stop_name': '',
            'closest_public_transport_stop_distance': 0
        })
    if pages == 1000:
        pages = get_pages(skanska_url)    
    print("Got page {} of {}".format(page, pages))
    page += 1
BaseImporter.commit()