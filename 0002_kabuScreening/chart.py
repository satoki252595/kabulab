import yfinance as yf
import mplfinance as mpf

# Define the stock symbol and time range
symbol = "AAPL"
start_date = "2022-01-01"
end_date = "2022-12-31"


def create_chart(symbol, start_date, end_date):
    # Fetch the stock data
    stock_data = yf.download(symbol, start=start_date, end=end_date)

    # Create a candlestick chart
    mpf.plot(stock_data, type='candle', volume=True,
             ylabel='Price', title=f"Stock Chart for {symbol}")


if __name__ == "__main__":
    create_chart(symbol, start_date, end_date)
