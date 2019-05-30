# project-maverick
A partner project with @kurtgalvin to explore deep learning and the possibilities of forecasting the Foreign Exchange (FOREX) market.

Apologies in advance for lack of documentation. This was not documented at the time of creation and it is quite hard to go back and add relevant comments after the fact.

## Installation

Requires Pandas, Numpy, MatplotLib, Keras, Tensorflow for deep learning models and predictions. Oanda V20 REST API to communicate with oanda brokerage. And Twilio API for live hourly updates to cellphone.

## Usage

```For running "finished product"
python money_machine.py
```
Was run continuously throughout trade week and closed during weekends to retrain models.\n
Unfortunately not able to do test runs and set up demo for this beauty as my memory on this project is clouded and there are various accounts needed to be created in order for all components to work together.

Maverick.py used in order to create LSTM models trained on a set of X-train and y-train data derived from existing candle data provided by Oanda V20 API.

Fabricator.py used to combine past candle data together with a prediction made by a model in a chronologically accurate fashion and saves the resulting output as a .txt file.

Simulator.py "plays" the outputted txt file from fabricator and outputs to console what the resulting wins, losses, pip wins, pip losses, trade count, etc. for the given currency pair in the given timeframe.\n
Fabricator and Simulator were basically used as our backtesting unit. 

Refinery.py leftout as it contains secret training techniques used to occasionally output a 54% accurate LSTM model.

## Project Status

This project will likely stay as just an experiment. Deep learning practice and experience will be further developed and improved upon in other projects in the future. 
