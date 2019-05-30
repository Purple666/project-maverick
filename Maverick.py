# Model
import keras
from keras.models import Sequential
from keras.models import load_model
from keras.layers.core import Dense
from keras.layers import LSTM
from keras.layers import SpatialDropout1D
from keras.optimizers import Adam
from keras.callbacks import EarlyStopping
from keras.callbacks import ReduceLROnPlateau
# Data
# from Local_Refinery import Candles
from itertools import product
import pandas as pd
import numpy as np
import os
import time
import requests


class Maverick:
	def __init__(self, instrument, granularity, strategy='alpha'):
		self._model = None
		self._directory = "strategies/"+strategy+"/"+instrument+"/"+granularity+"/models"
		self._callbacks = [EarlyStopping(monitor='val_acc', patience=10),
					   ReduceLROnPlateau(monitor='val_acc', factor=0.90, patience=1, verbose=0, min_lr=0.0001)]

	@property
	def model(self):
		if self._model != None:
			return self._model
		else:
			raise ValueError('No model available in state')

	@model.setter
	def model(self, value):
		directory = self._directory+value
		if os.path.exists(directory):
			self._model = load_model(directory)
		else:
			raise ValueError('Model filepath does not exist')

	@property
	def history(self):
		return self._history.history

	def LSTM(self, x_train, y_train, batch_size=128, epochs=1000):
		self._x_train = x_train
		self._model = Sequential()
		self._model.add(LSTM(32, return_sequences=True, input_shape=(x_train.shape[1], x_train.shape[2])))
		self._model.add(SpatialDropout1D(0.6))
		self._model.add(LSTM(16, return_sequences=True))
		self._model.add(SpatialDropout1D(0.6))
		self._model.add(LSTM(8, return_sequences=True))
		self._model.add(SpatialDropout1D(0.6))
		self._model.add(LSTM(4, return_sequences=False))
		self._model.add(Dense(y_train.shape[1], activation="softmax"))
		self._model.compile(loss='binary_crossentropy', optimizer=Adam(lr=0.001), metrics=['accuracy'])
		self._history = self._model.fit(x_train, y_train, batch_size=batch_size, epochs=epochs, validation_split=0.4, verbose=0, callbacks=self._callbacks)
		print('Time Series:', x_train.shape[1])
		print('-------------------------------------------------------------------')

	def save(self, look_forward):
		model = self.model
		directory = self._directory+"/test/"+str(self._x_train.shape[1])+"/"
		if not os.path.exists(directory):
			os.makedirs(directory)
		model.save(directory+str(look_forward)+'_LSTM.h5')
		print('\nModel Saved')


def run(save=True):
	for pair, back, forward in product(instrument, time_series, look_forward):
		data = Candles(x, granularity, candle_count=10000, provider='fxcm')
		x_train = data.x_train(back, forward)
		y_train = data.y_train(forward)[-len(x_train):]
		model = Maverick(x, granularity, strategy='alpha')
		model.LSTM(x_train, y_train)
		if save:
				model.save(forward)

if __name__ == '__main__':
	instrument = ["AUD_CAD"]
	granularity = 'H1'
	time_series = [96, 108, 120, 132, 144, 156, 168]
	look_forward = [12, 14, 16, 18, 20, 22, 24, 26, 28, 30]
	run()