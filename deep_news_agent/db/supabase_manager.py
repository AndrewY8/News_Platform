"""
This is the supbase manager that Ive created to manage the database for now 
since I'm not entirely sure if supabase_manager.py is integrated with anything.

"""

import os
import json
import numpy as np
from supabase import create_client, Client
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from .company_extractor import CompanyExtractor

class EmbeddingModel:
    def __init__(self):
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    
    def encode(self, query : str):
        return self.model.encode(query)

class dbManager:   
    def __init__(self, url, key, model, companyExtractor : CompanyExtractor):
        self.supabase : Client = create_client(url, key)
        self.model : EmbeddingModel = model
        self.extractor = companyExtractor

    @staticmethod
    def _sanitize(obj):
        """Recursively convert numpy types -> native Python types for JSON serialization."""
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.floating, np.float32, np.float64, np.float16)):
            return float(obj)
        if isinstance(obj, (np.integer, np.int32, np.int64, np.int16, np.int8)):
            return int(obj)
        if isinstance(obj, dict):
            return {k: dbManager._sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list) or isinstance(obj, tuple):
            return [dbManager._sanitize(v) for v in obj]
        return obj
    
    def create_row(self, table : str, data : dict):
        safe_data = self._sanitize(data)
        response = self.supabase.table(table).insert(safe_data).execute()
        return response.data
    
    def read_rows(self, table: str, filters: dict = None):
        query = self.supabase.table(table).select("*")
        if filters:
            for col, val in filters.items():
                query = query.eq(col, val)
        response = query.execute()
        return response.data

    def update_rows(self, table: str, filters: dict, updates: dict):
        query = self.supabase.table(table).update(updates)
        for col, val in filters.items():
            query = query.eq(col, val)
        response = query.execute()
        return response.data

    def delete_rows(self, table: str, filters: dict):
        query = self.supabase.table(table).delete()
        for col, val in filters.items():
            query = query.eq(col, val)
        response = query.execute()
        return response.data
    
    def similarity_search(self, text: str, top_k):
        embedding = self.model.encode(text).tolist()
        response = self.supabase.rpc(
            "match_news",
            {"query_embedding": embedding, "match_count": top_k}
        ).execute()
        return response.data

    def check_article_exists(self, table: str, article_title: str):
        """Check if an article with the given title already exists"""
        response = self.supabase.table(table).select("id").eq("article_title", article_title).execute()
        return len(response.data) > 0
    

    def add_article_with_embedding(self, table: str, article_data: dict):
        """Add article with auto-generated embedding"""
        # Generate embedding from summary only
        article_to_add = {}
        article_to_add['article_title'] = article_data['title']
        article_to_add['url'] = article_data['href']
        article_to_add['summary'] = article_data['body']
        article_to_add['source'] = article_data['source']
        article_to_add['companies'] = self.extractor.extract_companies(article_data['title'], article_data['body'])

        text_to_embed = article_data.get('body', '')
        embedding = self.model.encode(text_to_embed).tolist()

        # Add embedding to the data
        article_to_add['embedding'] = embedding

        # Insert the article
        return self.create_row(table, article_to_add)
    
    def batch_add_article_with_embedding(self):
        pass
