from tqdm.notebook import tqdm
import json
from tqdm import tqdm
from pyproj import Proj, transform
def jtsk_to_wgs(x, y):
    inProj = Proj('epsg:5514')
    outProj = Proj('epsg:4326')
    return transform(inProj, outProj, x, y)

doc = json.load(open('reality/KU_CZ.json', 'r'))
inProj = Proj('epsg:5514')
outProj = Proj('epsg:4326')
for area in tqdm(doc['features'], desc="Area"):
    for coordinate in tqdm(area['geometry']['coordinates'][0], desc="Coordinate", leave=False):
        coordinate[0], coordinate[1] = transform(inProj, outProj, coordinate[0], coordinate[1])
json.dump(doc, open('reality/KU_CZ_modified.json', 'w'))
