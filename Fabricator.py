from multiprocessing import Process, Pipe
from itertools import product
from Maverick import Maverick
import json
import time
import os
import pickle
import numpy as np


class Yalla:
	def __init__(self, start, worker, model_cycle=120): # start - number of candles from the end
		self.start = -start
		self.model_cycle = model_cycle
		self.instrument = worker.instrument
		self.granularity = worker.granularity
		self.look_forward = worker.look_forward
		self.x_train_dir = worker.directory+"/data/X_train/"+str(worker.time_series)+"/"+str(worker.look_forward)+".pkl"
		self.y_train_dir = worker.directory+"/data/y_train/"+str(worker.look_forward)+".pkl"
		self.close_dir = worker.directory+"/data/close.pkl"

	def x_y_train(self):
		with open(self.x_train_dir, 'rb') as file:
			x_train = pickle.load(file)
		with open(self.y_train_dir, 'rb') as file:
			y_train = pickle.load(file)
		return x_train, y_train[-len(x_train):]

	def close_data(self):
		with open(self.close_dir, 'rb') as file:
			close = pickle.load(file)
		close = close[:-self.look_forward]
		return close[-len(self.x_train):]

	def get_slice(self, pipe, n):
		hold_slice = []
		maverick = Maverick(self.instrument, self.granularity)
		maverick.LSTM(self.x_train[n-5000:n], self.y_train[n-5000:n])
		for i in range(self.model_cycle):
			prediction = maverick.model.predict(self.x_train[n].reshape(1, self.x_train.shape[1], self.x_train.shape[2]))
			prediction = [int(i*100+0.5) for i in prediction[-1]]
			hold_slice.append({"prediction": prediction, "close": self.close[n], "val_acc": maverick.history['val_acc'][-1]})
			n += 1
		pipe.send((hold_slice, n)) 

	def __iter__(self):
		self.candle = self.start
		self.x_train, self.y_train = self.x_y_train()
		self.close = self.close_data().tolist()
		return self

	def __next__(self):
		if self.candle < 0: 
			A, B = Pipe()
			P = Process(target=self.get_slice, args=(B,self.candle), daemon=True)
			P.start()
			P.join()
			result, self.candle = A.recv()
			return result
		else:
			raise StopIteration


class Worker:
	def __init__(self, instrument, granularity, time_series, look_forward):
		self.instrument = instrument
		self.granularity = granularity
		self.time_series = time_series
		self.look_forward = look_forward
		self.directory = "strategies/alpha/"+instrument+"/"+granularity+"/"
		self.dump_dir = self.directory+"predictions/"+str(time_series)+'/'
		self.yalla = Yalla(4440, self)

	def __call__(self):
		result = []
		for i in self.yalla:
			for x in i:
				result.append(x)
		self.send(result)
		print(f'Done: {self.time_series} {self.look_forward}')

	def send(self, result):
		if not os.path.exists(self.dump_dir):
			os.makedirs(self.dump_dir)
		with open(self.dump_dir+str(self.look_forward)+'.txt', 'w') as file:
			json.dump(result, file)


def fabricate(pair, gran, back, forward):
	worker = Worker(pair, gran, back, forward)
	worker()


if __name__ == '__main__':
	instruments = ["GBP_JPY"]
	granularities = ["H1"]
	time_series = [108, 120, 132, 144, 156, 168, 180, 192]
	look_forward = [12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48, 50]
	for pair, gran, back, forward in product(instruments, granularities, time_series, look_forward):
		fabricate(pair, gran, back, forward)

	# processes = dict.fromkeys(range(int(os.cpu_count()/2)), Process())
	# print(processes)
	# for pair, gran, back, forward in product(instruments, granularities, time_series, look_forward):
	# 	while True:
	# 		empty = [i for i in processes if not processes[i].is_alive()]
	# 		if empty != []:
	# 			worker = Worker(pair, gran, back, forward)
	# 			P = Process(target=worker.run)
	# 			processes[empty[0]] = P
	# 			P.start()
	# 			break
	# for key in processes:
	# 	processes[key].join()