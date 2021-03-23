#!/usr/bin/env python3
from reality_importer import BaseImporter 
from datetime import datetime
import json
import pymongo
import urllib.request
from tqdm import tqdm 

mongo_client = pymongo.MongoClient()

db = mongo_client['reality']
collection_sell = db['product']
collection_rent = db['product_rent']
raw_collection = db['bezrealitky']
total_products = 0
prague_boundaries = {
    'north': 50.18,
    'south': 49.97,
    'west': 14.22,
    'east': 14.71
}
offer_type = {
    'prodej': 1,
    'pronajem': 2
}
print("Connected to DB")
#with urllib.request.urlopen('https://www.bezrealitky.cz/api/record/markers?offerType=prodej&estateType=byt&boundary=[[{"lat":50.18,"lng":14.22},{"lat":50.18,"lng":14.71},{"lat":49.97,"lng":14.71},{"lat":49.97,"lng":14.22},{"lat":50.18,"lng":14.22}]]') as url:
response = BaseImporter.get_json_from_url('https://www.bezrealitky.cz/api/record/markers')
print("Inserting {} entries...".format(len(response)), end = '')
sell = rent = 0
for entry in tqdm(response):
    offer = entry['advertEstateOffer'][0]
    lat = float(eval(offer['gps'])['lat'])
    lon = float(eval(offer['gps'])['lng'])
    entry['timeAdded'] = datetime.now()
    entry['url'] = f'https://www.bezrealitky.cz/nemovitosti-byty-domy/{entry["uri"]}'
    entry['closestPublicTransportStop'] = BaseImporter.getClosestStop(lat, lon)
    if (prague_boundaries['south'] <= lat <= prague_boundaries['north'] and
        prague_boundaries['west'] <= lon <= prague_boundaries['east'] and
        entry['advertEstateOffer'][0]['keyEstateType'] == 'byt'):
        product_entry = {
                "vendor": "Bez realitky",
                "id": entry['id'],
                "timeAdded": entry['timeAdded'],
                "layout": entry['advertEstateOffer'][0]['keyDisposition'].replace('-', '+'),
                "totalFloorArea": entry['advertEstateOffer'][0]['surface'],
                "priceWithVAT": entry['advertEstateOffer'][0]['price'],
                "latitude": lat,
                "longitude": lon,
                'closestPublicTransportStop': entry['closestPublicTransportStop'],
                'url': entry['url']
            }
        BaseImporter.add_product({
            'vendor': product_entry['vendor'],
            'id': product_entry['id'],
            'layout': product_entry['layout'],
            'total_floor_area': product_entry['totalFloorArea'],
            'price': product_entry['priceWithVAT'],
            'latitude': product_entry['latitude'],
            'longitude': product_entry['longitude'],
            'type': offer_type.get(offer['keyOfferType']),
            'closest_public_transport_stop_name': product_entry['closestPublicTransportStop']['name'],
            'closest_public_transport_stop_distance': product_entry['closestPublicTransportStop']['distance'],
            'url': product_entry['url']
        })

#         if offer['keyOfferType'] == 'prodej':
#             sell += 1
#             collection_sell.insert_one(product_entry)
#         elif offer['keyOfferType'] == 'pronajem':
#             rent += 1
#             collection_rent.insert_one(product_entry)
#         else:
#             print(f"{offer['keyOfferType']} ", end='')
raw_collection.insert_many(response)
BaseImporter.commit()
print("done!")
