import json
import urllib.request
from math import atan2, cos, radians, sin, sqrt

import lxml.html
import mysql.connector
import pandas as pd
import pymongo


class BaseImporter:
    stops = None # DataFrame with public transport stops
    mysql_connection = None
    prague_boundaries = {
        'north': 50.18,
        'south': 49.97,
        'west': 14.22,
        'east': 14.71
    }

    @staticmethod
    def __get_distance(lat1, lon1, lat2, lon2):
        # approximate radius of earth in meters
        R = 6373000

        lat1 = radians(lat1)
        lon1 = radians(lon1)
        lat2 = radians(lat2)
        lon2 = radians(lon2)

        dlon = lon2 - lon1
        dlat = lat2 - lat1

        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c

    @staticmethod
    def getClosestStop(lat, lon):
        if BaseImporter.stops is None:
            mongo_client = pymongo.MongoClient()
            db = mongo_client['reality']
            collection = db['public_transport_stops']
            BaseImporter.stops = pd.DataFrame(collection.find()).drop(columns = '_id')

        closest_stop = BaseImporter.stops.join(BaseImporter.stops.point.apply(lambda x: BaseImporter.__get_distance(
            lat, lon, 
            x['coordinates'][1], x['coordinates'][0]
        )).rename('distance')).sort_values(by = 'distance').iloc[0, :].to_json(force_ascii = False)
        return eval(closest_stop)

    def get_document_from_url(self, url):
        # print(url)
        with urllib.request.urlopen(url) as request:
            content = request.read().decode()
            doc = lxml.html.fromstring(content)
            return doc

    @staticmethod
    def get_json_from_url(url):
        with urllib.request.urlopen(url) as urlObject:
            return json.loads(urlObject.read().decode())
    
    @staticmethod
    def add_product(entry):
        while BaseImporter.mysql_connection is None:
            BaseImporter.mysql_connection = mysql.connector.connect(
                host='localhost', 
                user='ralfeus', 
                database='reality', 
                auth_plugin='auth_socket', 
                unix_socket='/var/run/mysqld/mysqld.sock')
        cursor = BaseImporter.mysql_connection.cursor()
        query = "INSERT INTO `product` " \
                "(vendor, id, layout, floor_area, price, latitude, longitude, offer_type, " \
                " closest_public_transport_stop_name, closest_public_transport_stop_distance, " \
                " date_added)" \
                " VALUES (%(vendor)s, %(id)s, %(layout)s, %(total_floor_area)s, %(price)s, " \
                "         %(latitude)s, %(longitude)s, %(type)s, " \
                "         %(closest_public_transport_stop_name)s, %(closest_public_transport_stop_distance)s," \
                "         DATE(NOW()))"
        try:
            cursor.execute(query, entry)
            return True
        except mysql.connector.errors.IntegrityError:
#             print(entry)
            return False
        #BaseImporter.mysql_connection.commit()
        
    @staticmethod
    def commit():
        if BaseImporter.mysql_connection is not None:
            BaseImporter.mysql_connection.commit()
