# -*- coding: utf-8 -*-

"""## Retrieve and Instanciate Dependencies

For this work, we will need these libraries
"""

import sklearn
import time
import random
import copy

import pandas as pd # data manipulation library
import matplotlib.pyplot as plt # plot library
import numpy as np # math library

import sklearn.metrics as sklm # metrics
import statsmodels as sm # statistical models

from keras.models import Sequential
from keras.layers import Dense, Activation
from keras.wrappers.scikit_learn import KerasClassifier
from sklearn.model_selection import GridSearchCV

"""## Configurations

Make the environment reproducible
"""

import tensorflow as tf # machine learning library
import os

os.environ['PYTHONHASHSEED'] = '0'
tf.reset_default_graph()
tf.set_random_seed(0)
np.random.seed(0)
random.seed(0)

tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)

"""Set path for the folder in which everything should be stored."""

PATH = ''

"""## Util"""

class WalkingForwardTimeSeriesSplit():
    def __init__(self, n_splits):
        self.n_splits = n_splits
    
    def get_n_splits(self, X, y, groups):
        return self.n_splits
    
    def split(self, X, y=None, groups=None):
        n_samples = len(X)
        k_fold_size = n_samples // self.n_splits
        indices = np.arange(n_samples)

        margin = 0
        for i in range(self.n_splits):
            start = i * k_fold_size
            stop = start + k_fold_size
            mid = int(0.8 * (stop - start)) + start
            yield indices[start: mid], indices[mid + margin: stop]

"""## Dataset Generation Util"""

def retrieve_data(flow_interval):
    path = f"{PATH}dataset/dataset_flow_{flow_interval}.csv"
    data = pd.read_csv(path, ';')
    
    data['Flow'].apply(int)
    data['AveSpeed'].apply(float)
    data['Density'].apply(float)
    data['Sunday'].apply(int)
    data['Monday'].apply(int)
    data['Tuesday'].apply(int)
    data['Wednesday'].apply(int)
    data['Thursday'].apply(int)
    data['Friday'].apply(int)
    data['Saturday'].apply(int)
      
    return data

"""## Storage Util"""

import json

def print_json (obj):
  print(json.dumps(obj, sort_keys=True, indent=4))

def load(filename):
  with open(f"{PATH}results/comparison/{filename}.json", 'r') as json_file:
    return json.load(json_file)

def store(obj, path, name):
  with open(f"{PATH}{path}/{name}.json", 'w') as json_file:
    json.dump(obj, json_file, sort_keys=True, indent=4)

def store_results ():
  name = int(time.time())
  
  result_data['meta'] = {
    "SEEABLE_PAST": SEEABLE_PAST,
    "PREDICT_IN_FUTURE": PREDICT_IN_FUTURE,
    "FLOW_INTERVAL": FLOW_INTERVAL,
    "N_SPLITS": N_SPLITS,
  }

  store(result_data, "results", f"{name}")

  slim_result_data = copy.deepcopy(result_data)
  for model in slim_result_data['results']:
      del slim_result_data['results'][model]['raw']

  store(slim_result_data, "results", f"{name}_slim.json")

def store_comparisons (title):
  name = str(int(time.time()))
  
  j = copy.deepcopy(comparison_data)

  store(result_data, "results/comparison", f"{name+title}")
    
  for i in range(len(j)):
    print([*j[i]['results']])
    for model in j[i]['results']:
      del j[i]['results'][model]['raw']

  store(result_data, "results/comparison", f"{name+title}_slim")

"""## Models Util

### Dropped

#### Random (Baseline)

This implementation just guess a random number in the [0, 100] interval for every output.
"""

def random_guess_univariate (data):
  global result_data
  
  X, Y = generate_dataset(data, False, FLOW_INTERVAL, N_STEPS, N_FUTURE)

  name = "Random Guess"
  m = max(Y)

  expected, observed, times = [], [], []
  pointers = split_dataset(len(Y), SET_SPLIT, TEST_SPLIT)
  
  for i, j, k in pointers:
    start = time.time()

    Y_hat = [random.randint(0, m) for i in range(k - j)]

    expected.append(Y[j:k])
    observed.append(Y_hat)
    times.append(time.time() - start)

  result_data['results'][name] = evaluate(expected, observed, times, name)

  if VERBOSITY:
    plot_prediction(expected, observed, name)

"""#### ARIMA

This implementation was based on [How to Create an ARIMA Model for Time Series Forecasting in Python](https://machinelearningmastery.com/arima-for-time-series-forecasting-with-python/).
"""

def arima (X):
  size = int(len(X) * TRAIN_SPLIT)
  acc = X[size-(2*WEEK_SIZE):size]
  Y = X[size+N_FUTURE:]
  Y_hat = []
  
  #for t in range(len(Y)):
  for t in range(50):
    print(t, len(Y))
    
    model = sm.tsa.arima_model.ARIMA(acc, order=(5, 1, 0))
    model_fit = model.fit(disp=0)
    
    start = len(acc)
    end = start + N_FUTURE
    
    prediction = model_fit.predict(start=start, end=end+1)
    
    print(prediction)
    Y_hat.append(prediction[-1])    
    acc.append(X[size + t])
    acc.pop(0)
  
  print_difference(Y, Y_hat)

"""#### Logistic Regression"""

from sklearn.linear_model import LogisticRegression

