#!/usr/bin/env python3
from reality_importer import BaseImporter
from reality_prepare_rent_dataset import predict, prepareDataset
from datetime import datetime, time
from http.client import IncompleteRead
from time import sleep
import json
import math
import pymongo
import re
from tqdm import tqdm
import urllib.request

ATTEMPTS = 5

def get_json_from_url(url):
    attempts_left = ATTEMPTS
    while True:
        try:
            with urllib.request.urlopen(url) as urlObject:
                return json.loads(urlObject.read().decode())
        except IncompleteRead:
            attempts_left -= 1
            if not attempts_left:
                raise Exception(f"Couldn't get document from the URL {url}")
            else:
                print(f"An error has occurred during getting URL {url}. Retrying...")
    
def get_items(endpoint, request_params, cat_name=None):
    """
    Gets items from given endpoint and params
    """
#     print(f'Getting items count ... ', end='')
    items_count = get_json_from_url('{}/count?{}'.format(
        endpoint,
        '&'.join([f'{p}={v}' for p, v in request_params.items()])))['result_size']
#     print(items_count)

    page = 1
    result = []
    pages = math.ceil(items_count / request_params['per_page'])
    for page in tqdm(range(1, pages + 1), desc=cat_name):
#         print("Inserting entries {} through {}, page {} of {} ... ".format(
#                 (page - 1) * request_params['per_page'] + 1, 
#                 (page * request_params['per_page'] if page * request_params['per_page'] < items else items),
#                 page, pages))
        response = get_json_from_url('{}?page={}&{}'.format(
                                         endpoint, page, 
                                         '&'.join([f'{p}={v}' for p, v in request_params.items()])))
        result.append(response)
    return result

def predict_rent_price(items):
    items_to_predict = [{
        'labelsAll': x['labelsAll'],
        'price': x['price'],
        'name': x['name'],
        'locality': x['seo']['locality'],
        'totalFloorArea': x['totalFloorArea'],
        'public_transport_distance': x['closestPublicTransportStop']['distance'],
        'layout': x['seo']['category_sub_cb']
    } for x in items
    if 
        x['seo']['category_main_cb'] == 1 and 
        x['seo']['category_type_cb'] == 1 and
        x['seo']['locality'].startswith('praha-')]
    result = predict(items_to_predict)
    for index in range(len(items_to_predict)):
        items_to_predict[index].update(
            {'predicted_rent_price': items_to_predict[index]['totalFloorArea'] * result[index]})
    #items_to_predict.sort(key=lambda x: int(x['hash_id']))
    #items.sort(key=lambda x: int(x['hash_id']))

    return items
    
def is_valid(entry):
    if entry['price'] > 1000000000:
        return False
    return True

#mongo_client = pymongo.MongoClient("mongodb+srv://dbuser:PqUSHv9MdYDGYC4Zil62@test-ytcpu.mongodb.net/reality?retryWrites=true&w=majority")
mongo_client = pymongo.MongoClient()

db = mongo_client['reality']
#collection = db['product']
estates_collection = db['sreality_all']
projects_collection = db['sreality_projects']
response = {}
print("Connected to DB")
category_main_cb = {
        'apartments': 1,
        'houses': 2,
        'land': 3,
        'commercial': 4,
        'other': 5
}
estate_type = {
    1: 'byt',
    2: 'dum',
    3: 'pozemek',
    4: 'komercni',
    5: 'jine'
}
offer_type = {
    1: 'prodej',
    2: 'pronajem',
    3: 'drazba'
}
request_params = {
        'per_page': 999, # Amount of items per page
        'category_main_cb': 1, # Apartments
        'category_type_cb': 1, # Selling
        'locality_region_id': 10 # Praha
}
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
api_url = 'https://www.sreality.cz/api'
estatesUrl = f'{api_url}/cs/v2/estates'
projectUrl = f'{api_url}/cs/v2/projects'

items = get_json_from_url(f'{estatesUrl}/count')['result_size']
print('Found {} items'.format(items))
result = []
for name, category in tqdm(category_main_cb.items(), desc="Categories", leave=False):
    pages = get_items(estatesUrl, cat_name=name, request_params={
        'per_page': request_params['per_page'],
        'category_main_cb': category
    })
    for page in tqdm(pages, desc=name, leave=False):
        result += page['_embedded']['estates']
