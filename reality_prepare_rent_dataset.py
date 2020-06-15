import joblib
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

model = joblib.load('rent-model.huber')
scaler = joblib.load('rent-model.scaler')
# number of features calculated during model training
features_num = 92

def flatten(x):
    accu = []
    for item in x:
        accu += item
    return accu

def prepareDataset(originalDataframe):
    df = originalDataframe
    df['labelsAll'] = df['labelsAll'].aggregate(flatten)
    df['layout'] = df['name'].str.extract('(\d\+\S+)')
    df['area'] = df['name'].str.extract('(\d+)\sm').astype(int)
    df['locality'] = df['locality'].str.split('-').apply(lambda x: x[1])
    df['price_per_sq_meter'] = df.price / df.area
    df = df.join(pd.get_dummies(df.labelsAll.apply(pd.Series).stack()).sum(level = 0))
    #df = df.join(pd.get_dummies(df.layout, prefix = 'layout'))
    df = df.join(pd.get_dummies(df.locality, prefix = 'locality'))
    #df = df.drop(columns = ['price', 'area', 'layout', 'locality', 'labelsAll'])
    cols = pd.read_csv('columns.csv', header = None).iloc[:, 0].tolist()
    df = df.reindex(columns = cols).fillna(0)
    df = df.sort_values(by = ['public_transport_distance'])
    return df

def predict(X):
    X_p = pd.DataFrame({k: [v] for k, v in X.items()})
    X_p = prepareDataset(X_p)
    X_p = X_p.drop(columns = "price_per_sq_meter")
#     scaled_feature = scaler.transform([[X_p['public_transport_distance'][0]]])
#     X_p['public_transport_distance'] = scaled_feature
#     X_trans = PCA().fit_transform(X_p)
#     X_red = X_trans[:, 0:features_num] 

    return model.predict(X_p)