def logistic_regression_grid(data, useB):		
  global result_data		
      
  X, Y = generate_dataset(data, useB, FLOW_INTERVAL, N_STEPS, N_FUTURE)		
  X = X.reshape(X.shape[0], X.shape[1] * X.shape[2])		
        
  cv=[(slice(None), slice(None))] # to ignore the cross-validation		
  param_grid = {		
    "C": np.logspace(-3,3,7) + [None], 		
    "penalty": ["l1","l2", None]		
  }		
      
  model = LogisticRegression()		
      
  gs = sklearn.model_selection.GridSearchCV(estimator=model, param_grid=param_grid, scoring='neg_mean_squared_error', cv=cv, n_jobs=4, verbose=2)		
      
  i, j, k = 0, int(len(X) * (1 - TEST_SPLIT)), len(X)		
    
  gs.fit(X[i:j], Y[i:j])		
      
  best = gs.best_estimator_		
  predictions = best.predict(X[j:k])                         		
          
  mae = sklm.mean_absolute_error(Y[j:k], predictions)		
  rmse = np.sqrt(sklm.mean_squared_error(Y[j:k], predictions))		
  nrmse = rmse / np.std(Y[j:k])		
  hr = evaluate_precision_hit_ratio(Y[j:k], predictions)		
      
  res = {
    'params': gs.best_params_,
    'results': {
        'MAE': mae,
        'RMSE': rmse,
        'NRMSE': nrmse,
        'HR': hr,
    },
  }

  print_json(res)
  store(res, 'results/', 'lr_B_best_params' if isMulti else 'lr_A_best_params')

def logistic_regression(data, useB):
  global result_data
  
  name = "LR B" if useB else "LR A"

  expected, observed, times = [], [], []

  X, Y = generate_dataset(data, useB, FLOW_INTERVAL, N_STEPS, N_FUTURE)
  X = X.reshape(X.shape[0], X.shape[1] * X.shape[2])

  model = LogisticRegression()

  pointers = split_dataset(len(X), SET_SPLIT, TEST_SPLIT)
  
  for i, j, k in pointers:
    start = time.time()
    
    model.fit(X[i:j], Y[i:j])
    
    expected.append(Y[j:k])
    observed.append(model.predict(X[j:k]))
    times.append(time.time() - start)
    
  result_data['results'][name] = evaluate(expected, observed, times, name)
  
  if VERBOSITY:
    plot_prediction(expected, observed, name)

"""#### RNN

The optimzation was based on [How to Grid Search Hyperparameters for Deep Learning Models in Python With Keras](https://machinelearningmastery.com/grid-search-hyperparameters-deep-learning-models-python-keras/).
"""

from keras.layers import SimpleRNN

def create_rnn(input_shape):
  def create(n=50, activation='relu'):
    model = Sequential()		

    model.add(SimpleRNN(n, activation=activation, input_shape=input_shape))		
    model.add(Dense(1))		

    model.compile(optimizer='adam', loss='mse', metrics = ["accuracy"])
    return model		

  return create

def rnn_grid(data, useB):		
  global result_data		

  X, Y = generate_dataset(data, useB, FLOW_INTERVAL, N_STEPS, N_FUTURE)

  cv=[(slice(None), slice(None))]		
  param_grid = {		
    'activation': ['relu', 'sigmoid', None],
    'n': [50, 100, 200, 400],
    'batch_size': [8, 16, 32, 64],
  }	

  model = KerasClassifier(build_fn=create_rnn((X.shape[1], X.shape[2])), epochs=15, verbose=0)

  gs = sklearn.model_selection.GridSearchCV(estimator=model, param_grid=param_grid, scoring='neg_mean_squared_error', cv=cv, n_jobs=4, verbose=2)		

  i, j, k = 0, int(len(X) * (1 - TEST_SPLIT)), len(X)		

  gs.fit(X[i:j], Y[i:j])		

  best = gs.best_estimator_		
  predictions = best.predict(X[j:k])                         		

  mae = sklm.mean_absolute_error(Y[j:k], predictions)		
  rmse = np.sqrt(sklm.mean_squared_error(Y[j:k], predictions))		
  nrmse = rmse / np.std(Y[j:k])		
  hr = evaluate_precision_hit_ratio(Y[j:k], predictions)		

  res = {
    'params': gs.best_params_,
    'feature_importance': gs.best_estimator_.feature_importances_,
    'results': {
        'MAE': mae,
        'RMSE': rmse,
        'NRMSE': nrmse,
        'HR': hr,
    },
  }

  print_json(res)
  store(res, 'results/', 'rnn_B_best_params' if useB else 'rnn_A_best_params')

def rnn (data, useB): 
  global result_data
  
  name = "RNN B" if useB else "RNN A"
  
  X, Y = generate_dataset(data, useB, FLOW_INTERVAL, N_STEPS, N_FUTURE)
  
  expected, observed, times = [], [], []
  
  model = create_rnn((X.shape[1], X.shape[2]))()
  
  pointers = split_dataset(len(X), SET_SPLIT, TEST_SPLIT)
  
  for i, j, k in pointers:
    start = time.time()
    
    hist = model.fit(X[i:j], Y[i:j], validation_split=0.2, batch_size=64, epochs=15, verbose=0)
    
    expected.append(Y[j:k])
    observed.append(model.predict(X[j:k]))
    times.append(time.time() - start)
    
    if VERBOSITY:
      plot_history(hist, f"{name} ({str(len(times)).zfill(2)} of {len(pointers)})")
    
  result_data['results'][name] = evaluate(expected, observed, times, name)
  
  if VERBOSITY:
    plot_prediction(expected, observed, name)

"""### Misc

Function to help implement the training and evaluation of the models.
"""

def plot_history (history, name):
  """ Plot of History
  
  Plot the history of loss in the training session of a model
  
  Arguments:
    history: the history returned by Keras fit of a model
    name: the name of the model
  """
  
  path = f"{PATH}plots/history/{name}"
  
  plt.plot(history.history['loss'])
  plt.plot(history.history['val_loss'])
  plt.title(name + ' Model Loss')
  plt.ylabel('Loss')
  plt.xlabel('Epoch')
  plt.legend(['train', 'test'], loc='upper left')
  plt.rcdefaults()
  
  plt.savefig(path + ".png", bbox_inches='tight')
  plt.savefig(path + ".pdf")
  
  plt.close('all')

