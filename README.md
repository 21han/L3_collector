# L3_collector

## How to run?

* create a new conda environment
* `pip install -r req.txt` to install required packages in that environment
* Possible commands are:
    * `python -m src.collect --exchange binance --symbol BTCUSDT --data_type book`
    * `python -m src.collect --exchange binance --symbol BTCUSDT --data_type trade`
    * `python -m src.collect --exchange coinbase --symbol BTC-USD --data_type trade`
    * `python -m src.collect --exchange coinbase --symbol BTC-USD --data_type book`

Notice the difference in nomenclature between Coinbase and Binance. For coinbase there is always a `-` between
two asset classes. However, for Binance, `-` shouldn't be present.

## Data Standardization

We have standardized the data schema for Binance and Coinbase.

In this project, we have collected two types of data in real-time via websocket.

* tick trade data
* most recent 5 best prices for bid and ask (this is L2 not L3 data, L3 data in its strict definition contains all trade actions).

### Tick Trade Data Schema

For Binance:

```csv
1621484017026,BTCUSDT,851651093,39307.24000000,0.05838400,1621484017023,False
1621484017077,BTCUSDT,851651094,39307.22000000,0.02632400,1621484017076,False
1621484017286,BTCUSDT,851651095,39307.21000000,0.02892400,1621484017285,True
1621484017363,BTCUSDT,851651096,39305.24000000,0.00220500,1621484017362,False
```

For Coinbase:

```csv
1621483997642,BTC-USD,175006466,39400.15,0.00244823,1621483998165,False
1621483997725,BTC-USD,175006467,39400,0.07,1621483998250,True
1621483997968,BTC-USD,175006468,39396.71,0.00041051,1621483998482,True
1621483997969,BTC-USD,175006469,39396.43,0.01,1621483998482,True
1621483997972,BTC-USD,175006470,39396.43,0.02,1621483998482,True
1621483997972,BTC-USD,175006471,39396.72,0.00059321,1621483998482,Fal
```

The columns are: 

* epoch event time
* symbol 
* trade id
* price
* quantity
* trade time (in trade engine)
* market maker or not (for buyer)

### Book Data Schema (most recent top 5 best bid/ask)

For Binance

```csv
1621485165942,BTCUSDT,B,39441.9,0.128887,1
1621485165942,BTCUSDT,A,39441.91,0.211058,1
1621485165942,BTCUSDT,B,39441.11,0.038316,2
1621485165942,BTCUSDT,A,39442.49,0.029534,2
1621485165942,BTCUSDT,B,39440.93,0.053,3
1621485165942,BTCUSDT,A,39443.06,0.001012,3
1621485165942,BTCUSDT,B,39438.16,0.641013,4
1621485165942,BTCUSDT,A,39443.08,0.068272,4
1621485165942,BTCUSDT,B,39437.41,0.181,5
1621485165942,BTCUSDT,A,39443.27,0.076193,5
```

For Coinbase

```csv
1621484949000,BTC-USD,B,39619.67,0.23774803,1
1621484949000,BTC-USD,A,39619.68,0.07606068,1
1621484949000,BTC-USD,B,39588.9,1.324,2
1621484949000,BTC-USD,A,39628.93,0.19,2
1621484949000,BTC-USD,B,39588.32,0.01,3
1621484949000,BTC-USD,A,39634.45,0.4464,3
1621484949000,BTC-USD,B,39585.16,0.04207745,4
1621484949000,BTC-USD,A,39700.96,0.0127204,4
1621484949000,BTC-USD,B,39583.43,0.1,5
1621484949000,BTC-USD,A,39711.67,0.01,5
```

The columns are:

* epoch time-stamp
* symbol
* side
* price
* quantity
* level

## Background

- Tick data is the highest resolution data.
- sequence of executed trade + bid/ask quote

## Difference between L2 and L3 data

> L3 data (market-by-order) includes ever bid and ask added, updated, or removed from an exchange's order book, non-aggregated.
Normally, order books are aggregated by price level to include all bids or asks placed at a given price level. 
However, it is impossible to determine whether these bids/asks are from many traders or just 1. 
L3 data allows you to see individual bids/asks added to an order book. 
L2 (market-by-price-level) data includes these bids and asks aggregated by price level. 
> Only 3 exchanges in the industry provide non-aggregated, L3 data. All other exchanges provide L2 order boook data. [2]


