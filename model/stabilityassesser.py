import pandas as pd
from pandas import concat
from sklearn.metrics import mean_absolute_error
from numpy import asarray
from sklearn.ensemble import RandomForestRegressor
from matplotlib import pyplot

class StabilityAssesser(object):

    def compute_aggregate(self, data : dict, source_metric : str, destination_metric : str, window : int):
        data_aggregate = dict()
        data_aggregate["time"] = list()
        data_aggregate[destination_metric] = list()
        current_counter = 0
        current_begin_value = data[source_metric][0] if data.get(source_metric, False) else 0
        current_begin_epoch = data['time'][0] if data.get('time',False) else 0
        while True:
            current_counter+=window
            if current_counter >= len(data["time"]):
                break
            delta_epoch = data['time'][current_counter].timestamp() - current_begin_epoch.timestamp()
            delta_value = data[source_metric][current_counter] - current_begin_value
            data_aggregate['time'].append(data['time'][current_counter])
            data_aggregate[destination_metric].append(round((delta_value/delta_epoch)/(10**9),3)) # timestamp are in ns
            current_begin_epoch = data['time'][current_counter]
            current_begin_value = data[source_metric][current_counter]
        return pd.DataFrame(data_aggregate)

    def split(self, data : pd.DataFrame):
        return data[:, :-1], data[:, -1]

    def train_test_split(self, data, n_test):
        return data[:-n_test, :], data[-n_test:, :]

    def series_to_supervised(self, data, n_in=1, n_out=1, dropnan=True):
        n_vars = 1 if type(data) is list else data.shape[1]
        df = pd.DataFrame(data)
        cols = list()
        # input sequence (t-n, ... t-1)
        for i in range(n_in, 0, -1):
            cols.append(df.shift(i))
        # forecast sequence (t, t+1, ... t+n)
        for i in range(0, n_out):
            cols.append(df.shift(-i))
        # put it all together
        agg = concat(cols, axis=1)
        # drop rows with NaN values
        if dropnan:
            agg.dropna(inplace=True)
        return agg.values
        
    # walk-forward validation for univariate data
    def walk_forward_validation(self, traindata, n_test):
        predictions = list()
        # split dataset
        train, test = self.train_test_split(traindata, n_test)
        # seed history with training dataset
        history = [x for x in train]
        # step over each time-step in the test set
        for i in range(len(test)):
            # split test row into input and output columns
            testX, testY = test[i, :-1], test[i, -1]
            # fit model on history and make a prediction
            yhat = self.random_forest_forecast(history, testX)
            # store forecast in list of predictions
            predictions.append(yhat)
            # add actual observation to history for the next loop
            history.append(test[i])
            # summarize progress
            print('>expected=%.1f, predicted=%.1f' % (testY, yhat))
        # estimate prediction error
        error = mean_absolute_error(test[:, -1], predictions)
        return error, test[:, -1], predictions

    # fit an random forest model
    def build_and_fit_model(self, train):
        train = asarray(train)
        # split into input and output columns
        trainX, trainy = self.split(train)
        # fit model
        model = RandomForestRegressor(n_estimators=400)
        model.fit(trainX, trainy)
        return model

    # make a one-step prediction
    def one_step_prediction(self, model, testX):
        yhat = model.predict([testX])
        return yhat[0]

    # fit an random forest model and make a one step prediction
    def random_forest_forecast(self, train, testX):
        return self.one_step_prediction(self.build_and_fit_model(train), testX)

    # fit an random forest model and make a multi step prediction
    def try_mode(self, traindata, n_test):
        predictions = list()
        # split dataset
        train, test = self.train_test_split(traindata, n_test)
        model = self.build_and_fit_model(train)
        # step over each time-step in the test set
        for i in range(len(test)):
            # split test row into input and output columns
            testX, testY = test[i, :-1], test[i, -1]
            # fit model on history and make a prediction
            yhat = self.one_step_prediction(model, testX)
            # store forecast in list of predictions
            predictions.append(yhat)
            # summarize progress
            print('>expected=%.1f, predicted=%.1f' % (testY, yhat))
        # estimate prediction error
        error = mean_absolute_error(test[:, -1], predictions)
        return error, test[:, -1], predictions

    def assess(self, traindata : dict, targetdata : dict, metric : str):

        # traindata.append(targetdata["time"])
        data = traindata[metric] + targetdata[metric]
        traindata = self.series_to_supervised(data, n_in=4)

        # evaluate
        #mae, y, yhat = self.walk_forward_validation(traindata, n_test=len(targetdata["time"]))
        mae, y, yhat = self.try_mode(traindata, n_test=len(targetdata["time"]))
        print('MAE: %.3f' % mae)
        # plot expected vs predicted
        # pyplot.plot(y, label='Expected')
        # pyplot.plot(yhat, label='Predicted')
        # pyplot.legend()
        # pyplot.show()

        return True # TODO MAE < THRESHOLD