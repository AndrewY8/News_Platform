"""
SEC Document RAG Service
Provides RAG-based search and question answering for SEC documents.
"""

import logging
import os
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio
# Try to import scikit-learn, fallback to simple implementation if not available
try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError as e:
    print(f"Warning: scikit-learn not available ({e}), using simple text matching")
    SKLEARN_AVAILABLE = False
    TfidfVectorizer = None
    cosine_similarity = None
import re
from dataclasses import dataclass

# Import existing SEC service
from sec_service import sec_service

logger = logging.getLogger(__name__)

@dataclass
class DocumentChunk:
    """Represents a chunk of SEC document content."""
    id: str
    document_id: str
    content: str
    chunk_index: int
    start_position: int
    end_position: int
    metadata: Dict[str, Any]

class SimpleVectorStore:
    """
    Simple in-memory vector store using TF-IDF for document similarity.
    Falls back to basic text matching if scikit-learn is not available.
    In production, this could be replaced with a proper vector database like Pinecone, Weaviate, etc.
    """
    
    def __init__(self):
        self.chunks: Dict[str, DocumentChunk] = {}
        if SKLEARN_AVAILABLE:
            self.vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=1,
                max_df=0.95
            )
            self.vectors = None
        else:
            self.vectorizer = None
            self.vectors = None
        self.fitted = False
    
    def add_chunks(self, chunks: List[DocumentChunk]):
        """Add document chunks to the vector store."""
        for chunk in chunks:
            self.chunks[chunk.id] = chunk
        
        # Rebuild vectors when new chunks are added
        self._rebuild_vectors()
    
    def _rebuild_vectors(self):
        """Rebuild the TF-IDF vectors for all chunks."""
        if not self.chunks:
            return
        
        if not SKLEARN_AVAILABLE:
            # Just mark as fitted for text-based search
            self.fitted = True
            logger.info(f"Ready for text-based search with {len(self.chunks)} chunks")
            return
        
        try:
            texts = [chunk.content for chunk in self.chunks.values()]
            self.vectors = self.vectorizer.fit_transform(texts)
            self.fitted = True
            logger.info(f"Rebuilt vectors for {len(self.chunks)} chunks")
        except Exception as e:
            logger.error(f"Error rebuilding vectors: {e}")
            self.fitted = False
    
    def search(self, query: str, top_k: int = 5, min_similarity: float = 0.1) -> List[Tuple[DocumentChunk, float]]:
        """Search for similar chunks using TF-IDF similarity or text matching."""
        if not self.fitted or not self.chunks:
            return []
        
        if not SKLEARN_AVAILABLE:
            # Fallback to simple text matching
            return self._text_based_search(query, top_k)
        
        try:
            # Vectorize the query
            query_vector = self.vectorizer.transform([query])
            
            # Calculate similarities
            similarities = cosine_similarity(query_vector, self.vectors).flatten()
            
            # Get top-k results
            top_indices = similarities.argsort()[-top_k:][::-1]
            
            results = []
            chunk_list = list(self.chunks.values())
            
            for idx in top_indices:
                similarity = similarities[idx]
                if similarity >= min_similarity:
                    results.append((chunk_list[idx], similarity))
            
            return results
        
        except Exception as e:
            logger.error(f"Error during vector search: {e}")
            # Fallback to text search
            return self._text_based_search(query, top_k)
    
    def _text_based_search(self, query: str, top_k: int = 5) -> List[Tuple[DocumentChunk, float]]:
        """Simple text-based search fallback."""
        query_words = set(query.lower().split())
        results = []
        
        for chunk in self.chunks.values():
            content_words = set(chunk.content.lower().split())
            
            # Calculate simple word overlap score
            intersection = query_words.intersection(content_words)
            if intersection:
                score = len(intersection) / len(query_words)
                results.append((chunk, score))
        
        # Sort by score and return top-k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    def get_document_chunks(self, document_id: str) -> List[DocumentChunk]:
        """Get all chunks for a specific document."""
        return [chunk for chunk in self.chunks.values() if chunk.document_id == document_id]
    
    def clear(self):
        """Clear all chunks and vectors."""
        self.chunks.clear()
        self.vectors = None
        self.fitted = False

