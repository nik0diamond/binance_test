from binance.client import Client
from time import sleep
import prometheus_client as prom
import logging

def get_some_dicts_by_bigger_value(dict_list, parameter, count):
    return sorted(dict_list, key = lambda i: float(i[parameter]), reverse=True)[:count]


def get_sum_value_first_bids_then_asks(bids, asks, num_of_things):
    num_of_asks = num_of_things - len(bids)
    sum_of_value = 0
    for bid in bids[:num_of_things]:
        sum_of_value = sum_of_value + int(float(bid[1]))  #hereinafter I use int(), couse i didn't met any real float number in output
    if num_of_asks > 0:
        for ask in asks[:num_of_asks]:
            sum_of_value = sum_of_value + int(float(ask[1]))
    return sum_of_value


#I'm didn't understand if you asks ise firs 200 of each of bids or asks, or previous bids and then asks if len(bids<200)
#and resolve both variants
def get_sum_value_first_bids_and_asks(bids, asks, num_of_things):
    sum_of_value = 0
    for bid in bids[:num_of_things]:
        sum_of_value = sum_of_value + int(float(bid[1]))
    for ask in asks[:num_of_things]:
        sum_of_value = sum_of_value + int(float(ask[1]))
    return sum_of_value


def count_delta_by_deals(bids, asks):
    # in one source I found the absolute delta is difference between ask and bids deals (not volume) and realise it simple function
    # but in all my requests numbers of asks and bids always equals
    delta_by_deals = len(asks) - len(bids)
    return delta_by_deals


def calculate_delta_by_volumes(bids, asks):
    sum_of_ask_deals = 0
    for i in asks:
        sum_of_ask_deals = sum_of_ask_deals + int(float(i[1]))

    sum_of_bids_deals = 0
    for i in bids:
        sum_of_bids_deals = sum_of_bids_deals + int(float(i[1]))

    return sum_of_ask_deals - sum_of_bids_deals


def price_spread(bids, asks):
    ask_price, ask_value = map(list, zip(*asks))
    bid_price, bid_value = map(list, zip(*bids))
    ask_price = [float(i) for i in ask_price]
    bid_price = [float(i) for i in bid_price]
    return round(max(ask_price) - min(bid_price), 7)


def btc_tasks(btc_tickers):
    for i in get_some_dicts_by_bigger_value(btc_tickers, parameter='volume', count=5):
        symbol = i['symbol']
        volume = i['volume']
        logging.info("The volume of " + symbol + " is " + str(float(volume)))
        order_book = client.get_order_book(symbol=symbol)
        bids_list = order_book['bids']
        asks_list = order_book['asks']
        logging.info("Notional volume of top 200 bids " + str(get_sum_value_first_bids_then_asks(bids_list,
                                                                                          asks_list,
                                                                                          num_of_things=200)) + \
              " (asks including if we have no enough of bids)")

        logging.info("Notional volume of top 200 bids and top 200 asks " + \
              str(get_sum_value_first_bids_then_asks(bids_list,
                                                     asks_list,
                                                     num_of_things=200)))


def usd_tasks(usd_tickers):
    results = []
    for i in get_some_dicts_by_bigger_value(usd_tickers, parameter='volume', count=5):
        symbol = i['symbol']
        count = i['count']

        logging.info("The number of traders for " + symbol + " is " + str(count))
        order_book = client.get_order_book(symbol=symbol)
        bids_list = order_book['bids']
        asks_list = order_book['asks']
        spread = price_spread(bids_list, asks_list)
        delta_by_deals = count_delta_by_deals(bids_list, asks_list)
        delta_by_volume_ = calculate_delta_by_volumes(bids_list, asks_list)
        logging.info("The price spread for " + symbol + " is " + str(spread))
        logging.info("The delta by orders for " + i['symbol'] + " is " + str(delta_by_deals))
        logging.info("The delta by volume of deals for " + symbol + " is " + str(delta_by_volume_))
        results.append([symbol, spread, delta_by_deals, delta_by_volume_])
    return results


if __name__ == "__main__":
    logging.basicConfig(filename='output.log', format='%(asctime)s | %(levelname)s: %(message)s', level=logging.INFO)
    client = Client()
    tickers = client.get_ticker()

    # The next code is answer Q1 in task, executing once.
    btc_tickers = []
    for ticker in tickers:
        if "BTC" in ticker['symbol']:
            btc_tickers.append(ticker)

    btc_tasks(btc_tickers)

    # The next code in loop, for metrics. This code also include answers for Q2
    price_spread_ = prom.Gauge('price_spread', 'Price spread of symbol', ['symbol'])
    delta_by_volume_ = prom.Gauge('delta_by_volume', 'Delta by volume for symbol ', ['symbol'])
    prom.start_http_server(8080)

    while True:
        tickers = client.get_ticker()
        usd_tickers = []
        for ticker in tickers:
            if "USDT" in ticker['symbol']:
                usd_tickers.append(ticker)

        metrics = usd_tasks(usd_tickers)

        for metric in metrics:
            symbol = metric[0]
            spread = metric[1]
            delta_volume = metric[3]

            price_spread_.labels(symbol=symbol).set(spread)
            delta_by_volume_.labels(symbol=symbol).set(delta_volume)

        sleep(10)
