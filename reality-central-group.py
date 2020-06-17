#!/usr/bin/env python3
from reality_importer import BaseImporter 
from datetime import datetime
import json
import pymongo
import re
import urllib.request

def get_time_id():
    with urllib.request.urlopen("https://www.central-group.cz/api/system/time-version?timeId=&langId=") as url:
        return url.read().decode()

mongo_client = pymongo.MongoClient()
db = mongo_client['reality']
collection = db['product']
raw_collection = db['centralGroup']
total_products = 0
response = {}
print("Connected to DB")
time_id = get_time_id()
with urllib.request.urlopen('https://www.central-group.cz/api/apartment/search/stats?timeId={}&langId=1&sort=1&search=true'.format(time_id)) as url:
    response = json.loads(url.read().decode())
    print(response)
    total_products = response['totalCount']

print("Got ", total_products, "products from Central Group")
offset = 0
step = 50 
while offset < total_products:
    print("Getting", offset, "-", offset + step if offset + step < total_products else total_products, "items out of", total_products)
    with urllib.request.urlopen('https://www.central-group.cz/api/apartment/search?search=true&langId=1&timeId={}&offset={}&limit={}'.format(time_id, offset, step)) as url:
        response = json.loads(url.read().decode())
    offset += step
    
    for entry in response:
        entry['timeAdded'] = datetime.now()
        entry['url'] = 'https://www.central-group.cz/byt-detail/{}'.format(entry['catalogNumber'])
        # collection.insert_one({
        #     "vendor": "Central Group",
        #     "id": entry['catalogNumber'],
        #     "timeAdded": entry['timeAdded'],
        #     "layout": re.search('\\d\\+kk', entry['layoutLabel']).group(),
        #     "totalFloorArea": entry['totalFloorArea'],
        #     "priceWithVAT": entry['totalPriceWithVAT']
        # })
        BaseImporter.add_product({
            'vendor': "Central Group",
            'id': entry['catalogNumber'],
            'layout': re.search('\\d\\+kk', entry['layoutLabel']).group(),
            'total_floor_area': entry['totalFloorArea'],
            'price': entry['totalPriceWithVAT'],
            'latitude': 0,
            'longitude': 0,
            'type': 1,
            'closest_public_transport_stop_name': '',
            'closest_public_transport_stop_distance': 0, 
            'url': entry['url']
        })
    raw_collection.insert_many(response)
BaseImporter.commit()