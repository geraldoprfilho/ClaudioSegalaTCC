# -*- coding: utf-8 -*-
"""tcc.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1fpyYtJyD0OtH2pP_DKB9QpaTzfUICiMu

# TODO

+ Discover why the result are being inconsistent
+ Discover if there are negative predictions and NaNs
+ Discover why some results came negative (that does not make sense, but the evaluation with log is getting errors)

# Install Dependencies

In this phase we have to download all the dependencies that our code will need
"""

!pip install tensorflow
!pip install pandas
!pip install matplotlib
!pip install numpy
!pip install sklearn
!pip install keras

"""# Mount Drive

Connect to Google Drive of 'alfredcoinworth'
"""

import google as g # To connect with google drive
g.colab.drive.mount('/content/drive')

"""# Define headers

In this phase we have to declare all the libraries that we will use.
"""

import tensorflow as tf # machine learning library
import pandas as pd # data manipulation library
import matplotlib.pyplot as plt # plot library
import numpy as np # math library
import datetime as dt # to discover week day
import time as tm # to convert to seconds
import sklearn as skl # regression templates library
import sklearn.metrics as sklm # metrics
import random as rnd # random
import statistics as st # statistics

from keras.models import Sequential
from keras.layers import LSTM, GRU, SimpleRNN, Dense, Dropout

"""# Plot & Print Functions"""

def plot_flow (seq):
  plt.figure(figsize=(80, 10))
  plt.plot(raw_seq)

def plot_history (history, name):
  plt.plot(history.history['loss'])
  plt.plot(history.history['val_loss'])
  plt.title(name + ' Model Loss')
  plt.ylabel('Loss')
  plt.xlabel('Epoch')
  plt.legend(['train', 'test'], loc='upper left')
  plt.figure(figsize=(100, 100))
  plt.show(name + "ind")
  plt.close('all')
  
def print_metrics (Y_hat, Y_test):
  #evs = sklm.explained_variance_score(Y_test, Y_hat)
  mse = sklm.mean_squared_error(Y_test, Y_hat)
  mae = sklm.mean_absolute_error(Y_test, Y_hat)
  #msle = sklm.mean_squared_log_error(Y_test, Y_hat)
  me = sklm.max_error(Y_test, Y_hat)
  
  #print(f"EVS: {evs}")
  print(f"RMSE: {np.sqrt(mse)}")
  print(f"MSE: {mse}")
  print(f"MAE: {mae}")
  #print(f"MSLE: {msle}")
  print(f"Max Error: {me}")

"""# Data Retrieval & Transformation

In this phase we have to get the data stored in Google Drive and remove the columns that we won't need. Also, convert some of them to other types.
"""

def data_analysis (data):
  print(f"This data is from <{data['Date'].min()}> to <{data['Date'].max()}>")
  print(f"It contains {len(data['Date'])} entries")

def prepare_data(data):
  """ Prepare the data
  
  This will fix types of the dataframe to use time as seconds instead of string,
  use week day instead of date as string, use speed as float instead of string. 
  Also, will drop columns that are not necessary.
  """
   
  data['Time'] = data['Time'].apply(lambda x : tm.strptime(x, '%H:%M:%S'))
  data['Time'] = data['Time'].apply(lambda x : dt.timedelta(hours=x.tm_hour,minutes=x.tm_min,seconds=x.tm_sec).total_seconds())
  data['Time'] = data['Time'].apply(lambda x : int(x))

  data['Date'] = pd.to_datetime(data['Date'], format='%Y/%m/%d')
  
  data['WeekDay'] = data['Date'].apply(lambda x : x.weekday())

  data['Speed'].apply(lambda x : float(x))
  
  return data


# Get data from Google Drive
col_names = ['Sensor', 'Date', 'Time', 'Lane', 'Speed', 'Max Speed', 'Size']
all_data = pd.read_csv('/content/drive/My Drive/TCC/chunks/all_data_sorted.csv', ';', header=None, names=col_names)
data = all_data[all_data['Sensor'] == 'RSI128']
data = data.drop(columns=['Sensor','Lane','Max Speed','Size'])
data = prepare_data(data)

data_analysis(data)

"""# Configure Hyperparameters"""

VALIDATION_SPLIT = 0.25

TRAIN_SPLIT = 0.8

SEEABLE_PAST = 100 # in minutes

PREDICT_IN_FUTURE = 60 # in minutes

FLOW_INTERVAL = 150 # the interval size for each flow

MULTIVARIATE = False # if we are gonna use multiple data or not

# Derivated

N_STEPS = SEEABLE_PAST * 60 // FLOW_INTERVAL # the number of flows to see in the past

