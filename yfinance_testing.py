import yfinance as yf

# Create a Ticker object for the company
ticker = yf.Ticker("AAPL")

# Access the info attribute, which returns a dictionary
company_info = ticker.info

# Print the entire dictionary
import pprint
pprint.pprint(company_info)
