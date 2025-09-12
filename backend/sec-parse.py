import requests
from bs4 import BeautifulSoup

url = "https://www.sec.gov/files/company_tickers.json"
headers = {"User-Agent": "patbirnmail@gmail.com"}
data = requests.get(url, headers=headers).json()

def get_cik_from_ticker(ticker):
    ticker = ticker.upper()
    for entry in data.values():
        if entry["ticker"] == ticker:
            return str(entry["cik_str"]).zfill(10)  # zero-pad to 10 digits
    return None

def get_latest_filings(cik):
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

    
def get_filing_url(cik):
    forms = get_latest_filings(cik)["filings"]["recent"]["form"]
    accessions = get_latest_filings(cik)["filings"]["recent"]["accessionNumber"]
    docs = get_latest_filings(cik)["filings"]["recent"]["primaryDocument"]
    for form, acc, doc in zip(forms, accessions, docs):
        if form == "10-K":
            acc_no_dash = acc.replace("-", "")
            filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_dash}/{doc}"
            print(filing_url)
            return filing_url
    return None

def get_filing_content(filing_url):
    response = requests.get(filing_url, headers=headers)
    response.raise_for_status()
    
    # Parse HTML and extract text content
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Get text content
    text = soup.get_text()
    
    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = ' '.join(chunk for chunk in chunks if chunk)
    
    return text

# Test with AAPL
ticker = "AAPL"
cik = get_cik_from_ticker(ticker)
if cik:
    filing_url = get_filing_url(cik)
    if filing_url:
        content = get_filing_content(filing_url)
        # print(f"Latest 10-K filing for {ticker}:")
        # print(f"URL: {filing_url}")
        # print(f"Content length: {len(content)} characters")
        print(f"Word count: {len(content.split())} words")
        # print(f"First 500 characters: {content[:1000000]}...")
    else:
        print(f"No 10-K filing found for {ticker}")
else:
    print(f"Could not find CIK for {ticker}")