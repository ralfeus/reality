#!/usr/bin/env python3
import math
from reality_importer import BaseImporter, mongo_client, mongo_db
from datetime import datetime
import json
import re
from lxml.cssselect import CSSSelector

class BezRealitky(BaseImporter):
    sel_items = lambda self, i: CSSSelector('article')(i)
    sel_next_page = lambda self, i: CSSSelector('li.page-item + li.page-item a span')(i)[0]
    sel_url = lambda self, i: CSSSelector('div a')(i)[0].attrib['href']
    sel_id = lambda self, i: re.search('/(\d+)-', self.sel_url(i)).groups()[0]
    sel_layout = lambda self, i: CSSSelector('ul.featuresList li span')(i)[0].tail
    sel_area = lambda self, i: re.sub('\D', '', CSSSelector('ul.featuresList li span')(i)[1].tail)
    sel_price = lambda self, i: re.sub('\D', '', CSSSelector('p.propertyPrice span')(i)[0].text)
    sel_title = lambda self, i: CSSSelector('span.text-subheadline')(i)[0].text

    def __get_json(self, document):
        script = CSSSelector('script#__NEXT_DATA__')(document)[0].text
        data = json.loads(script)
        return data['props']['pageProps']

    def fetch(self):
        collection_sell = mongo_db['product']
        collection_rent = mongo_db['product_rent']
        raw_collection = mongo_db['bezrealitky']
        total_products = 0
        # prague_boundaries = {
        #     'north': 50.18,
        #     'south': 49.97,
        #     'west': 14.22,
        #     'east': 14.71
        # }
        offer_type = {
            'prodej': 1,
            'pronajem': 2
        }
        offer_urls = {
            'prodej': {
                'byt': 'https://www.bezrealitky.cz/vypis/nabidka-prodej/byt',
                'dum': 'https://www.bezrealitky.cz/vypis/nabidka-prodej/dum',
                'pozemek': 'https://www.bezrealitky.cz/vypis/nabidka-prodej/pozemek'
            },
            'pronajem': {
                'byt': 'https://www.bezrealitky.cz/vypis/nabidka-pronajem/byt',
                'dum': 'https://www.bezrealitky.cz/vypis/nabidka-pronajem/dum'
            }
        }
        print("Connected to DB")
        print("Trying to get entries...")
        for offer, v in offer_urls.items():
            print(f"Offer type: {offer}")
            for property_type, url in v.items():
                print(f"\t{property_type}")
                page = 1
                total_pages = 9999
                while page <= total_pages:
                    self._logger.info("Page %s of %s", page, total_pages)
                    response = self.get_document_from_url(f'{url}?page={page}')
                    # self._logger.info('Got document')
                    data = self.__get_json(response)
                    if page == 1:
                        total = data['totalCount']
                        entries_per_page = data['limit']
                        total_pages = math.ceil(total / entries_per_page)
                    page += 1
                    # items = self.sel_items(response)
                    # print(f"Inserting {len(items)} entries...", end = '')
                    for item in data['adverts']:
                        markers = filter(lambda m: m['id'] == item['id'], data['markers'])
                        try:
                            gps = next(markers)['gps']
                        except:
                            gps = {'lat': 0, 'lng': 0}
                        lat = float(gps['lat'])
                        lon = float(gps['lng'])
                        layout_parts = item['disposition'].split('_')
                        layout = f'{layout_parts[1]}+{layout_parts[2].lower()}' \
                            if len(layout_parts) > 1 else layout_parts[0].lower()
                        try:
                            json_doc = {
                                "url": "https://www.bezrealitky.cz/nemovitosti-byty-domy/" + item['uri'],
                                "id": item['id'],
                                "timeAdded": datetime.now(),
                                'advertEstateOffer': {
                                    'currency': item['currency'],
                                    'keyOfferType': offer,
                                    'keyEstateType': property_type,
                                    'keyDisposition': layout,
                                    'gps': gps,
                                    **item
                                }
                            }
                            json_doc['closestPublicTransportStop'] = BaseImporter.getClosestStop(lat, lon)
                            raw_collection.insert_one(json_doc)
                            if 'Praha' in item['address'] and property_type == 'byt':
                                self.add_product({
                                    "vendor": "Bez realitky",
                                    "id": item['id'],
                                    "layout": layout,
                                    "total_floor_area": item['surface'],
                                    "price": item['price'],
                                    'type': offer_type[offer],
                                    'latitude': lat,
                                    'longitude': lon,
                                    'closest_public_transport_stop_name': json_doc['closestPublicTransportStop']['name'],
                                    'closest_public_transport_stop_distance': json_doc['closestPublicTransportStop']['distance'],
                                    'url': json_doc['url']
                                })
                        except AttributeError as ex:
                            self._logger.error("Couldn't add item")
                            self._logger.exception(ex)

        self.commit()
        print("done!")

if __name__ == '__main__':
    BezRealitky().fetch()