def plot_prediction (Y, Y_hat, title):
  """ Plot Prediction
  
  Plot the prediction (Flow x Time) of what was expected and what
  was predicted.
  """

  for i in range(len(Y)):
    name = f"{title} ({str(i+1).zfill(2)} of {len(Y)})"
    path = f"{PATH}plots/prediction/{name}"
    
    plt.plot(Y[i])
    plt.plot(Y_hat[i])
    plt.title(title + 'Prediction')
    plt.ylabel('Flow')
    plt.xlabel('Time')
    plt.legend(['actual', 'prediction'], loc='upper left')
    plt.rcdefaults()

    plt.savefig(path + ".png", bbox_inches='tight')
    plt.savefig(path + ".pdf")

    plt.close('all')

def evaluate_precision_hit_ratio (Y, Y_hat):
  """ Trend Prediction Ratio Calculation
  
  Calculates the ratio of up/down prediction.
  
  Arguments:
    Y: the expected dataset.
    Y_hat: the observed dataset.
  """
  
  cnt = 0
  
  for i in range(len(Y)):
    if i < N_FUTURE:
      continue
      
    exp = Y[i] - Y[i - N_FUTURE]
    obs = Y_hat[i] - Y[i - N_FUTURE]
    
    if exp * obs > 0:
      cnt += 1
    
  return cnt / len(Y)

def evaluate_precision_bucket (Y, Y_hat):
  """ Precision Bucket Calculation
  
  Counts how many of the prediction got wronng by at most 2ˆx, x 
  being the bucket. There are 7 buckets, that is, the maximum error 
  calculated is 128.
  
  Arguments:
    Y: the expected dataset.
    Y_hat: the observed dataset.
  """
  
  n = 7 # the number of buckets
  buckets = [0] * n
  
  for i in range(len(Y)):
    diff = abs(Y[i] - Y_hat[i])
    
    for i in range (n):
      if diff <= 2**i:
        buckets[i] += 1
        break

  for i in range (n):
     buckets[i] = buckets[i] / len(Y)

  return tuple(buckets)

def evaluate_raw (expected, observed, times):
  """ Evaluate Raw Sessions 
  
  Evaluate each of the train&test sessions by RMSE, NRMSE, MAE, HR, PRE. 
  It will store the results in a object and return it.
  
  Arguments:
    expected: an array of expected instances of each train&test session.
    observed: an array of observed instances of each train&test session.
    times: an array of the time of each train&test session.
  """
  
  n = len(expected)

  for i in range(n):
    observed[i] = [max(o, 0) for o in observed[i]]
  
  raw = {
    'expected': expected,
    'observed': observed,
    'TIME': times,
    'RMSE': [0] * n,
    'NRMSE': [0] * n,
    'MAE': [0] * n,
    'HR': [0] * n,
    #'PRE': [0] * n,
  }
  
  for i in range(n):
    Y = expected[i]
    Y_hat = observed[i]
    time = times[i]

    raw['MAE'][i] = sklm.mean_absolute_error(Y, Y_hat)
    raw['RMSE'][i] = np.sqrt(sklm.mean_squared_error(Y, Y_hat))
    raw['NRMSE'][i] = raw['RMSE'][i] / np.std(Y)
    raw['HR'][i] = evaluate_precision_hit_ratio(Y, Y_hat)
    #raw['PRE'][i] = evaluate_precision_bucket(Y, Y_hat)
    
    if VERBOSITY:
      print(f"({i+1}/{n}) Test Size: {len(Y)}, Time: {time}s")
      print(f"\tRMSE: {raw['RMSE'][i]}")
      print(f"\tNRMSE: {raw['NRMSE'][i]}")
      print(f"\tMAE: {raw['MAE'][i]}")
      print(f"\tHit Ratio: {raw['HR'][i] * 100}%")

  return raw

def evaluate (expected, observed, times, name):
  """ Evaluate Sessions
  
  Evaluate models by RMSE, NRMSE, MAE, HR, PRE. It will store the 
  results in a object and return it.
  
  Arguments:
    expected: an array of expected instances of each 
      train&test session.
    observed: an array of observed instances of each 
      train&test session.
    times: an array of the time of each train&test session.
    name: the name of the model
  """
  n = len(expected)
  flatten = lambda l : [i for sl in l for i in sl]
  
  # Make the arrays serializable
  expected = list(map(list, expected))
  observed = list(map(list, observed))
  
  for i in range(n):
    expected[i] = list(map(float, expected[i]))
    observed[i] = list(map(float, observed[i]))
  
  raw = evaluate_raw(expected, observed, times)
  
  #n_buckets = len(raw['PRE'])
  #_pre = [[pre[i] for pre in raw['PRE']] for i in range(n_buckets)]
  
  eva = {
    'TIME': int(sum(times)),
    'RMSE': float(np.mean(raw['RMSE'])),
    'NRMSE': float(np.mean(raw['NRMSE'])),
    'MAE': float(np.mean(raw['MAE'])),
    'HR': float(np.mean(raw['HR'])),
    #'PRE': [float(np.mean(p)) for p in _pre],
    'has_negative': (min(flatten(observed)) < 0),
    'raw': raw
  }
  
  print(f"\n{name} Final Result:")
  print(f"\tTotal Time: {eva['TIME']}s")
  print(f"\tRMSE: {eva['RMSE']}")
  print(f"\tNRMSE: {eva['NRMSE']}")
  print(f"\tMAE: {eva['MAE']}")
  print(f"\tHit Ratio: {eva['HR'] * 100}%")
  #print(f"\tPrecision: {eva['PRE']}")
    
  return eva