for entry in tqdm(result, desc="Adding entries to MySQL DB"):
    if not is_valid(entry):
        result.remove(entry)
        continue
    totalFloorAreaMatch = re.search(r'\s+([\d\s]+)\s+m²', entry['name'])
    entry['url'] = 'https://www.sreality.cz/detail/{}/{}/{}/{}/{}'.format(
        offer_type[entry['seo']['category_type_cb']],
        estate_type[entry['seo']['category_main_cb']],
        layout[entry['seo']['category_sub_cb']] if entry['seo']['category_sub_cb'] in layout.keys() else 'atypický',
        entry['seo']['locality'],
        entry['hash_id'])
    entry['totalFloorArea'] = int(re.sub(r'\s', '', 
        totalFloorAreaMatch[1])) if totalFloorAreaMatch is not None else 0
    entry['timeAdded'] = datetime.now()
    entry['dateAdded'] = datetime.combine(
            datetime.now().date(), 
            time(0, 0, 0))
    if (entry['seo']['locality'].startswith('praha-') and 
        entry['seo']['category_main_cb'] == 1):
        closestStop = BaseImporter.getClosestStop(entry['gps']['lat'], entry['gps']['lon'] )
        entry['closestPublicTransportStop'] = closestStop
        product = {
            'vendor': 'sreality',
            'id': str(entry['hash_id']),
            'layout': layout[entry['seo']['category_sub_cb']] if entry['seo']['category_sub_cb'] in layout.keys() else 'atypický',
            'total_floor_area': entry['totalFloorArea'],
            'price': entry['price'],
            'latitude': entry['gps']['lat'],
            'longitude': entry['gps']['lon'],
            'type': entry['seo']['category_type_cb'],
            'closest_public_transport_stop_name': closestStop['name'] if closestStop else None,
            'closest_public_transport_stop_distance': closestStop['distance'] if closestStop else None, 
            'url': entry['url']
        }
        BaseImporter.add_product(product)
BaseImporter.commit()

# TODO: Has to be fixed
# result = predict_rent_price(result )
estates_collection.insert_many(result)
print("SReality all: Done adding estates")

items = get_json_from_url(f'{projectUrl}/count')['result_size']
print(f'Found {items} projects')
result = get_items(projectUrl, request_params={
    'per_page': request_params['per_page']
})
for projects in result:
    for project in tqdm(projects['projects'], desc="Projects", leave=False):
        project_url = f'{api_url}{project["_links"]["self"]["href"]}'
        job_done = False
        attempts_left = 3
        while not job_done and attempts_left:
            try:
                project_doc = get_json_from_url(project_url)
    #         print('\tGetting {} objects from the project "{}"'.format(
    #             project_doc["_embedded"]["estates"]["result_size"],
    #             project['name']
    #         ))
                for entry in tqdm(project_doc['_embedded']['estates']['_embedded']['estates'], desc=project['name'], leave=False):
                    entry['url'] = 'https://www.sreality.cz/detail/{}/{}/{}/{}/{}'.format(
                        offer_type[entry['seo']['category_type_cb']],
                        estate_type[entry['seo']['category_main_cb']],
                        layout[entry['seo']['category_sub_cb']] if entry['seo']['category_sub_cb'] in layout.keys() else 'atypický',
                        entry['seo']['locality'],
                        entry['hash_id'])
                    entry['projectId'] = project['id']
                    entry['totalFloorArea'] = int(entry['usable_area'])
                    entry['timeAdded'] = datetime.now()
                    entry['dateAdded'] = datetime.combine(
                            datetime.now().date(), 
                            time(0, 0, 0))   
                    estates_collection.insert_one(entry)
                    if (BaseImporter.prague_boundaries['south'] <= entry['gps']['lat'] <= BaseImporter.prague_boundaries['north'] and
                        BaseImporter.prague_boundaries['west'] <= entry['gps']['lon'] <= BaseImporter.prague_boundaries['east'] and
                        entry['seo']['category_main_cb'] == 1):
                        closestStop = BaseImporter.getClosestStop(entry['gps']['lat'], entry['gps']['lon'] )

                        product = {
                            'vendor': 'sreality',
                            'id': str(entry['hash_id']),
                            'layout': layout[entry['seo']['category_sub_cb']] if entry['seo']['category_sub_cb'] in layout.keys() else 'atypický',
                            'total_floor_area': entry['totalFloorArea'],
                            'price': entry['price'],
                            'latitude': entry['gps']['lat'],
                            'longitude': entry['gps']['lon'],
                            'type': entry['seo']['category_type_cb'],
                            'closest_public_transport_stop_name': closestStop['name'],
                            'closest_public_transport_stop_distance': closestStop['distance'], 
                            'url': entry['url']
                        }
                        BaseImporter.add_product(product)
                job_done = True    
            except urllib.error.HTTPError as ex:
                print("Some shit has happened: %s" % str(ex))
                print("But I'll try again")
                attempts_left -= 1
                sleep(5)

        projects_collection.insert_one(project)
print("SReality all: Done adding projects")
print("Committing transaction...")
BaseImporter.commit()
print("Done!")

