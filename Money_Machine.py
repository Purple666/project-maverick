from Money_Machine_Candle_Data import Candle_Data
from multiprocessing import Process, Pipe
from twilio.rest import Client
import oandapyV20
import oandapyV20.endpoints.positions as positions
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.accounts as accounts
from oandapyV20.exceptions import V20Error
from keras.models import load_model
import sqlite3
import json
import configparser
import datetime
import time


def send_text(body):
	config = configparser.ConfigParser()
	config.read("../Config/twilio.ini")
	account_sid = config.get("twilio","account_sid")
	auth_token = config.get("twilio","auth_token")
	from_ = config.get("twilio","from_")
	to = config.get("twilio","to")
	client = Client(account_sid, auth_token)
	client.messages.create(body=body+"\nTime: "+datetime.datetime.now().strftime("%H:%M"), from_=from_, to=to)

def log_data():
	conn = sqlite3.connect('Money_Machine.db')
	c = conn.cursor()
	t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	acc = Oanda().account_summary()
	c.execute("INSERT INTO account VALUES (?, ?, ?, ?)", (acc['id'], t, float(acc['NAV']), acc['openTradeCount']))
	conn.commit()
	conn.close()

class Oanda:
	def __init__(self):
		config = configparser.ConfigParser()
		config.read('../Config/oanda.ini')
		self._accountID = config['oanda']['account_id']
		access_token = config['oanda']['api_key']
		self._client = oandapyV20.API(access_token, environment='live')

	def try_request(func): # attempt to connect back with Oanda 10 times, after that send text and break
		def try_request_wrapper(*args, **kwargs):
			for i in range(9):
				try:
					return func(*args, **kwargs)
				except V20Error:
					print('ConnectionError:',i+1)
					time.sleep(2)
				except Exception as e:
					print(e)
					time.sleep(2)
			send_text("ConnectionError time out")
		return try_request_wrapper

	@try_request
	def account_summary(self):
		r = accounts.AccountSummary(self._accountID)
		self._client.request(r)
		return r.response['account']

	def _account_update(self):
		summary = self.account_summary()
		opened = '\nOpened: '+str(Strategy.g_open)
		Strategy.g_open = 0
		closed = '\nClosed: '+str(Strategy.g_close)
		Strategy.g_close = 0
		open_pos = '\nOpen_Pos: '+str(summary['openPositionCount'])
		open_pl_n = int(float(summary['unrealizedPL'])*100)/100
		open_pl = '\nOpen_PL: '+str(open_pl_n)
		balance_n = int(float(summary['balance'])*100)/100
		balance = '\nBalance: '+str(balance_n)
		total = '\nTotal: $'+str(int(float(summary['NAV'])*100)/100)
		print(opened, closed, total)
		return opened+closed+total+open_pos

	@try_request
	def get_open_positions(self):
		open_positions = positions.OpenPositions(accountID=self._accountID)
		x = self._client.request(open_positions)['positions']
		dick = {}
		for i in x:
			dick[i['instrument']] = [int(i['short']['units']), int(i['long']['units'])]
			dick[i['instrument']] = dick[i['instrument']][0]+dick[i['instrument']][1]
		return dick

	@try_request
	def close_position(self, instrument, units=0):
		units = self.get_open_positions()[instrument] if units == 0 else units
		data = {"shortUnits": "ALL"} if units < 0 else {"longUnits": "ALL"}
		self._client.request(positions.PositionClose(accountID=self._accountID, instrument=instrument, data=data))

	def convert_to_cad(self, pair):
		cad_pairs = ["AUD_CAD", "CAD_CHF", "CAD_JPY", "EUR_CAD", "GBP_CAD", "NZD_CAD", "USD_CAD"]
		if "CAD" not in pair:
			for x in cad_pairs:
				if pair[4:7] in x:
					pair = x
		return 1/Candle_Data.current_close(pair, "H1") if pair[0:3] == "CAD" else 1

	@try_request
	def create_market_order(self, instrument, units, stop_loss):
		stop_loss = round(stop_loss,3) if "JPY" in instrument else stop_loss
		data = {
			"order": {
				"units": str(units),
				"instrument": instrument,
				"timeInForce": "FOK",
				"type": "MARKET",
				"positionFill": "DEFAULT",
				"stopLossOnFill": {
					"timeInForce": "GTC",
					"price": str(stop_loss)
				}
			}
		}
		open = orders.OrderCreate(accountID=self._accountID, data=data)
		self._client.request(open)