def generate_dataset(data, useB, n_steps, n_future):
  """ Generate Dataset
  
  Generate a dataset provided a sequence. Reshape the sequence in rolling intervals from [samples, timesteps] into 
  [samples, timesteps, features] and split the sequence. The split the sequence in rolling intervals with a corresponding value 
  like the example bellow.

  Ex: split_sequence([1, 2, 3, 4, 5], 3) #([[1, 2, 3], [2, 3, 4]], [4, 5])
  
  Arguments:
    raw_seq: the sequence to reshape.
    useB: if the dataset is more complex or not.
    n_steps: size of the rolling interval
    n_future: the distance to the interval the value should be.  
  """

  sequence = np.array(data if useB else data['Flow'])

  n = len(sequence)
  X, Y = list(), list()

  for i in range(n):
    j = i + n_steps
    k = j + n_future

    if k >= n:
      break

    seq_x, seq_y = sequence[i:j], sequence[k]
    X.append(seq_x)	
    Y.append(seq_y[0] if useB else seq_y)

  X, Y = np.array(X), np.array(Y)	
  
  if not useB:
    X = X.reshape((X.shape[0], X.shape[1], 1))

  return X, Y

"""### Moving Average (Baseline)

This implementation just get the mean of every flow value in the input and place it as output.
"""

def moving_average (data):
  global result_data

  name = "Moving Average"
  
  X, Y = generate_dataset(data, False, N_STEPS, N_FUTURE)

  cv = WalkingForwardTimeSeriesSplit(n_splits=N_SPLITS)
  expected, observed, times = [], [], []

  for train_index, test_index in cv.split(X):
    X_test = X[test_index]
    Y_test = Y[test_index]
  
    start_time = time.time()
    Y_hat = [np.mean(x) for x in X_test]
    end_time = time.time()
    
    expected.append(Y_test)
    observed.append(Y_hat)
    times.append(end_time - start)
    
  result_data['results'][name] = evaluate(expected, observed, times, name)
  
  if VERBOSITY:
    plot_prediction(expected, observed, name)

"""### Naive (Baseline)

This implementation just use the last value of input as output.
"""

def naive (data):
  global result_data

  name = "Naive"
  
  X, Y = generate_dataset(data, False, N_STEPS, N_FUTURE)
  X = X.reshape(X.shape[0], X.shape[1])

  cv = WalkingForwardTimeSeriesSplit(n_splits=N_SPLITS)
  expected, observed, times = [], [], []

  for train_index, test_index in cv.split(X):
    X_test = X[test_index]
    Y_test = Y[test_index]
  
    start_time = time.time()
    Y_hat = [x[-1] for x in X_test]
    end_time = time.time()
    
    expected.append(Y_test)
    observed.append(Y_hat)
    times.append(end_time - start)
    
  result_data['results'][name] = evaluate(expected, observed, times, name)
  
  if VERBOSITY:
    plot_prediction(expected, observed, name)

"""### Random Forest

This implementation is based on [Random Forest Algorithm with Python and Scikit-Learn](https://stackabuse.com/random-forest-algorithm-with-python-and-scikit-learn/)
"""

from sklearn.ensemble import RandomForestRegressor

def random_forest_grid(data, useB):
  global result_data

  name = "RF Grid B" if useB else "RF Grid A"
  
  X, Y = generate_dataset(data, useB, N_STEPS, N_FUTURE)
  X = X.reshape(X.shape[0], X.shape[1] * X.shape[2])
    
  param_grid = {
    'bootstrap': [True, False],
    'max_depth': [8, 16, 32, 64, None],
    'n_estimators': [50, 100, 200, 400],
  }
  model = sklearn.ensemble.RandomForestRegressor(max_features='auto', random_state=0)
  scoring = 'neg_mean_squared_error'
  tscv = WalkingForwardTimeSeriesSplit(n_splits=N_SPLITS)
  grid_search = GridSearchCV(estimator=model, param_grid=param_grid, scoring=scoring, cv=tscv, n_jobs=4, verbose=2)

  grid_search.fit(X, Y)

  best_model = grid_search.best_estimator_

  expected, observed, times = [], [], []

  cv = WalkingForwardTimeSeriesSplit(n_splits=N_SPLITS)

  for train_index, test_index in cv.split(X):
    X_train, X_test = X[train_index], X[test_index]
    Y_train, Y_test = Y[train_index], Y[test_index]

    start_time = time.time()
    best_model.fit(X_train, Y_train)
    end_time = time.time()
    
    expected.append(Y_test)
    observed.append(best_model.predict(X_test))
    times.append(end_time - start_time)
    
  res = evaluate(expected, observed, times, name)
  res['params'] = grid_search.best_params_

  store(res, "results/grid", f"{name}")

def random_forest(data, useB):
  global result_data
  
  name = "RF B" if useB else "RF A"
  
  model = sklearn.ensemble.RandomForestRegressor(n_estimators=100, max_features='auto', random_state=0)

  X, Y = generate_dataset(data, useB, N_STEPS, N_FUTURE)
  X = X.reshape(X.shape[0], X.shape[1] * X.shape[2])

  expected, observed, times = [], [], []
  tscv = WalkingForwardTimeSeriesSplit(n_splits=N_SPLITS)

  for train_index, test_index in tscv.split(X):
    X_train, X_test = X[train_index], X[test_index]
    Y_train, Y_test = Y[train_index], Y[test_index]

    start_time = time.time()
    model.fit(X_train, Y_train)
    end_time = time.time()
    
    expected.append(Y_test)
    observed.append(model.predict(X_test))
    times.append(end_time - start_time)
    
  result_data['results'][name] = evaluate(expected, observed, times, name)
  
  if VERBOSITY:
    plot_prediction(expected, observed, name)

