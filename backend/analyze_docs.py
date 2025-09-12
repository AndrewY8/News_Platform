#!/usr/bin/env python3
import requests
import json
from collections import Counter

# Get documents from API
response = requests.post("http://localhost:8004/api/sec/search", 
                        json={"query": "AAPL", "limit": 50},
                        headers={"Content-Type": "application/json"})

if response.status_code == 200:
    data = response.json()
    docs = data['documents']
    
    print(f'Total documents: {len(docs)}')
    print()
    
    # Analyze document types
    types = {}
    for doc in docs:
        doc_type = doc['documentType']
        date = doc['filingDate']
        title = doc['title']
        doc_id = doc['id']
        
        if doc_type not in types:
            types[doc_type] = []
        types[doc_type].append((date, title, doc_id))
    
    for doc_type, docs_list in types.items():
        print(f'{doc_type}: {len(docs_list)} documents')
        
        # Check for duplicates by date
        dates = [d[0] for d in docs_list]
        date_counts = Counter(dates)
        duplicates = {date: count for date, count in date_counts.items() if count > 1}
        
        if duplicates:
            print(f'  WARNING: Duplicate dates found!')
            for date, count in duplicates.items():
                print(f'    {date}: {count} documents')
                # Show which documents have the same date
                same_date_docs = [doc for doc in docs_list if doc[0] == date]
                for i, (d, t, doc_id) in enumerate(same_date_docs):
                    print(f'      {i+1}. {t} (ID: {doc_id})')
        
        # Show a few examples
        print(f'  Examples:')
        for i, (date, title, doc_id) in enumerate(docs_list[:3]):
            print(f'    {date} - {title}')
        print()
    
    # Specifically look for 10-K documents
    print('All 10-K documents found:')
    count_10k = 0
    for doc in docs:
        if doc['documentType'] == '10-K':
            count_10k += 1
            print(f'  {doc["filingDate"]} - {doc["title"]} (ID: {doc["id"]})')
    
    if count_10k == 0:
        print('  No 10-K documents found!')
        print('  This might indicate they are not in the most recent filings.')
    
else:
    print(f'Error: {response.status_code} - {response.text}')