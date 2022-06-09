from datetime import datetime
import json
import logging
import urllib.request
from math import atan2, cos, radians, sin, sqrt

from inspect import getframeinfo, getouterframes, currentframe
import lxml.html
import MySQLdb
import pandas as pd
import pymongo
from time import sleep

ATTEMPTS = 5
logging.basicConfig(level=logging.INFO)
mongo_client = pymongo.MongoClient('sandlet', connect=True)
mongo_db = mongo_client['reality']

class BaseImporter:
    stops = None # DataFrame with public transport stops
    mysql_connection = None
    prague_boundaries = {
        'north': 50.18,
        'south': 49.97,
        'west': 14.22,
        'east': 14.71
    }
    _logger:logging.Logger = None

    def __init__(self):
        self._logger = logging.getLogger(type(self).__name__)

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
            mongo_db = mongo_client['reality']
            collection = mongo_db['public_transport_stops']
            BaseImporter.stops = pd.DataFrame(collection.find()).drop(columns = '_id')

        closest_stop = BaseImporter.stops.join(BaseImporter.stops.point.apply(lambda x: BaseImporter.__get_distance(
            lat, lon, 
            x['coordinates'][1], x['coordinates'][0]
        )).rename('distance')).sort_values(by = 'distance').iloc[0, :].to_json(force_ascii = False)
        return eval(closest_stop)

    def get_document_from_url(self, url):
        for attempt in range(ATTEMPTS):
            try:
                with urllib.request.urlopen(url) as request:
                    content = request.read().decode()
                    doc = lxml.html.fromstring(content)
                    return doc
            except Exception as ex:
                self._logger.exception("BaseImporter::get_document_from_url(): An error has occurred")
                self._logger.exception(ex)
                sleep(30)
        raise Exception(f"BaseImporter::get_document_from_url(): Couldn't get document {url}")

    @staticmethod
    def get_json_from_url(url):
        with urllib.request.urlopen(url) as urlObject:
            return json.loads(urlObject.read().decode())
    
    @staticmethod
    def add_product(entry):
        attempts_left = ATTEMPTS
        while True:
            if BaseImporter.mysql_connection is None:
                BaseImporter.connect()
            try:
                cursor = BaseImporter.mysql_connection.cursor()
                query = "INSERT INTO `product` " \
                        "(vendor, id, layout, floor_area, price, latitude, longitude, offer_type, url, " \
                        " closest_public_transport_stop_name, closest_public_transport_stop_distance, " \
                        " date_added)" \
                        " VALUES (%(vendor)s, %(id)s, %(layout)s, %(total_floor_area)s, %(price)s, " \
                        "         %(latitude)s, %(longitude)s, %(type)s, %(url)s, " \
                        "         %(closest_public_transport_stop_name)s, " \
                        "         %(closest_public_transport_stop_distance)s, " \
                        "         DATE(NOW()))"
                cursor.execute(query, entry)
                return True
            except MySQLdb._exceptions.DataError as ex:
                print(str(ex))
                print(entry)
            except MySQLdb._exceptions.IntegrityError:
    #             print(entry)
                return False
            except MySQLdb._exceptions.OperationalError as ex:
                print(str(ex))
                attempts_left -= 1
                if not attempts_left:
                    return False
                BaseImporter.connect()
            #BaseImporter.mysql_connection.commit()
        
    @staticmethod
    def connect():
        attempts_left = 5
        BaseImporter.mysql_connection = None
        while BaseImporter.mysql_connection is None:
            if not attempts_left:
                raise Exception("Couldn't connect to MySQL")
            attempts_left -= 1
            BaseImporter.mysql_connection = MySQLdb.connect(
                host='sandlet', 
                user='reality',
                password='reality',
                database='reality'
                #auth_plugin='mysql_native_password' 
                #unix_socket='/var/run/mysqld/mysqld.sock'
            )
    
    @staticmethod
    def commit():
        if BaseImporter.mysql_connection is not None:
            BaseImporter.mysql_connection.commit()

frame = currentframe().f_back
while frame.f_code.co_filename.startswith('<frozen'):
    frame = frame.f_back
print(datetime.now(), frame.f_code.co_filename)