"""### Support Vector Machine"""

from sklearn import svm

def support_vector_machine_grid(data, useB):
  global result_data

  name = "SVM Grid B" if useB else "SVM Grid A"
  
  X, Y = generate_dataset(data, useB, N_STEPS, N_FUTURE)
  X = X.reshape(X.shape[0], X.shape[1] * X.shape[2])
    
  param_grid = {
    'C': [1.0, 10.0, 100.0],
    'gamma': list(np.logspace(-2, 2, 2)) + ['scale'],
    'epsilon': [0.01, 0.1, 1]
  }
  model = svm.SVR()
  scoring = 'neg_mean_squared_error'
  tscv = WalkingForwardTimeSeriesSplit(n_splits=N_SPLITS)
  grid_search = GridSearchCV(estimator=model, param_grid=param_grid, scoring=scoring, cv=tscv, n_jobs=4, verbose=2)

  grid_search.fit(X, Y)

  best_model = grid_search.best_estimator_

  expected, observed, times = [], [], []

  cv = WalkingForwardTimeSeriesSplit(n_splits=N_SPLITS)

  for train_index, test_index in cv.split(X):
    X_train, X_test = X[train_index], X[test_index]
    Y_train, Y_test = Y[train_index], Y[test_index]

    start_time = time.time()
    best_model.fit(X_train, Y_train)
    end_time = time.time()
    
    expected.append(Y_test)
    observed.append(best_model.predict(X_test))
    times.append(end_time - start_time)
    
  res = evaluate(expected, observed, times, name)
  res['params'] = grid_search.best_params_

  store(res, "results/grid", f"{name}")

def support_vector_machine(data, useB):
  global result_data
  
  name = "SVM B" if useB else "SVM A"
  
  model = svm.SVR(gamma='scale', C=1.0, epsilon=0.2)

  X, Y = generate_dataset(data, useB, N_STEPS, N_FUTURE)
  X = X.reshape(X.shape[0], X.shape[1] * X.shape[2])

  expected, observed, times = [], [], []
  tscv = WalkingForwardTimeSeriesSplit(n_splits=N_SPLITS)

  for train_index, test_index in tscv.split(X):
    X_train, X_test = X[train_index], X[test_index]
    Y_train, Y_test = Y[train_index], Y[test_index]

    start_time = time.time()
    model.fit(X_train, Y_train)
    end_time = time.time()
    
    expected.append(Y_test)
    observed.append(model.predict(X_test))
    times.append(end_time - start_time)
    
  result_data['results'][name] = evaluate(expected, observed, times, name)
  
  if VERBOSITY:
    plot_prediction(expected, observed, name)

"""### LSTM"""

from keras.layers import LSTM

def create_lstm(input_shape):
  def create(n=100, activation='relu'):
    model = Sequential()		

    model.add(LSTM(n, activation=activation, input_shape=input_shape))		
    model.add(Dense(1))		

    model.compile(optimizer='adam', loss='mse', metrics = ["accuracy"])	

    return model

  return create

def lstm_grid(data, useB):		
  global result_data

  name = "LSTM Grid B" if useB else "LSTM Grid A"
        
  X, Y = generate_dataset(data, useB, N_STEPS, N_FUTURE)

  param_grid = {		
    'activation': ['relu', 'sigmoid', None],
    'n': [50, 100, 200, 400],
    'batch_size': [8, 16, 32, 64]
  }
  model = KerasClassifier(build_fn=create_lstm((X.shape[1], X.shape[2])), validation_split=0.2, epochs=15, verbose=0)
  scoring = 'neg_mean_squared_error'
  tscv = WalkingForwardTimeSeriesSplit(n_splits=N_SPLITS)
  grid_search = GridSearchCV(estimator=model, param_grid=param_grid, scoring=scoring, cv=tscv, n_jobs=4, verbose=2)		
      
  grid_search.fit(X, Y)

  best_model = grid_search.best_estimator_

  expected, observed, times = [], [], []

  cv = WalkingForwardTimeSeriesSplit(n_splits=N_SPLITS)

  for train_index, test_index in cv.split(X):
    X_train, X_test = X[train_index], X[test_index]
    Y_train, Y_test = Y[train_index], Y[test_index]

    start_time = time.time()
    best_model.fit(X_train, Y_train)
    end_time = time.time()
    
    expected.append(Y_test)
    observed.append(best_model.predict(X_test))
    times.append(end_time - start_time)
    
  res = evaluate(expected, observed, times, name)
  res['params'] = grid_search.best_params_

  store(res, "results/grid", f"{name}")

def lstm (data, useB): 
  global result_data
  
  name = "LSTM B" if useB else "LSTM A"

  X, Y = generate_dataset(data, useB, N_STEPS, N_FUTURE)

  model = create_lstm((X.shape[1], X.shape[2]))()
  
  expected, observed, times = [], [], []
  tscv = WalkingForwardTimeSeriesSplit(n_splits=N_SPLITS)

  for train_index, test_index in tscv.split(X):
    X_train, X_test = X[train_index], X[test_index]
    Y_train, Y_test = Y[train_index], Y[test_index]
  
    start_time = time.time()
    history = model.fit(X_train, Y_train, validation_split=0.2, batch_size=64, epochs=15, verbose=0)
    end_time = time.time()

    expected.append(Y_test)
    observed.append(model.predict(X_test))
    times.append(end_time - start_time)

    if VERBOSITY:
      plot_name = f"{name} ({str(len(times)).zfill(2)} of {N_SPLITS})"
      plot_history(history, plot_name)

  result_data['results'][name] = evaluate(expected, observed, times, name)
  
  if VERBOSITY:
    plot_prediction(expected, observed, name)