N_FUTURE = PREDICT_IN_FUTURE * 60 // FLOW_INTERVAL # how much in the future we want to predict (0 = predict the flow on the next 5 minutes)

N_FEATURES = 9 if MULTIVARIATE else 1

DAY_SIZE = (24 * 3600) // FLOW_INTERVAL  

WEEK_SIZE = 7 * DAY_SIZE

"""# Get Flow

This will transform the time series of register cars that passed in a array of flow per 5 minute.
"""

def get_weekday(n):
  return tuple([1 if n == i else 0 for i in range(7)])

def get_flow (data):
  """ Extract flow from data
  
  This will transform the time series of register cars that passed in a array of
  flow per 'timeInterval' seconds.
  """
  
  date = np.asarray(data['Date'])
  weekDay = np.asarray(data['WeekDay'])
  time = np.asarray(data['Time'])
  speed = np.asarray(data['Speed'])
  
  dateControl = date[0] #seta o controle de data com o primeiro dia do chunk
  timeBlock = FLOW_INTERVAL
  countFlow = 0
  accSpeed = 0
  flowData = []

  for i in range(len(speed)):
    #if pd.to_datetime(date[i], format='%Y/%m/%d') == pd.to_datetime('2016-05-22', format='%Y/%m/%d'):
    #    break
    if time[i] >= timeBlock: # init a new time block
      w0, w1, w2, w3, w4, w5, w6 = get_weekday(weekDay[i])
      avgSpeed = accSpeed // countFlow if countFlow else 0
      flowData.append((countFlow, avgSpeed, w0, w1, w2, w3, w4, w5, w6)) 
      timeBlock += FLOW_INTERVAL
      countFlow = 0
      accSpeed = 0
      
    if date[i] > dateControl: # reset on day change
      dateControl = date[i]
      timeBlock = FLOW_INTERVAL 
      countFlow = 0
      accSpeed = 0
      
    if time[i] < timeBlock: # add car on flow
      countFlow += 1
      accSpeed += speed[i]
  
  return flowData if MULTIVARIATE else [t[0] for t in flowData]


raw_seq = get_flow(data)

plot_flow(raw_seq)

"""# Prepare for dataset for training

+ Adjust the dataset
+ Split the dataset
+ Create storage for the results
"""

def split_sequence(sequence):
  """ Split a univariate sequence into samples
  
  This function will split a sequence into many samples in the form of two
  arrays. The first array will have as elements arrays of size n_step and the 
  second array will have as elements a integer. 
  Example:
  
  split_sequence([1, 2, 3, 4, 5], 3) #=> ([[1, 2, 3], [2, 3, 4]], [4, 5])
  """
  
  n = len(sequence)
  X, Y = list(), list()
  
  for i in range(n):
    # find the end of this pattern
    end_ix = i + N_STEPS

    # check if we are beyond the sequence
    if end_ix + N_FUTURE > n-1:
      break

    # gather input and output parts of the pattern
    seq_x, seq_y = sequence[i:end_ix], sequence[end_ix + N_FUTURE]
    X.append(seq_x)
    Y.append(seq_y[0] if MULTIVARIATE else seq_y)

  return np.array(X), np.array(Y)


def reshape_flow (raw_seq):  
  # split into samples
  X, Y = split_sequence(raw_seq)

  # reshape from [samples, timesteps] into [samples, timesteps, features]
  X = X.reshape((X.shape[0], X.shape[1], N_FEATURES))
  
  return X, Y


X, Y = reshape_flow(raw_seq)

"""# Baseline: Random"""

def base_rand (Y):
  Y_hat = [rnd.randint(0, 100) for i in range(len(Y))]
    
  print_metrics(Y_hat, Y)
  
  
base_rand(Y)

"""# Baseline: Default"""

def base_default (X, Y):
  Y_hat = [st.mean([v[0] for v in x]) for x in X]
    
  print_metrics(Y_hat, Y)
  
  
base_default(X, Y)

"""# Baseline: ARIMA"""

# TODO: check if this ARIMA is ok
def base_arima (X):
  size = int(len(X) * TRAIN_SPLIT)
  acc = X[:size]
  Y = X[size+N_FUTURE:]
  Y_hat = []
  
  for t in range(len(Y)):
    model = ARIMA(acc)
    model_fit = model.fit(disp=0)
    
    start = len(acc)
    end = start + N_FUTURE
    
    prediction = model_fit.forecast(start=start, end=end+1)
    
    Y_hat.append(prediction[-1])    
    acc.append(X[size + t])

  mse = np.sqrt(sklm.mean_squared_error(Y_hat, Y))
  print(f"MSE: {mse}")
  