class SECDocumentChunker:
    """Handles chunking of SEC documents for RAG processing."""
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_document(self, document_content: str, document_id: str, metadata: Dict[str, Any] = None) -> List[DocumentChunk]:
        """
        Split document content into overlapping chunks for RAG processing.
        
        Args:
            document_content: The full document content
            document_id: Unique identifier for the document
            metadata: Additional metadata for the document
            
        Returns:
            List of DocumentChunk objects
        """
        if not document_content or not document_content.strip():
            return []
        
        if metadata is None:
            metadata = {}
        
        chunks = []
        content = self._clean_content(document_content)
        
        # Try to chunk by paragraphs first, then fall back to character-based chunking
        paragraph_chunks = self._chunk_by_paragraphs(content)
        
        if paragraph_chunks:
            chunks.extend(self._create_chunks_from_segments(paragraph_chunks, document_id, metadata))
        else:
            # Fall back to character-based chunking
            char_chunks = self._chunk_by_characters(content)
            chunks.extend(self._create_chunks_from_segments(char_chunks, document_id, metadata))
        
        return chunks
    
    def _clean_content(self, content: str) -> str:
        """Clean document content for better chunking."""
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove HTML tags if present
        content = re.sub(r'<[^>]+>', '', content)
        
        # Remove excessive punctuation
        content = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\[\]\"\']+', ' ', content)
        
        return content.strip()
    
    def _chunk_by_paragraphs(self, content: str) -> List[str]:
        """Attempt to chunk by logical paragraphs."""
        # Split by double newlines or periods followed by significant whitespace
        paragraphs = re.split(r'\n\s*\n|\.\s{3,}', content)
        
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # If adding this paragraph would exceed chunk size, save current chunk
            if len(current_chunk) + len(paragraph) > self.chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                # Start new chunk with overlap
                current_chunk = self._get_overlap_text(current_chunk) + " " + paragraph
            else:
                current_chunk += " " + paragraph if current_chunk else paragraph
        
        # Add the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _chunk_by_characters(self, content: str) -> List[str]:
        """Fall back to character-based chunking."""
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + self.chunk_size
            
            # Try to end at a sentence boundary
            if end < len(content):
                # Look for sentence endings within the last 200 characters
                search_start = max(start + self.chunk_size - 200, start)
                sentence_end = self._find_sentence_boundary(content, search_start, end)
                if sentence_end > start:
                    end = sentence_end
            
            chunk = content[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = max(start + self.chunk_size - self.overlap, end)
        
        return chunks
    
    def _find_sentence_boundary(self, content: str, start: int, end: int) -> int:
        """Find the best sentence boundary within a range."""
        # Look for sentence endings (., !, ?) followed by space or end of string
        for i in range(end - 1, start - 1, -1):
            if content[i] in '.!?' and (i + 1 >= len(content) or content[i + 1].isspace()):
                return i + 1
        return end
    
    def _get_overlap_text(self, text: str) -> str:
        """Get the last portion of text for overlap."""
        if len(text) <= self.overlap:
            return text
        
        # Try to find a good breaking point for overlap
        overlap_start = len(text) - self.overlap
        
        # Look for sentence boundary within overlap region
        for i in range(overlap_start, len(text)):
            if text[i] in '.!?' and i + 1 < len(text) and text[i + 1].isspace():
                return text[i + 1:].strip()
        
        # Fall back to character-based overlap
        return text[-self.overlap:].strip()
    
    def _create_chunks_from_segments(self, segments: List[str], document_id: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        """Create DocumentChunk objects from text segments."""
        chunks = []
        position = 0
        
        for i, segment in enumerate(segments):
            chunk_id = f"{document_id}_chunk_{i}"
            
            chunk = DocumentChunk(
                id=chunk_id,
                document_id=document_id,
                content=segment,
                chunk_index=i,
                start_position=position,
                end_position=position + len(segment),
                metadata=metadata
            )
            
            chunks.append(chunk)
            position += len(segment)
        
        return chunks

class SECRAGService:
    """Main RAG service for SEC documents."""
    
    def __init__(self):
        self.vector_store = SimpleVectorStore()
        self.chunker = SECDocumentChunker(chunk_size=1000, overlap=200)
        self.document_cache: Dict[str, Dict[str, Any]] = {}
    
    async def process_document(self, document_id: str, force_refresh: bool = False) -> bool:
        """
        Process a SEC document for RAG queries.
        
        Args:
            document_id: The SEC document ID (format: cik_accession)
            force_refresh: Whether to force reprocessing even if cached
            
        Returns:
            True if successfully processed, False otherwise
        """
        try:
            # Check if already processed and cached
            if document_id in self.document_cache and not force_refresh:
                logger.info(f"Document {document_id} already processed")
                return True
            
            logger.info(f"Processing SEC document: {document_id}")
            
            # Parse document ID to get CIK and accession
            parts = document_id.split("_", 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid document ID format: {document_id}")
            
            cik, accession = parts
            
            # Get document content using existing SEC service
            filings_data = sec_service.get_latest_filings(cik)
            if not filings_data:
                raise ValueError(f"Could not find filings for CIK: {cik}")
            
            # Find the specific document
            recent = filings_data.get("filings", {}).get("recent", {})
            accessions = recent.get("accessionNumber", [])
            docs = recent.get("primaryDocument", [])
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            
            document_info = None
            for i, acc in enumerate(accessions):
                if acc == accession:
                    doc_name = docs[i] if i < len(docs) else None
                    form_type = forms[i] if i < len(forms) else "Unknown"
                    filing_date = dates[i] if i < len(dates) else "Unknown"
                    
                    if doc_name:
                        # Construct document URL
                        acc_no_dash = accession.replace("-", "")
                        doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_dash}/{doc_name}"
                        
                        document_info = {
                            'url': doc_url,
                            'form_type': form_type,
                            'filing_date': filing_date,
                            'company': filings_data.get("name", "Unknown Company"),
                            'ticker': sec_service._get_ticker_from_cik(cik)
                        }
                    break
            
            if not document_info:
                raise ValueError(f"Could not find document for accession: {accession}")
            
            # Get document content
            content = sec_service.get_document_content(document_info['url'])
            if not content:
                raise ValueError(f"Could not retrieve document content from: {document_info['url']}")
            
            # Create metadata for chunks
            metadata = {
                'company': document_info['company'],
                'ticker': document_info['ticker'],
                'form_type': document_info['form_type'],
                'filing_date': document_info['filing_date'],
                'url': document_info['url'],
                'processed_at': datetime.utcnow().isoformat()
            }
            
            # Chunk the document
            chunks = self.chunker.chunk_document(content, document_id, metadata)
            
            if not chunks:
                raise ValueError("No chunks were created from document content")
            
            # Add chunks to vector store
            self.vector_store.add_chunks(chunks)
            
            # Cache document info
            self.document_cache[document_id] = {
                'info': document_info,
                'metadata': metadata,
                'chunk_count': len(chunks),
                'processed_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Successfully processed document {document_id} into {len(chunks)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {e}")
            return False
    
    def query_document(self, document_id: str, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Query a specific SEC document using RAG.
        
        Args:
            document_id: The SEC document ID
            query: User question about the document
            top_k: Number of relevant chunks to retrieve
            
        Returns:
            Dictionary containing answer and relevant chunks
        """
        try:
            # Check if document is processed
            if document_id not in self.document_cache:
                return {
                    'error': f'Document {document_id} has not been processed yet. Please wait for processing to complete.',
                    'chunks': [],
                    'metadata': {}
                }
            
            # Get document-specific chunks
            document_chunks = self.vector_store.get_document_chunks(document_id)
            
            if not document_chunks:
                return {
                    'error': f'No processed chunks found for document {document_id}',
                    'chunks': [],
                    'metadata': self.document_cache[document_id]
                }
            
            # Search within document chunks
            if SKLEARN_AVAILABLE:
                # Use TF-IDF similarity
                temp_vectorizer = TfidfVectorizer(
                    max_features=500,
                    stop_words='english',
                    ngram_range=(1, 2),
                    min_df=1
                )
                
                chunk_texts = [chunk.content for chunk in document_chunks]
                chunk_vectors = temp_vectorizer.fit_transform(chunk_texts)
                query_vector = temp_vectorizer.transform([query])
                
                # Calculate similarities
                similarities = cosine_similarity(query_vector, chunk_vectors).flatten()
                
                # Get top-k results
                top_indices = similarities.argsort()[-top_k:][::-1]
                
                relevant_chunks = []
                for idx in top_indices:
                    if similarities[idx] > 0.05:  # Minimum similarity threshold
                        chunk = document_chunks[idx]
                        relevant_chunks.append({
                            'content': chunk.content,
                            'similarity': float(similarities[idx]),
                            'chunk_index': chunk.chunk_index,
                            'metadata': chunk.metadata
                        })
            else:
                # Use simple text matching
                query_words = set(query.lower().split())
                chunk_scores = []
                
                for chunk in document_chunks:
                    content_words = set(chunk.content.lower().split())
                    intersection = query_words.intersection(content_words)
                    if intersection:
                        score = len(intersection) / len(query_words)
                        chunk_scores.append((chunk, score))
                
                # Sort by score and get top-k
                chunk_scores.sort(key=lambda x: x[1], reverse=True)
                
                relevant_chunks = []
                for chunk, score in chunk_scores[:top_k]:
                    if score > 0.1:  # Minimum similarity threshold
                        relevant_chunks.append({
                            'content': chunk.content,
                            'similarity': score,
                            'chunk_index': chunk.chunk_index,
                            'metadata': chunk.metadata
                        })
            
            # Generate answer based on relevant chunks
            answer = self._generate_answer(query, relevant_chunks)
            
            return {
                'answer': answer,
                'chunks': relevant_chunks,
                'document_info': self.document_cache[document_id]['info'],
                'metadata': self.document_cache[document_id]['metadata'],
                'query': query
            }
            
        except Exception as e:
            logger.error(f"Error querying document {document_id}: {e}")
            return {
                'error': f'Error processing query: {str(e)}',
                'chunks': [],
                'metadata': {}
            }
    
    def _generate_answer(self, query: str, relevant_chunks: List[Dict[str, Any]]) -> str:
        """
        Generate an answer based on relevant chunks.
        This is a simple implementation - could be enhanced with an LLM.
        """
        if not relevant_chunks:
            return "I couldn't find relevant information in this document to answer your question."
        
        # For now, provide a summary of the most relevant chunks
        answer_parts = []
        answer_parts.append(f"Based on the document content, here's what I found related to your question:")
        answer_parts.append("")
        
        for i, chunk in enumerate(relevant_chunks[:3], 1):  # Limit to top 3 chunks
            # Extract a relevant excerpt (first 200 characters)
            excerpt = chunk['content'][:300].strip()
            if len(chunk['content']) > 300:
                excerpt += "..."
            
            answer_parts.append(f"{i}. {excerpt}")
            answer_parts.append("")
        
        if len(relevant_chunks) > 3:
            answer_parts.append(f"(Found {len(relevant_chunks)} total relevant sections)")
        
        answer_parts.append("")
        answer_parts.append("Note: This is a document-based search. For more detailed analysis, consider asking more specific questions about particular sections or terms.")
        
        return "\n".join(answer_parts)
    
    def get_document_status(self, document_id: str) -> Dict[str, Any]:
        """Get processing status for a document."""
        if document_id in self.document_cache:
            return {
                'status': 'processed',
                'chunk_count': self.document_cache[document_id]['chunk_count'],
                'processed_at': self.document_cache[document_id]['processed_at'],
                'metadata': self.document_cache[document_id]['metadata']
            }
        else:
            return {
                'status': 'not_processed',
                'chunk_count': 0,
                'processed_at': None,
                'metadata': {}
            }
    
    def clear_cache(self):
        """Clear all cached documents and vectors."""
        self.document_cache.clear()
        self.vector_store.clear()
        logger.info("Cleared SEC RAG service cache")

# Global instance
sec_rag_service = SECRAGService()