"""### GRU"""

from keras.layers import GRU

def create_gru(input_shape):
  def create(n=100, activation='relu'):
    model = Sequential()		

    model.add(GRU(n, activation=activation, input_shape=input_shape))		
    model.add(Dense(1))		

    model.compile(optimizer='adam', loss='mse', metrics = ["accuracy"])		

    return model		
    
  return create

def gru_grid(data, useB):		
  global result_data

  name = "GRU Grid B" if useB else "GRU Grid A"
        
  X, Y = generate_dataset(data, useB, N_STEPS, N_FUTURE)

  param_grid = {		
    'activation': ['relu', 'sigmoid', None],
    'n': [50, 100, 200, 400],
    'batch_size': [8, 16, 32, 64]
  }
  model = KerasClassifier(build_fn=create_gru((X.shape[1], X.shape[2])), validation_split=0.2, epochs=15, verbose=0)
  scoring = 'neg_mean_squared_error'
  tscv = WalkingForwardTimeSeriesSplit(n_splits=N_SPLITS)
  grid_search = GridSearchCV(estimator=model, param_grid=param_grid, scoring=scoring, cv=tscv, n_jobs=4, verbose=2)		
      
  grid_search.fit(X, Y)

  best_model = grid_search.best_estimator_

  expected, observed, times = [], [], []

  cv = WalkingForwardTimeSeriesSplit(n_splits=N_SPLITS)

  for train_index, test_index in cv.split(X):
    X_train, X_test = X[train_index], X[test_index]
    Y_train, Y_test = Y[train_index], Y[test_index]

    start_time = time.time()
    best_model.fit(X_train, Y_train)
    end_time = time.time()
    
    expected.append(Y_test)
    observed.append(best_model.predict(X_test))
    times.append(end_time - start_time)
    
  res = evaluate(expected, observed, times, name)
  res['params'] = grid_search.best_params_

  store(res, "results/grid", f"{name}")

def gru (data, useB): 
  global result_data
  
  name = "GRU B" if useB else "GRU A"

  X, Y = generate_dataset(data, useB, N_STEPS, N_FUTURE)

  model = create_gru((X.shape[1], X.shape[2]))()
  
  expected, observed, times = [], [], []
  tscv = WalkingForwardTimeSeriesSplit(n_splits=N_SPLITS)

  for train_index, test_index in tscv.split(X):
    X_train, X_test = X[train_index], X[test_index]
    Y_train, Y_test = Y[train_index], Y[test_index]
  
    start_time = time.time()
    history = model.fit(X_train, Y_train, validation_split=0.2, batch_size=64, epochs=15, verbose=0)
    end_time = time.time()

    expected.append(Y_test)
    observed.append(model.predict(X_test))
    times.append(end_time - start_time)

    if VERBOSITY:
      plot_name = f"{name} ({str(len(times)).zfill(2)} of {N_SPLITS})"
      plot_history(history, plot_name)

  result_data['results'][name] = evaluate(expected, observed, times, name)
  
  if VERBOSITY:
    plot_prediction(expected, observed, name)

"""## Comparison Util

### Misc
"""

def run_models():
  global result_data
  
  result_data = {
      'results': {},
      'meta': {}
  }

  data = retrieve_data(FLOW_INTERVAL)

  moving_average(data)
  naive(data)
  random_forest(data, False)
  random_forest(data, True)
  support_vector_machine(data, False)
  support_vector_machine(data, True)
  lstm(data, False)
  lstm(data, True)
  gru(data, False)
  gru(data, True)

  store_results()

def plot_precision_bucket (results):
  """ Plot Precision Bucket 
  
  Plot a stack box graph of the precision mesuared by the buckets.
  
  """
  
  path = f"{PATH}plots/precision"
  
  N = len(results)
    
  ind = np.arange(N)    # the x locations for the groups
  width = 0.35       # the width of the bars: can also be len(x) sequence
  
  pre = []
  bott = []
  
  models = list(results.keys())

  n_buckets = len(results[models[0]]['PRE'])
    
  for i in range(n_buckets):
    pre.append([v["PRE"][i] for v in results.values()])
    
    if i == 0:
      bott.append([0] * N)
    else:
      bott.append([bott[i-1][j] + pre[i-1][j]  for j in range(N)])
  
  p = []
  leg_lin = []
  leg_lab = []
  
  for i in range(n_buckets):
    _p = plt.bar(ind, tuple(pre[i]), width, bottom=tuple(bott[i]))
    
    leg_lin.append(_p[0])
    leg_lab.append(f"Bucket of {2**i}")
    p.append(_p)

  plt.ylabel('Scores')
  plt.title('Precision by model and bucket')
  plt.xticks(ind, models, rotation=90)
  plt.yticks(np.arange(0, 1.05, 0.05))
  plt.legend(tuple(leg_lin), tuple(leg_lab))
  
  plt.savefig(path + ".png", bbox_inches='tight')
  plt.savefig(path + ".pdf")

  plt.close('all')

def plot_performance(results, metric, y_label, title):
  """ Plot Performance
  
  Plot a bar graph of the performance of some metric
  
  Arguments:
    metric: the name of the property of the metric
    y_label: the name of the label of the metric
    title: the title of the plot
  """
  
  path = f"{PATH}plots/performance/{title} Performance Bar"
  
  models = tuple(results.keys())
  y_pos = np.arange(len(models))
  performance = [v[metric] for v in results.values()]

  plt.rcdefaults()
  plt.bar(y_pos, performance, align='center', alpha=0.5)
  plt.xticks(y_pos, models, rotation=90)
  plt.ylabel(y_label)
  plt.title(title)

  plt.savefig(path + ".png", bbox_inches='tight')
  plt.savefig(path + ".pdf")
    
  plt.close('all')

