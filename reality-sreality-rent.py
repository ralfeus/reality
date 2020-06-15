#!/usr/bin/env python3
from datetime import datetime
from datetime import time
from reality_importer import BaseImporter
from reality_prepare_rent_dataset import predict
import pymongo
import re

mongo_client = pymongo.MongoClient()

db = mongo_client['reality']
original_collection = db['sreality_all']
collection = db['product_rent']
raw_collection = db['sreality_rent']
print("Connected to DB")
layout = {
        2: '1+kk',
        3: '1+1',
        4: '2+kk',
        5: '2+1',
        6: '3+kk',
        7: '3+1',
        8: '4+kk',
        9: '4+1',
        10: '5+kk',
        11: '5+1',
        12: '6-a-vice'
}
items = original_collection.find({
    'seo.category_main_cb': 1, # Apartments
    'seo.category_type_cb': 2, # Selling
    'seo.locality': {'$regex': '^praha'},
    'timeAdded': {'$gt': datetime.combine(datetime.now().date(), time(0, 0, 0))}
})
print(f'Got {items.count()} items')
for entry in items:
    entry['url'] = 'https://www.sreality.cz/detail/pronajem/byt/{}/{}/{}'.format(
        layout[entry['seo']['category_sub_cb']] if entry['seo']['category_sub_cb'] in layout.keys() else 'atypický',
        entry['seo']['locality'],
        entry['hash_id'])
    entry['closestPublicTransportStop'] = BaseImporter.getClosestStop(entry['gps']['lat'], entry['gps']['lon'])
    collection.insert_one({
        "vendor": 'sreality',
        "id": entry['hash_id'],
        "timeAdded": entry['timeAdded'],
        'dateAdded': entry['dateAdded'],
        "layout": layout[entry['seo']['category_sub_cb']] if entry['seo']['category_sub_cb'] in layout.keys() else 'atypický',
        "totalFloorArea": re.search('\s+(\d+)\s+', entry['name']).groups()[0],
        "priceWithVAT": entry['price'],
        "latitude": entry['gps']['lat'],
        "longitude": entry['gps']['lon'],
        'closestPublicTransportStop': entry['closestPublicTransportStop']
    })
    try:
        raw_collection.insert(entry)
    except pymongo.errors.DuplicateKeyError:
        pass
