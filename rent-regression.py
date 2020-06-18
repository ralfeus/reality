from pymongo import MongoClient
import pandas as pd
from datetime import datetime
from datetime import time

def flatten(x):
    accu = []
    for item in x:
        accu += item
    return accu


client = MongoClient('sandlet')
db = client.reality
coll = db['sreality_rent']

dataset = coll.aggregate([
    {'$match': {
        'timeAdded': {'$gt': datetime.combine(datetime.now().date(), time(0, 0, 0))}
    }},
    {'$group': {
        '_id': "$hash_id",
        'labelsAll': {'$first': "$labelsAll"},
        'price': {'$first': "$price"},
        'name': {'$first': "$name"},
        'locality': {'$first': "$seo.locality"},
        'public_transport_distance': {'$last': "$closestPublicTransportStop.distance"}
    }}
])
df_original = pd.DataFrame(dataset)
df = df_original
print(f'Got data. df.shape is {df.shape}')
df.labelsAll = df.labelsAll.aggregate(flatten)
df['layout'] = df.name.str.extract(r'(\d\+\S+)')
df['area'] = df.name.str.extract(r'(\d+)\sm').astype(int)
# df['locality'] = df['locality'].str.split('-').apply(lambda x: x[1])
df = df.drop(columns = ['_id', 'name'])
# df = df.join(pd.get_dummies(df.labelsAll.apply(pd.Series).stack()).sum(level = 0))
df = df.join(pd.get_dummies(df.layout, prefix = 'layout'))
df = df.join(pd.get_dummies(df.locality, prefix = 'locality'))
df['price_per_sq_meter'] = df.price / df.area
df = df.drop(columns = ['price', 'layout', 'locality', 'labelsAll'])

### Cleansing data 
df = df[df['area'] > 0]
df = df[df.price_per_sq_meter >= 250]
### end of cleansing

df = df.sort_values(by = ['price_per_sq_meter'])

from matplotlib import pyplot as plt
from sklearn.decomposition import PCA
import sklearn.ensemble as e
import sklearn.linear_model as r 
from sklearn.svm import LinearSVR
from sklearn.model_selection import train_test_split
from sklearn.model_selection import learning_curve
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures
from sklearn.preprocessing import StandardScaler
import numpy as np

df_90 = df.head(int(len(df) * 0.98))
X_train = df_90.drop(columns = "price_per_sq_meter")
y_train = df_90.price_per_sq_meter
pca = PCA()
m = len(X_train)
X_trans = StandardScaler().fit_transform(X_train)
X_trans = pca.fit_transform(X_trans)
X_red = np.ndarray((m, 0))
total_variance = 0
index = 0
while total_variance < 0.99:
    X_red = np.append(X_red, X_trans[:, index].reshape(m, 1), axis = 1) 
    total_variance += pca.explained_variance_ratio_[index]
    index += 1
print("Taken {} features".format(index))

model = make_pipeline(PolynomialFeatures(1), r.RANSACRegressor(base_estimator = r.Ridge()))
training_sizes, training_scores, validation_scores = learning_curve(
    estimator = model,
    X = X_red,
    y = y_train,
    train_sizes = np.linspace(2000, m * 0.8, dtype = int), 
    cv = 5
)
print("Built model")

line1, line2 = plt.plot(
    training_sizes, training_scores.mean(axis = 1), 'g', 
    training_sizes, validation_scores.mean(axis = 1), 'r')
plt.legend((line1, line2), ('Training', 'Cross-validation'))
