# L3_collector

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

- TODO: add in draw.io chart

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

We can design the security master as the following:


## Readings

[1] [tick data](https://firstratedata.com/a/4/tick-data-intro)

[2] [Kaiko](https://www.kaiko.com/collections/order-books/binance)

[3] [Binance Official Guide on Managing Local Orderbook Correctly](https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md#all-market-tickers-stream)