base_arima([e[0] for e in raw_seq])

"""# GRU"""

def gru (X, Y): 
  n_weeks = len(X) // WEEK_SIZE
  
  # define model
  model = Sequential()
  model.add(GRU(50, activation='relu', input_shape=(N_STEPS, N_FEATURES)))
  model.add(Dense(1))
  
  # compile model
  model.compile(optimizer='adam', loss='mse', metrics = ["accuracy"])
  
  # fit model
  res = 0.0

  for i in range(n_weeks - 4):
    X_train = X[(WEEK_SIZE*i):(WEEK_SIZE*(i+3))]
    Y_train = Y[(WEEK_SIZE*i):(WEEK_SIZE*(i+3))]
    X_test = X[(WEEK_SIZE*(i+3)):(WEEK_SIZE*(i+4))]
    Y_test = Y[(WEEK_SIZE*(i+3)):(WEEK_SIZE*(i+4))]
    
    train_sz = TEST_SIZE * i
    test_sz = train_sz + TEST_SIZE

    hist = model.fit(X_train, Y_train, validation_split=VALIDATION_SPLIT, batch_size=64, epochs=15, verbose=0) # verbose = 2
    
    Y_hat = model.predict(X_test, verbose=0) # verbose = 2
        
    res += np.sqrt(sklm.mean_squared_error(Y_test, Y_hat))

    #plot_history(hist, "lstm")
    #print_metrics(Y_hat.round().flatten().tolist(), Y_test.tolist())

  print(f"K-validated RMSE: {res / (n_weeks - 4) }")


gru(X, Y)

"""# LSTM"""

def lstm (X, Y): 
  n_weeks = len(X) // WEEK_SIZE
  
  # define model
  model = Sequential()
  model.add(LSTM(50, activation='relu', input_shape=(N_STEPS, N_FEATURES)))
  model.add(Dense(1))
  
  # compile model
  model.compile(optimizer='adam', loss='mse', metrics = ["accuracy"])
  
  # fit model
  res = 0.0

  for i in range(n_weeks - 4):
    X_train = X[(WEEK_SIZE*i):(WEEK_SIZE*(i+3))]
    Y_train = Y[(WEEK_SIZE*i):(WEEK_SIZE*(i+3))]
    X_test = X[(WEEK_SIZE*(i+3)):(WEEK_SIZE*(i+4))]
    Y_test = Y[(WEEK_SIZE*(i+3)):(WEEK_SIZE*(i+4))]
    
    train_sz = TEST_SIZE * i
    test_sz = train_sz + TEST_SIZE

    hist = model.fit(X_train, Y_train, validation_split=VALIDATION_SPLIT, batch_size=64, epochs=15, verbose=0) # verbose = 2
    
    Y_hat = model.predict(X_test, verbose=0) # verbose = 2
        
    res += np.sqrt(sklm.mean_squared_error(Y_test, Y_hat))
    
    #plot_history(hist, "lstm")
    #print_metrics(Y_hat.round().flatten().tolist(), Y_test.tolist())

  print(f"K-validated RMSE: {res / (n_weeks - 4) }")


lstm(X, Y)

"""# RNN"""

def rnn (X, Y): 
  n_weeks = len(X) // WEEK_SIZE
  
  # define model
  model = Sequential()
  model.add(SimpleRNN(50, activation='relu', input_shape=(N_STEPS, N_FEATURES)))
  model.add(Dense(1))
  
  # compile model
  model.compile(optimizer='adam', loss='mse', metrics = ["accuracy"])
  
  # fit model
  res = 0.0

  for i in range(n_weeks - 4):
    X_train = X[(WEEK_SIZE*i):(WEEK_SIZE*(i+3))]
    Y_train = Y[(WEEK_SIZE*i):(WEEK_SIZE*(i+3))]
    X_test = X[(WEEK_SIZE*(i+3)):(WEEK_SIZE*(i+4))]
    Y_test = Y[(WEEK_SIZE*(i+3)):(WEEK_SIZE*(i+4))]
    
    train_sz = TEST_SIZE * i
    test_sz = train_sz + TEST_SIZE

    hist = model.fit(X_train, Y_train, validation_split=VALIDATION_SPLIT, batch_size=64, epochs=15, verbose=0) # verbose = 2
    
    Y_hat = model.predict(X_test, verbose=0) # verbose = 2
        
    res += np.sqrt(sklm.mean_squared_error(Y_test, Y_hat))
    
    #plot_history(hist, "lstm")
    #print_metrics(Y_hat.round().flatten().tolist(), Y_test.tolist())

  print(f"K-validated RMSE: {res / (n_weeks - 4) }")


rnn(X, Y)