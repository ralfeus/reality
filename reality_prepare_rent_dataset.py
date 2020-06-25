import joblib
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

def flatten(x):
    accu = []
    for item in x:
        accu += item
    return accu

def prepareDataset(originalDataframe):
    df = originalDataframe
    df['labelsAll'] = df['labelsAll'].aggregate(flatten)
    df['totalFloorArea'] = df['totalFloorArea'].astype(int)
    df['price_per_sq_meter'] = df.price / df.totalFloorArea
    cols = pd.read_csv('columns.csv', header = None).iloc[:, 0].tolist()
    df = df.reindex(columns = cols).fillna(0)    
    if 'labelsAll' in df.columns:
        df = df.join(pd.get_dummies(df.labelsAll.apply(pd.Series).stack(), prefix='label').sum(level = 0)).drop(columns='labelsAll')
    if 'layout' in df.columns:
        df = df.join(pd.get_dummies(df.layout, prefix = 'layout')).drop(columns='layout')
    if 'locality' in df.columns:
        df = df.join(pd.get_dummies(df.locality, prefix = 'locality')).drop(columns='locality')
   
    df = df.drop(columns = ['price', 'totalFloorArea'])
    df = df.sort_values(by = ['public_transport_distance'])

    return df

def predict(X):
    '''
    Predicts rent prices for properties to sell based on trained model.
    Model is trained on Prague apartments only. So same properties should be predicted.
    Arguments:
    X -- list of dictionaries. Each dictionary represents a property
    '''
    # Prepare dataset for prediction
    model = joblib.load('rent-model.pipeline')
    df = prepareDataset(pd.DataFrame(X))
    df = df.reindex(columns=model.features, fill_value=0)

    # Transform features
    X_pred = df
    X_trans = joblib.load('rent-model.scaler').transform(X_pred)
    X_trans = joblib.load('rent-model.pca').transform(X_trans)
    X_red = X_trans[:, :model.features_num]

    predicted = model.predict(X_red)
    return predicted
