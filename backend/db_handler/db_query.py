from db_manager import dbManager
from google import genai
from google.genai import types
from openai import OpenAI
from pydantic import BaseModel, TypeAdapter
from enum import Enum
import json

class ScoreSchema(BaseModel):
    id: str
    reputation_score: float
    article_content_score: float
    article_relevance_score: float

class ArticleScoresList(BaseModel):
    scores: list[ScoreSchema]

class Models(Enum):
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"

class db_query:
    def __init__(self, dbmanager : dbManager, api_key : str, model :  Models = Models.OPENAI, model_name : str = 'gemini-2.0-flash-001'):
        self.manager = dbmanager
        self.model_type = model
        self.model_name = model_name
        match model:
            case Models.GEMINI:
                self.client = genai.Client(
                    api_key = api_key,
                    http_options=types.HttpOptions(api_version='v1')
                )

            case Models.OPENAI:
                self.client = OpenAI(api_key=api_key)

            case Models.ANTHROPIC:
                pass
    
    def _generate_config(self):
        match self.model_type:
            case Models.GEMINI:
                self.gemini_config = {
                    "temperature": 0.0,
                    "topP": 0.95,
                    "topK": 20,
                    "maxOutputTokens": 1000,
                    "stopSequences": ['STOP!'],
                    
                    # Add the JSON settings directly into this dictionary
                    "responseMimeType": "application/json",
                    
                    # Convert the Pydantic schema to a JSON schema dictionary
                    # We use TypeAdapter to specify that we expect a list of ScoreSchema objects
                    "responseSchema": TypeAdapter(list[ScoreSchema]).json_schema(),
                }
            case Models.OPENAI:
                self.openai_config = ArticleScoresList

            case Models.ANTHROPIC:
                pass

    def _format_articles_batch(self, articles: list) -> str:
        formatted_articles = []
        for i, article in enumerate(articles):
            formatted_articles.append({
                "id": article.get("id"),
                "index": i,
                "title": article.get("article_title"),
                "summary": article.get("summary"),
                "source": article.get("source", "Unknown")
            })
        return json.dumps(formatted_articles, indent=2)
    
    def _serve_prompt(self, query : str, articles):
        batch_prompt = f"""
        <task>
        Analyze and score each article based on how well it answers the user's query.
        Compare articles relative to each other for consistent scoring.
        </task>
        
        <user_query>
        {query}
        </user_query>
        
        <articles_to_rank>
        {self._format_articles_batch(articles)}
        </articles_to_rank>
        
        <scoring_instructions>
        For EACH article, provide three scores (0-10):
        
        1. reputation_score: Credibility and authority of the news source
           - 9-10: Major reputable sources (Reuters, AP, BBC, etc.)
           - 7-8: Well-known regional/specialized sources
           - 5-6: Lesser-known but legitimate sources
           - 1-4: Questionable or unknown sources
        
        2. article_content_score: Quality and depth of information
           - 9-10: Comprehensive, well-written, detailed
           - 7-8: Good quality, covers topic well
           - 5-6: Adequate but may lack depth
           - 1-4: Poor quality, minimal information
        
        3. article_relevance_score: How well it matches the query
           - 9-10: Directly answers the query completely
           - 7-8: Strong match, minor gaps
           - 5-6: Moderately relevant
           - 1-4: Barely relevant or off-topic
        
        Return scores for ALL articles in a single JSON response.
        </scoring_instructions>
        """
        return batch_prompt
    
    def _calculate_scores(self, score_values : ScoreSchema):
        self.w1 = 0.3
        self.w2 = 0.3
        self.w3 = 0.4
        return (score_values.reputation_score * self.w1 + 
                score_values.article_content_score * self.w2 +
                score_values.article_relevance_score * self.w3)
    
    def _find_and_rank_sources(self, query : str, top_results):
        articles = self.manager.similarity_search(query, top_results)
        prompt = self._serve_prompt(query, articles)
        self._generate_config()
        match self.model_type:
            case Models.GEMINI:
                scores = self.client.models.generate_content(
                    contents=prompt,
                    model=self.model_name,
                    config=self.gemini_config, # Renamed from 'config' for clarity
                )
            case Models.OPENAI:
                scores = self.client.responses.parse(
                    model = self.model_name,
                        input=[
                            {
                                "role": "system", "content": "Determine to the best of your ability what the correct weights for each of the articles should be."
                            },
                            {
                                "role": "user",
                                "content": prompt,
                            },
                        ],
                        text_format=self.openai_config,
                )
            case Models.ANTHROPIC:
                pass
        return scores