def plot_performance_improved(results, metric, y_label, title):
  """ Plot Performance Improved
  
  Plot a box graph of the performance of some metric
  
  Arguments:
    results: the struct that contain the results of the models
    metric: the name of the property of the metric
    y_label: the name of the label of the metric
    title: the title of the plot
  """
  
  path = f"{PATH}plots/performance/{title} Performance Boxes"
  
  fig, ax_plot = plt.subplots()
  
  ax_plot.set_title(title)
  ax_plot.set_xlabel(y_label)
  ax_plot.set_ylabel('Model')
  
  bplot = ax_plot.boxplot([v['raw'][metric] for v in results.values()], vert=False)
  ax_plot.set_yticklabels(list(results.keys()))
  
  plt.savefig(path + ".png", bbox_inches='tight')
  plt.savefig(path + ".pdf")
    
  plt.close('all')

def plot_snapshot(results):
  # plot_precision_bucket(results)
  # plot_performance(results, 'TIME', 'Seconds', 'Training Time Comparison')
  plot_performance_improved(results, 'TIME', 'Seconds', 'Training Time Comparison')
  # plot_performance(results, 'RMSE', 'RMSE', 'Root Mean Square Error Comparison')
  plot_performance_improved(results, 'RMSE', 'RMSE', 'Root Mean Square Error Comparison')
  # plot_performance(results, 'NRMSE', 'NRMSE', 'Normalized Root Mean Square Error Comparison')
  plot_performance_improved(results, 'NRMSE', 'NRMSE', 'Normalized Root Mean Square Error Comparison')
  # plot_performance(results, 'MAE', 'MAE', 'Max Absolute Error Comparison')
  plot_performance_improved(results, 'MAE', 'MAE', 'Max Absolute Error Comparison')
  # plot_performance(results, 'HR', 'Percentage', 'Hit Ratio Comparison')
  plot_performance_improved(results, 'HR', 'Percentage', 'Hit Ratio Comparison')

def plot_results_comparison(name, xlabel, xticks, metric):
  path = f"{PATH}plots/comparison/{name.lower().replace(' ', '_')}_{metric.lower()}"
  models = [*comparison_data[0]['results']]
  
  for model in models:
    datapoints = [result['results'][model][metric] for result in comparison_data]
    plt.plot(datapoints) 

  plt.title(name)
  plt.ylabel(metric)
  plt.xlabel(xlabel)
  plt.xticks(np.arange(len(xticks)), xticks)
  plt.legend(models, loc='upper left')
  plt.rcdefaults()

  plt.savefig(path + ".png", bbox_inches='tight')
  plt.savefig(path + ".pdf")
    
  plt.close('all')

"""### Comparisons"""

def compare_results_by_n_split(values):
  global N_SPLITS
  global comparison_data
  
  aux = N_SPLITS
  comparison_data = []
  
  for value in values:
    N_SPLITS = value

    start_time = time.time()
    run_models()
    end_time = time.time()
    
    comparison_data.append(copy.deepcopy(result_data))
    plot_snapshot(comparison_data[-1])

    print(f"({len(comparison_data)} of {len(values)}) Finished Running with N_SPLITS {value} in {end_time - start_time} seconds")

  store_comparisons('_n_split_comparison')
  
  N_SPLITS = aux

def compare_results_by_seeable_past(values):
  global SEEABLE_PAST
  global N_STEPS
  global comparison_data
  
  aux = SEEABLE_PAST
  comparison_data = []
  
  for value in values:
    SEEABLE_PAST = value
    N_STEPS = SEEABLE_PAST * 60 // FLOW_INTERVAL

    start_time = time.time()
    run_models()
    end_time = time.time()
    
    comparison_data.append(copy.deepcopy(result_data))
    plot_snapshot(comparison_data[-1])

    print(f"({len(comparison_data)} of {len(values)}) Finished Running with SEEABLE_PAST {value} in {end_time - start_time} seconds")

  store_comparisons('_seeable_past_comparison')
  
  SEEABLE_PAST = aux
  N_STEPS = SEEABLE_PAST * 60 // FLOW_INTERVAL

def compare_results_by_flow_interval(values):
  global FLOW_INTERVAL
  global N_STEPS
  global N_FUTURE
  global DAY_SIZE
  global WEEK_SIZE
  global comparison_data
  
  aux = FLOW_INTERVAL
  comparison_data = []
  
  for value in values:
    FLOW_INTERVAL = value
    N_STEPS = SEEABLE_PAST * 60 // FLOW_INTERVAL
    N_FUTURE = PREDICT_IN_FUTURE * 60 // FLOW_INTERVAL
    DAY_SIZE = (24 * 3600) // FLOW_INTERVAL  
    WEEK_SIZE = 7 * DAY_SIZE

    start_time = time.time()
    run_models()
    end_time = time.time()
    
    comparison_data.append(copy.deepcopy(result_data))
    plot_snapshot(comparison_data[-1])

    print(f"({len(comparison_data)} of {len(values)}) Finished Running with FLOW_INTERVAL {value} in {end_time - start_time} seconds")

  store_comparisons('_flow_interval_comparison')
  
  FLOW_INTERVAL = aux
  N_STEPS = SEEABLE_PAST * 60 // FLOW_INTERVAL
  N_FUTURE = PREDICT_IN_FUTURE * 60 // FLOW_INTERVAL
  DAY_SIZE = (24 * 3600) // FLOW_INTERVAL  
  WEEK_SIZE = 7 * DAY_SIZE

