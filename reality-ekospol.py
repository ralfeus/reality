#!/usr/bin/env python3
from reality_importer import BaseImporter 

from datetime import datetime
import json
import pymongo
import re
import urllib.request
from urllib.error import HTTPError
import logging
import lxml.html
from lxml.cssselect import CSSSelector
from tqdm import tqdm

selProjects = CSSSelector('div.project-box a')
selItems = CSSSelector('div.responsive-table table tbody tr[onclick]')
#selLastPage = CSSSelector('li.pagination-link>a')
selIdentification = CSSSelector('td:nth-child(1)')
selLayout = CSSSelector('td:nth-child(2)')
selTotalFloorArea = CSSSelector('td:nth-child(4)')
#selProject = CSSSelector('div.tile div.grid div.g-9.m-12.s-12.xs-12 div.grid div.g-6.m-12.s-12.xs-12 div.grid div.g-6')
#selLocation = CSSSelector('div.entry-subheader>p')
selFloor = CSSSelector('td:nth-child(3)')
selOrientation = CSSSelector('td:nth-child(6)')
selPrice = CSSSelector('td.cena')
#selURL = CSSSelector('')

urlBase = 'https://www.ekospol.cz'

def get_document_from_url(url):
    logging.debug("Getting %s", url)
    with urllib.request.urlopen(url) as request:
        content = request.read().decode()
        doc = lxml.html.fromstring(content)
        return doc

def get_projects():
    doc = get_document_from_url('https://www.ekospol.cz/byty/prodej-bytu-praha/')
    projects = selProjects(doc)
    mapped_projects = dict(map(lambda p: (p.cssselect('h2')[0].text, p.get('href')), projects))
    return mapped_projects

mongo_client = pymongo.MongoClient()

db = mongo_client['reality']
collection = db['product']
raw_collection = db['ekospol']
print("Connected to DB")
projects = get_projects()
idx_project = 1
for project,url in tqdm(projects.items(), desc='Projects'):
    print("Project '{}' ({} of {})".format(project, idx_project, len(projects)))
    #page = 1
    #pages = 1000
    #while page <= pages:
    try:
        doc = get_document_from_url(urlBase + url + "/cenik")
        items = selItems(doc) 
        for item in tqdm(items, desc=project):
            json_doc = {
                "url": urlBase + re.search('/[^\']+', item.get('onclick')).group(),
                "identification": selIdentification(item)[0].text.strip(),
                "layout": selLayout(item)[0].text.strip(),
                "totalFloorArea": float(re.search('[0-9\.]+', selTotalFloorArea(item)[0].text, re.MULTILINE).group()),
                #"location": selLocation(item)[0].text.strip(),
                "project": project,
                "floor": selFloor(item)[0].text.strip(),
                "orientation":selOrientation(item)[0].text.strip(),
                "priceWithVAT": int(re.sub('\D', '', selPrice(item)[0].text)),
                "timeAdded": datetime.now()
            }
            raw_collection.insert_one(json_doc)
            BaseImporter.add_product({
                'vendor': "Ekospol",
                'id': json_doc['identification'],
                'layout': json_doc['layout'],
                'total_floor_area': json_doc['totalFloorArea'],
                'price': json_doc['priceWithVAT'],
                'latitude': 0,
                'longitude': 0,
                'type': 1,
                'closest_public_transport_stop_name': '',
                'closest_public_transport_stop_distance': 0, 
                'url': json_doc['url']
            })
    except HTTPError:
        logging.warning("Couldn't get product %s. It's not available anymore", project)
        #if pages == 1000:
        #    pages = get_pages(doc)    
        #print("Got page {} of {}".format(page, pages))
        #page += 1
    idx_project += 1
BaseImporter.commit()