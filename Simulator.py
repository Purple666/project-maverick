from itertools import product
import matplotlib.pyplot as plt
from statistics import mean
import json
import time


class Yalla:
	def __init__(self, instruments, time_series=False, look_forward=False, percent=51):
		self._instruments = instruments
		self._time_series = [60, 72, 84, 96, 108, 120, 132, 144, 156, 168, 180, 192] if not time_series else time_series
		self._look_forward = [12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48, 50] if not look_forward else look_forward
		self._percent = percent
		self._result_dick = {a: {b: {} for b in self._time_series} for a in self._instruments}

	def __call__(self):
		for pair, ts, forward in product(self._instruments, self._time_series, self._look_forward):
			directory = f"strategies/alpha/{pair}/H1/predictions/{ts}/"
			with open(directory+str(forward)+'.txt', 'r') as file:
				file = json.load(file)
			precock = Precocktion(pair, self._percent)
			for f in file:
				precock(f['prediction'], f['close'])
			self._result_dick[pair][ts][forward] = precock.get_trades() # ['pips']

	def pip_results(self, bar_width, chart=False):
		count = (len(self._time_series)/2*-bar_width)+bar_width/2
		pip_dick = {a: [] for a in self._time_series}
		for pair, ts in product(self._instruments, self._time_series):
			for i in self._result_dick[pair][ts]:
				pip_dick[ts].append(self._result_dick[pair][ts][i]['pips'])
			plt.bar([i+count for i in self._look_forward], pip_dick[ts], bar_width, label=ts)
			count += bar_width
			print(f'{ts} -- Mean: {mean(pip_dick[ts])}  ', f'Sum: {sum(pip_dick[ts])}')
		if chart:
			plt.xticks(self._look_forward)
			plt.legend(loc='upper left')
			plt.ylabel('pips')
			plt.tight_layout()
			plt.show()

	def ratio_result(self, bar_width, chart=False):
		plt.figure(num='AI prediction')
		count = (len(self._time_series)/2*-bar_width)+bar_width/2
		pip_dick = {a: [] for a in self._time_series}
		for pair, ts in product(self._instruments, self._time_series):
			# plt.subplot(2,1,1)
			for i in self._result_dick[pair][ts]:
				pips = self._result_dick[pair][ts][i]['pips']
				ratio = pips/self._result_dick[pair][ts][i]['count']
				pip_dick[ts].append(ratio)
			plt.bar([i+count for i in self._look_forward], pip_dick[ts], bar_width, label=ts)
			count += bar_width
			print(f'{ts} -- Mean: {mean(pip_dick[ts])}')
		if chart:
			# plt.subplot(2,1,1)
			self._show_chart(plt)

	def history_result(self, bar_width, chart=False): # NOT READY
		count = (len(self._time_series)/2*-bar_width)+bar_width/2
		pip_dick = {a: [] for a in self._time_series}
		for pair, ts in product(self._instruments, self._time_series):
			for i in self._result_dick[pair][ts]:
				pips = self._result_dick[pair][ts][i]['pips']
				ratio = pips/self._result_dick[pair][ts][i]['count']
				pip_dick[ts].append(ratio)
			plt.bar([i+count for i in self._look_forward], pip_dick[ts], bar_width, label=ts)
			count += bar_width
			print(f'{ts} -- Mean: {mean(pip_dick[ts])}')
		if chart:
			plt.xticks(self._look_forward)
			plt.legend(loc='upper left')
			plt.ylabel('pips')
			plt.tight_layout()
			plt.show()

	def _show_chart(self, plt):
		plt.xticks(self._look_forward)
		plt.legend(loc='upper left')
		plt.ylabel('pips')
		plt.tight_layout()
		plt.show()
			

class Precocktion:
	def __init__(self, instrument, requirement):
		self._instrument = instrument
		self._requirement = requirement
		self._pos = [] # position
		self._trades = dict.fromkeys(['count', 'win', 'loss', 'pips', 'pip_win', 'pip_loss', 'max_win', 'max_loss', 'avg_win', 'avg_loss'], 0)
		self._trades['history'] = []

	def __call__(self, prediction, close):
		self._prediction = prediction
		self._close = close
		if max(self._prediction) > self._requirement:
			self._open_position()
		else:
			self._close_position()

	def _open_position(self):
		if self._pos == []:
			self._pos = [-1, self._close] if self._prediction[0] > 50 else [1, self._close]
		elif self._pos[0] == -1 and self._prediction[0] < 50:
			self._close_position()
			self._open_position()	
		elif self._pos[0] == 1 and self._prediction[1] < 50:
			self._close_position()
			self._open_position()

	def _close_position(self):
		try:
			pips = self._pos[1] - self._close if self._pos[0] == -1 else self._close - self._pos[1]
			pips = round(pips*100) if "JPY" in self._instrument else round(pips*10000)
			self._trades['pips'] += pips
			if pips > 0:
				self._trades['win'] += 1
				self._trades['pip_win'] += pips
			else:
				self._trades['loss'] += 1
				self._trades['pip_loss'] += pips
			self._trades['history'].append(pips)
			self._trades['count'] += 1
			self._pos = []
		except IndexError:
			pass

	def get_trades(self):
		if self._trades['win'] != 0:
			self._trades['avg_win'] = round(self._trades['pip_win']/self._trades['win'], 2) 
		if self._trades['loss'] != 0:
			self._trades['avg_loss'] = round(self._trades['pip_loss']/self._trades['loss'], 2)
		self._trades['loss'] = self._trades['loss'] if self._trades['loss'] != 0 else 1
		self._trades['max_win'] = max(self._trades['history']) if self._trades['history'] != [] else 0
		self._trades['max_loss'] = min(self._trades['history']) if self._trades['history'] != [] else 0
		return self._trades

if __name__ == '__main__':
	look = list(range(12, 51, 2))
	look = [12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48, 50]
	# time_series = [60, 72, 84, 96, 108]
	time_series = [132]
	look = [12]
	x = Yalla(instruments=["AUD_CAD"], time_series=time_series, look_forward=look, percent=51)
	x()
	x.pip_results(0.2, chart=False)
	# x.ratio_result(0.2, chart=True)