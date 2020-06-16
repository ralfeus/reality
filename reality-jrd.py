#!/usr/bin/env python3
from reality_importer import BaseImporter 

from datetime import datetime
import json
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
    selOrientation = CSSSelector('td:nth-child(6) > p')
    selPrice = CSSSelector('td:nth-child(10) > p > strong')
    #selURL = CSSSelector('')

    urlBase = 'https://www.jrd.cz'

    def fetch(self):
        mongo_client = pymongo.MongoClient()

        db = mongo_client['reality']
        raw_collection = db['jrd']
        print("Connected to DB")
        projects = self.get_projects()
        idx_project = 1
        for project,url in tqdm(projects.items(), desc='Projects'):
            #page = 1
            #pages = 1000
            #while page <= pages:
            if re.match('https?://', url):
                json_doc = self.get_atypical_project_items(url)
            else:
                doc = self.get_document_from_url(self.urlBase + url)
                project_location = self.get_project_location(doc)
                items = self.selItems(doc) 
                for item in tqdm(items, desc=project):
                    json_doc = {
                        "url": self.urlBase + item.get('data-href'),
                        "identification": self.selIdentification(item)[0].text.strip(),
                        "layout": self.selLayout(item)[0].text.strip(),
                        "totalFloorArea": self.selTotalFloorArea(item)[0].text.strip(),
                        "location": project_location,
                        "project": project,
                        "floor": self.selFloor(item)[0].text.strip(),
                        "orientation": self.selOrientation(item)[0].text.strip(),
                        "priceWithVAT": int(re.sub(r'\D', '', self.selPrice(item)[0].text)),
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
                    'closest_public_transport_stop_distance': 0
                })
                #if pages == 1000:
                #    pages = get_pages(doc)    
                #print("Got page {} of {}".format(page, pages))
                #page += 1
            idx_project += 1
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