## Types of Tick Data

There are 4 types of tick data. 

- trade tick data (sequence of executed trade)
- Level 1: Best Bid/Offer or BBO quotes
- Level 2: partial/full order book
- Level 3: execution and amendment actions (e.g. update a limit order or cancel a limit order)

Sometimes full order book is also referred as L3 data 
as long as it is not aggregated at a price level.

## Motivation

- improve backtesting and build simulation using more realistic model execution price based on order book
- better understanding of institutional and retail trade behavior
- arbitrage opportunities
- empower more advanced signal construction/strategies


## Coverage

For this project, we will cover `Binance` and `Coinbase` L3 data collection.

As of today (2021-05-16) only 3 crypto exchanges offer L3 data feed: Coinbase, Bitstamp, and Bitfinex. Therefore, for
`Binance`, we will collect the following data feed:

* trade tick data (sequence of executed trade)
* the most recent orderbook (depth = 5) (extensible to more depth)

We want to mange the local order book. In order to do so, we followed the [3] guide from Binance
official documentation. Conveniently, the described algorithm has already been implemented by
[_process_depth_message](https://python-binance.readthedocs.io/en/latest/_modules/binance/depthcache.html)
method in `DepthCacheManager` class. Therefore, we avoid re-inventing wheel and use this method directly
to log/store the most recent order book (depth = 5).

In addition, according to binance official doc, the websocket (@depth) offers two update speed:

- 1000 ms (1 second)
- 100 ms (0.1 second)

We will default to 1000 ms, but can easily change this by updating the `config.json` file.


## Argument Options

User needs to pass in `exchange`, `symbol`, `data_type`, `data_dir` to the python program.

Possible options are specified below:

```python
parser.add_argument("--exchange", required=True, choices=["coinbase", "binance"])
parser.add_argument("--symbol", required=True, type=str, help="Format: {base asset}{quote asset} (ex. 'BTCUSDT')")
parser.add_argument("--data_dir", type=str, help="local data directory path", default="./data/")
```


## Data Quality Check

The data quality check is a completely independent process from the scraper. The advantage of this set-up is such that 
data quality check has zero interference with the scraper. (i.e. if data quality check process fails, it will not affect
the scraper or data collector in any ways and thereby adding robustness to the pipeline). In addition, we have added
slack integration (and PagerDuty possibly in the future) to further enhance any data quality issues we catch.


## ETL Workflow

![](https://github.com/gzhami/L3_collector/blob/main/resource/sys_design.png)

## Failure Prevention

### Network Level

At network level, we can set up concurrent processes in three geographical region: Asia, Europe and America. 
For example, we run three separate AWS ec2 instances in (1) Dublin, Europe; (2) Ohio, USA; (3) Tokyo, Japan to reduce 
the probability that we experience any service outage in one single geographical region.

The probabilities that all three regions have network failure is marginal. 

To even further enhance failure prevention measure, we can run concurrent process using GCP, Azure along with AWS to prevent 
enterprise level network failure instead of geography specific failure. 

### API Level

At API Level, exchange could change their APIs. However, this is already handled by the code logic by always saving the 
raw message and persist to S3. Therefore, any API changes are completely recoverable and interrupted data can be 
back-filled easily. 

In addition, we can set up proper alerts that subscribe to exchange API updates on Slack; such that, we are aware of any
API change plans ahead of time.

## Security Master

For Coinbase: we can query from [Coinbase Get Products](https://docs.pro.coinbase.com/#get-products) API endpoint to get a list
of available currency pairs for trading. 

For Binance, we can query from [Binance Exchange Info](https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#exchange-information)
API endpoint.

We can then use [tracked-upsert model](https://blog.getdbt.com/track-data-changes-with-dbt-snapshots/)
to track changes

Below are the suggested columns:

* exchange
* datetime
* trading pair
* is_current
* last_modified_datetime
* last_modified_user

In addition, we can set up alerts on newly added trading pairs to Coinbase or Binance (in case there are opportunities).


## Readings

[1] [tick data](https://firstratedata.com/a/4/tick-data-intro)

[2] [Kaiko](https://www.kaiko.com/collections/order-books/binance)

[3] [Binance Official Guide on Managing Local Orderbook Correctly](https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md#all-market-tickers-stream)



