#!/usr/bin/env python3
from reality_importer import BaseImporter 

from datetime import datetime
import json
import pymongo
import re
import urllib.request
import lxml.html
from lxml.cssselect import CSSSelector
# from tqdm import tqdm

selItems = CSSSelector('div.item-tiles.mt-5>div.grid>div.g-12.m-6')
selLastPage = CSSSelector('.pagination li:last-child a')
selLastButOnePage = CSSSelector('.pagination li:nth-last-child(2) a')
selIdentification = CSSSelector('div.tile div.grid div.g-9.m-12.s-12.xs-12 div.grid div.g-6.m-12.s-12.xs-12 div.grid div.g-6 strong')
selLayout = CSSSelector('div.tile div.grid div.g-9.m-12.s-12.xs-12 div.grid div.g-6.m-12.s-12.xs-12 div.grid div.g-3 strong')
selTotalFloorArea = CSSSelector('div.tile div.grid div.g-9.m-12.s-12.xs-12 div.grid div.g-6.m-12.s-12.xs-12 div.grid div.g-3 div.m-a-r.s-a-r.xs-a-r strong')
selLayoutDescription = CSSSelector('div.tile div.grid div.g-9.m-12.s-12.xs-12 div.grid div.g-6.m-12.s-12.xs-12')
selProject = CSSSelector('div.tile div.grid div.g-9.m-12.s-12.xs-12 div.grid div.g-6.m-12.s-12.xs-12 div.grid div.g-6')
selFloor = CSSSelector('div.tile div.grid div.g-9.m-12.s-12.xs-12 div.grid div.g-6.m-12.s-12.xs-12 div.grid div.g-3')
selOrientation = CSSSelector('div.tile div.grid div.g-9.m-12.s-12.xs-12 div.grid div.g-6.m-12.s-12.xs-12 div.grid div.g-3 div.m-a-r.s-a-r.xs-a-r')
selPrice = CSSSelector('div.price-info div.grid div.g-6.m-10.s-10.xs-10 div.grid div.g-12.m-6.s-4.xs-6.m-inverse.s-inverse.xs-inverse div.a-r strong')
selUrl = CSSSelector('a.tile-link')

def get_document_from_url(url):
    with urllib.request.urlopen(url) as request:
        content = request.read().decode()
        doc = lxml.html.fromstring(content)
        return doc

def get_pages(document):
    txtNextPage = '»'
    last_pagination = selLastPage(document)[0].text
    if last_pagination == txtNextPage:
        return int(selLastButOnePage(document)[0].text)
    else:
        return int(last_pagination)

#mongo_client = pymongo.MongoClient("mongodb+srv://dbuser:PqUSHv9MdYDGYC4Zil62@test-ytcpu.mongodb.net/test?retryWrites=true&w=majority")
mongo_client = pymongo.MongoClient()
db = mongo_client['reality']
collection = db['product']
raw_collection = db['finep']
print("Connected to DB")
page = 1
pages = 1000
while page <= pages:
    doc = get_document_from_url('https://www.finep.cz/cs/vyhledavani?page={}'.format(page))
    items = selItems(doc) 
    for item in items:
        json_doc = {
            "identification": selIdentification(item)[0].text,
            "layout": selLayout(item)[0].text,
            "totalFloorArea": float(re.search('[0-9,]+', selTotalFloorArea(item)[0].text, re.MULTILINE).group().replace(',', '.')),
            "layoutDescription": lxml.html.tostring(selLayoutDescription(item)[1]),
            "project": selProject(item)[1].text,
            "floor": selFloor(item)[2].text,
            "orientation":selOrientation(item)[1].text,
            "priceWithVAT": int(re.sub('\D', '', selPrice(item)[0].text)),
            "timeAdded": datetime.now(),
            "url": selUrl(item)[0].get('href')
        }
        raw_collection.insert_one(json_doc)
#         collection.insert_one({
#             "vendor": "Finep",
#             "id": json_doc['identification'],
#             "timeAdded": json_doc['timeAdded'],
#             "layout": json_doc['layout'],
#             "totalFloorArea": json_doc['totalFloorArea'],
#             "priceWithVAT": json_doc['priceWithVAT']
#         })
        BaseImporter.add_product({
            'vendor': "Finep",
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
        pages = get_pages(doc)    
    print("Got page {} of {}".format(page, pages))
    page += 1
BaseImporter.commit()