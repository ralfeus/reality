#!/usr/bin/env python3
from reality_importer import BaseImporter 

from datetime import datetime
import json
import logging
import pymongo
import re
import urllib.request
import lxml.html
from lxml.cssselect import CSSSelector
from tqdm import tqdm

class JRD(BaseImporter):

    selProjects = CSSSelector('a.box-projects_item')
    selProjectName = CSSSelector('div.box-projects_item-cover-label h3')
    selItems = CSSSelector('table.table-pricelist tr[data-href]')
    #selLastPage = CSSSelector('li.pagination-link>a')
    selIdentification = CSSSelector('td:nth-child(1) > p > strong')
    selLayout = CSSSelector('td:nth-child(2) > p')
    selTotalFloorArea = CSSSelector('td:nth-child(4) > p')
    selLocation = CSSSelector('div > strong')
    selFloor = CSSSelector('td:nth-child(3) > p')
    selOrientation = CSSSelector('td > p')
    selPrice = CSSSelector('td strong')
    #selURL = CSSSelector('')

    urlBase = 'https://www.jrd.cz'

    def fetch(self):
        mongo_client = pymongo.MongoClient()

        db = mongo_client['reality']
        raw_collection = db['jrd']
        print("Connected to DB")
        try:
            projects = self.get_projects()
        except:
            logging.exception("Couldn't get projects")
            exit(1)
        for project,url in tqdm(projects.items(), desc='Projects'):
            if re.match('https?://', url):
                json_docs = self.get_atypical_project_items(url)
                #print(f"\tGot {len(json_docs)} items")
                for json_doc in json_docs:
                    raw_collection.insert_many(json_doc)
                    self.add_product({
                        'vendor': "JRD",
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
            else:
                doc = self.get_document_from_url(f"https:{url}")
                project_location = self.get_project_location(doc)
                items = self.selItems(doc) 
                #print(f"\tGot {len(items)} items")
                for item in tqdm(items, desc=project):
                    layout = self.selLayout(item)[0].text.strip()
                    json_doc = {
                        "url": self.urlBase + item.get('data-href'),
                        "type": 'land' if layout == 'Pozemek' else 'apartment',
                        "identification": self.selIdentification(item)[0].text.strip(),
                        "layout": layout,
                        "totalFloorArea": self.selTotalFloorArea(item)[0].text.strip(),
                        "location": project_location,
                        "project": project,
                        "floor": self.selFloor(item)[0].text.strip() if layout != 'Pozemek' else '',
                        "orientation": next((e.text.strip() 
                            for e in self.selOrientation(item) 
                            if e.text and re.match('[A-Z]{1,4}', e.text.strip())), ''),
                        "priceWithVAT": int(re.sub(r'\D', '', next((e.text 
                            for e in self.selPrice(item) if re.search('Kč', e.text)), 0))),
                        "timeAdded": datetime.now()
                    }
                    # print(json_doc)
                    raw_collection.insert_one(json_doc)
                    self.add_product({
                        'vendor': "JRD",
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
        self.commit()

    def get_atypical_project_items(self, url):
        return []

    # def get_pages(self, document):
    #     last_page_link = selLastPage(document)
    #     if len(last_page_link) == 0:
    #         return 1
    #     else:
    #         return int(last_page_link[len(last_page_link) - 1].text)

    def get_project_location(self, doc):
        location_elements = self.selLocation(doc)
        for item in location_elements:
            if item.text == 'Lokalita':
                for sibling in item.itersiblings():
                    return sibling.text
        return ''

    def get_projects(self):
        doc = self.get_document_from_url(f'{self.urlBase}/cs/projekty.html')
        projects = self.selProjects(doc)
        mapped_projects = dict(map(
            lambda p: (self.selProjectName(p)[0].text, p.get('href')), 
            projects))
        return mapped_projects


if __name__ == '__main__':
    JRD().fetch()