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
    
    # Check for duplicate IDs
    ids = [doc['id'] for doc in docs]
    id_counts = Counter(ids)
    duplicate_ids = {doc_id: count for doc_id, count in id_counts.items() if count > 1}
    
    if duplicate_ids:
        print('DUPLICATE IDs found:')
        for doc_id, count in duplicate_ids.items():
            print(f'  {doc_id}: appears {count} times')
        print()
    else:
        print('No duplicate IDs found.')
        print()
    
    # Check for documents with same date and type
    print('Checking for same date + same type duplicates:')
    date_type_combos = {}
    for doc in docs:
        key = f"{doc['documentType']}_{doc['filingDate']}"
        if key not in date_type_combos:
            date_type_combos[key] = []
        date_type_combos[key].append(doc)
    
    duplicates_found = False
    for key, docs_list in date_type_combos.items():
        if len(docs_list) > 1:
            duplicates_found = True
            doc_type, date = key.split('_')
            print(f'  {doc_type} on {date}: {len(docs_list)} documents')
            for i, doc in enumerate(docs_list):
                print(f'    {i+1}. {doc["title"]} (ID: {doc["id"]})')
            print()
    
    if not duplicates_found:
        print('  No same date+type duplicates found.')
        print()
    
    # Look specifically at 10-Q documents since you mentioned seeing duplicate 10-Qs
    print('All 10-Q documents:')
    tenq_docs = [doc for doc in docs if doc['documentType'] == '10-Q']
    tenq_dates = Counter([doc['filingDate'] for doc in tenq_docs])
    
    for doc in tenq_docs:
        date_count = tenq_dates[doc['filingDate']]
        duplicate_flag = " (DUPLICATE DATE)" if date_count > 1 else ""
        print(f'  {doc["filingDate"]} - {doc["title"]} (ID: {doc["id"]}){duplicate_flag}')
    
    print()
    print('10-Q date frequency:')
    for date, count in tenq_dates.items():
        if count > 1:
            print(f'  {date}: {count} documents (DUPLICATE)')
        else:
            print(f'  {date}: {count} document')

else:
    print(f'Error: {response.status_code} - {response.text}')