class Strategy(Oanda):
	g_open = 0
	g_close = 0
	def __init__(self, instrument, granularity, req):
		Oanda.__init__(self)
		self._instrument = instrument
		self._granularity = granularity
		self._super_req = req
		self._loss_percent = 0.0075 # 0.75%
		self._live_units = 0

	def _set_live_units(self):
		try:
			self._live_units = self.get_open_positions()[self._instrument]
		except KeyError:
			self._live_units = 0

	def _live_units_check(self, prediction):
		if self._live_units < 0 and prediction[0] == max(prediction):
			pass
		elif self._live_units > 0 and prediction[1] == max(prediction):
			pass
		else:
			if self._live_units != 0: 
				self.close_position(self._instrument, units=self._live_units)
				Strategy.g_close += 1
			self.start(prediction)

	def _stop_loss(self, sell=False, buy=False):
		series = Candle_Data.core_stop_loss(self._instrument, self._granularity)
		bb = (series['upper_band'] - series['lower_band'])*3
		return int((series['close'] - bb)*10000)/10000 if buy else int((series['close'] + bb)*10000)/10000

	def _position_units(self, stop_loss):
		current = Candle_Data.current_close(self._instrument, self._granularity)
		loss = float(self.account_summary()['NAV'])*self._loss_percent
		stop_loss = current - stop_loss
		return int(loss/(stop_loss*self.convert_to_cad(self._instrument)))

	def start(self, prediction):
		self._set_live_units()
		if max(prediction) < self._super_req:
			if self._live_units != 0: 
				self.close_position(self._instrument, units=self._live_units)
				Strategy.g_close += 1
		elif self._live_units != 0:
			self._live_units_check(prediction)
		elif self._live_units == 0 and max(prediction) > self._super_req:
			Strategy.g_open += 1
			stop = self._stop_loss(sell=True) if prediction[0] == max(prediction) else self._stop_loss(buy=True) # Sell or Buy
			self.create_market_order(self._instrument, self._position_units(stop), stop)

	'''
	def _good_prediction(self, prediction):
		units = self._live_units
		if units == 0 and max(prediction) > self._super_req:
			Strategy.g_open += 1
			stop = self._stop_loss(sell=True) if prediction[0] == max(prediction) else self._stop_loss(buy=True) # Sell or Buy
			self.create_market_order(self._instrument, self._position_units(stop), stop)
		elif units < 0 and max(prediction) == prediction[1] or units > 0 and max(prediction) == prediction[0]: # We need to reverse position
			Strategy.g_close += 1
			self.close_position(self._instrument, units=self._live_units)

	def start(self, prediction):
		# Thread to update live positions HERE
		self._set_live_units() # replace
		if max(prediction) > self._super_req:
			self._good_prediction(prediction)
		elif self._live_units != 0:
			Strategy.g_close += 1
			self.close_position(self._instrument, units=self._live_units)
	'''	


class Main(Oanda):
	def __init__(self):
		Oanda.__init__(self)
		self.dick = {}
		with open("Maverick_Settings.txt") as instruments:
			file = json.load(instruments)
			pairs = file
		print("\nLoading Models...", end="\r")
		self.model_dick = {i: load_model('Models/'+str(pairs[i]['data_split'])+'/'+pairs[i]['granularity']+'_'+str(pairs[i]['look_forward'])+'_'+i+'_LSTM.h5') for i in pairs}
		self.pairs = pairs
		print("Project Maverick")
		print("Now Entering The Danger Zone")

	def __market_hours(self): # Start trading sunday at 14:58 and stop on friday at 14:00
		the_time = datetime.datetime.now()
		if the_time.isoweekday() == 7 and the_time.hour < 14: # Sunday
			time.sleep(120)
			return False
		elif the_time.isoweekday() == 5 and the_time.hour >= 13: # Friday
			send_text("Trade Week Over")
			exit()
		elif the_time.minute >= 59:
			return True
		else:
			return False

	def _prediction(self, instrument, model):
		data = self.dick[instrument].core_strategy(self.pairs[instrument]['time_series'])[-1]
		data = data.reshape(1,data.shape[0],data.shape[1])
		prediction = model.predict(data)
		return [int((i*100)+0.5) for i in prediction[0]]

	def start(self):
		trade_dict = {i: Strategy(i, self.pairs[i]['granularity'], self.pairs[i]['percent']) for i in self.pairs}
		while True:
			if self.__market_hours():
				print("\nBoarding F-14 Tomcat", end="")
				self.dick = {i: Candle_Data(i, self.pairs[i]['granularity'], 319) for i in self.pairs}
				for i in self.pairs:
					trade_dict[i].start(self._prediction(i, self.model_dick[i]))
					self.dick.pop(i, None)
				send_text(self._account_update())
				log_data()
				print("Mission Complete")
				time.sleep(120)
			time.sleep(1)


if __name__ == '__main__':
	try:
		x = Main()
		x.start()
	except Exception as ex:
		print('ERROR:',ex)
		send_text('ERROR:'+str(ex))
		time.sleep(14400)