def compare_results_by_predict_in_future(values):
  global PREDICT_IN_FUTURE
  global N_FUTURE
  global comparison_data
  
  aux = PREDICT_IN_FUTURE
  comparison_data = []
  
  for value in values:
    PREDICT_IN_FUTURE = value
    N_FUTURE = PREDICT_IN_FUTURE * 60 // FLOW_INTERVAL

    start_time = time.time()
    run_models()
    end_time = time.time()
    
    comparison_data.append(copy.deepcopy(result_data))
    plot_snapshot(comparison_data[-1])

    print(f"({len(comparison_data)} of {len(values)}) Finished Running with PREDICT_IN_FUTURE {value} in {end_time - start_time} seconds")

  store_comparisons('_predict_future_comparison')
  
  PREDICT_IN_FUTURE = aux
  N_FUTURE = PREDICT_IN_FUTURE * 60 // FLOW_INTERVAL

"""## Train&Test

Run all the models and store the results at the end
"""

# Model Parameters

SEEABLE_PAST = 180 # in minutes

PREDICT_IN_FUTURE = 15 # in minutes

FLOW_INTERVAL = 450 # the interval size for each flow

N_SPLITS = 4

# Derivated Model Parameters

N_STEPS = SEEABLE_PAST * 60 // FLOW_INTERVAL # the number of flows to see in the past

N_FUTURE = PREDICT_IN_FUTURE * 60 // FLOW_INTERVAL # how much in the future we want to predict (0 = predict the flow on the next 5 minutes)

DAY_SIZE = (24 * 60 * 60) // FLOW_INTERVAL  

WEEK_SIZE = (7 * 24 * 60 * 60) // FLOW_INTERVAL

VERBOSITY = True

result_data = {
    'results': {},
    'meta': {}
}

data = retrieve_data(FLOW_INTERVAL)

# random_forest(data, False)

random_forest_grid(data, False)

random_forest_grid(data, True)

# support_vector_machine(data, False)

support_vector_machine_grid(data, False)

support_vector_machine_grid(data, True)

# lstm(data, False)

lstm_grid(data, False)

lstm_grid(data, True)

# gru(data, False)

gru_grid(data, False)

gru_grid(data, True)

"""## Compare"""

VERBOSITY = False

predict_futures = [15, 30, 45, 60]
compare_results_by_predict_in_future(predict_futures)

plot_results_comparison('Predict Future for Training Comparison', 'Time in the Future in Minutes', predict_futures, 'NRMSE')

plot_results_comparison('Predict Future for Training Comparison', 'Time in the Future in Minutes', predict_futures, 'RMSE')

plot_results_comparison('Predict Future for Training Comparison', 'Time in the Future in Minutes', predict_futures, 'MAE')

plot_results_comparison('Predict Future for Training Comparison', 'Time in the Future in Minutes', predict_futures, 'HR')

plot_results_comparison('Predict Future for Training Comparison', 'Time in the Future in Minutes', predict_futures, 'TIME')

flow_intervals = [150, 300, 450]
compare_results_by_flow_interval(flow_intervals)

plot_results_comparison('Flow Interval for Training Comparison', 'Flow Size in Seconds', flow_intervals, 'NRMSE')

plot_results_comparison('Flow Interval for Training Comparison', 'Flow Size in Seconds', flow_intervals, 'RMSE')

plot_results_comparison('Flow Interval for Training Comparison', 'Flow Size in Seconds', flow_intervals, 'MAE')

plot_results_comparison('Flow Interval for Training Comparison', 'Flow Size in Seconds', flow_intervals, 'HR')

plot_results_comparison('Flow Interval for Training Comparison', 'Flow Size in Seconds', flow_intervals, 'TIME')

seeable_pasts = [60, 120, 240, 480]
compare_results_by_seeable_past(seeable_pasts)

plot_results_comparison('Seeable Past for Training Comparison', 'Seeable Past in Seconds', seeable_pasts, 'NRMSE')

plot_results_comparison('Seeable Past for Training Comparison', 'Seeable Past in Seconds', seeable_pasts, 'RMSE')

plot_results_comparison('Seeable Past for Training Comparison', 'Seeable Past in Seconds', seeable_pasts, 'MAE')

plot_results_comparison('Seeable Past for Training Comparison', 'Seeable Past in Seconds', seeable_pasts, 'HR')

plot_results_comparison('Seeable Past for Training Comparison', 'Seeable Past in Seconds', seeable_pasts, 'TIME')

n_splits = [1, 2, 4, 8]
compare_results_by_n_split(n_splits)

plot_results_comparison('Number of Splits for Training Comparison', 'Number of Splits', n_splits, 'NRMSE')

plot_results_comparison('Number of Splits for Training Comparison', 'Number of Splits', n_splits, 'RMSE')

plot_results_comparison('Number of Splits for Training Comparison', 'Number of Splits', n_splits, 'MAE')

plot_results_comparison('Number of Splits for Training Comparison', 'Number of Splits', n_splits, 'HR')

plot_results_comparison('Number of Splits for Training Comparison', 'Number of Splits', n_splits, 'TIME')

"""## Observations:

+ For the evaluation of the RNN and it's variations was used the Walking Forward methodology so that we had many test sessions and all training sessions where the same size [[1]](https://towardsdatascience.com/time-series-nested-cross-validation-76adba623eb9)
+ To remove the cross-validation of the GridSearchCV we based on the answer in [scikit learn discussion - allow GridSearchCV to work with params={} or cv=1](https://github.com/scikit-learn/scikit-learn/issues/2048)
+ Grid Search on Keras was based on the article [How to Grid Search Hyperparameters for Deep Learning Models in Python With Keras](https://machinelearningmastery.com/grid-search-hyperparameters-deep-learning-models-python-keras/)
"""