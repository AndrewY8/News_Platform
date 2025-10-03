"""
Chat Router Module - Updated to use News Agent System
Contains all chat/search related FastAPI endpoints using PlannerAgent and AggregatorAgent.
"""

import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from db_handler.supaManager import dbManager, EmbeddingModel
from db_handler.company_extractor import CompanyExtractor
import google.generativeai as genai
import os
import sys

# Add parent directory to path for news_agent imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from news_agent.integration.planner_aggregator import EnhancedPlannerAgent
    from news_agent.agent import PlannerAgent
    NEWS_AGENT_AVAILABLE = True
except Exception as e:
    NEWS_AGENT_AVAILABLE = False
    print(f"Warning: News Agent System not available in chat router: {e}")

logger = logging.getLogger(__name__)

# Database manager will be passed from app.py

# Initialize enhanced news agent system
enhanced_news_agent = None
news_agent = None  # Keep for backward compatibility

if NEWS_AGENT_AVAILABLE:
    try:
        # Initialize EnhancedPlannerAgent with aggregation capabilities
        enhanced_news_agent = EnhancedPlannerAgent(
            max_concurrent_retrievers=3,
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            enable_aggregation=True
        )
        # Keep reference to underlying PlannerAgent for streaming compatibility
        news_agent = enhanced_news_agent.planner_agent
        logger.info("Chat router: Enhanced News Agent System initialized")
    except Exception as e:
        logger.error(f"Chat router: Failed to initialize Enhanced News Agent System: {e}")
        # Fallback to basic PlannerAgent
        try:
            news_agent = PlannerAgent(max_concurrent_retrievers=3)
            logger.info("Chat router: Fallback to basic PlannerAgent")
        except Exception as fallback_e:
            logger.error(f"Chat router: Fallback also failed: {fallback_e}")
            news_agent = None
            enhanced_news_agent = None

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Pydantic Models
class ChatRequest(BaseModel):
    message: str
    user_id: Optional[int] = 1
    conversation_history: Optional[List[Dict]] = []

class EnhancedSearchRequest(BaseModel):
    query: str
    user_id: Optional[int] = 1
    use_agent: bool = True
    limit: int = 10

# Result transformation functions (same as in main app.py)
def convert_planner_to_aggregator_format(agent_results):
    """Convert PlannerAgent results to AggregatorAgent expected format"""
    if not agent_results or not isinstance(agent_results, list):
        return {}

    formatted = {
        "breaking_news": [],
        "financial_news": [],
        "sec_filings": [],
        "general_news": []
    }

    for result in agent_results:
        if result.get('status') != 'success' or not result.get('results'):
            continue

        retriever_name = result.get('retriever', '').lower()
        results = result.get('results', [])

        # Map retrievers to categories
        if 'edgar' in retriever_name:
            category = 'sec_filings'
        elif 'tavily' in retriever_name or 'financial' in retriever_name:
            category = 'financial_news'
        elif 'breaking' in retriever_name or 'urgent' in retriever_name:
            category = 'breaking_news'
        else:
            category = 'general_news'

        # Add results to the appropriate category
        for item in results:
            if isinstance(item, dict) and ('content' in item or 'body' in item or 'title' in item):
                formatted[category].append(item)

    logger.info(f"Formatted results: {[(k, len(v)) for k, v in formatted.items()]}")
    return formatted

def transform_agent_results_to_articles(agent_results):
    """Transform news agent results to frontend-compatible article format"""
    articles = []

    logger.info(f"transform_agent_results_to_articles called with: type={type(agent_results)}, is_list={isinstance(agent_results, list)}")

    if not agent_results or not isinstance(agent_results, list):
        logger.warning(f"Early return from transform: agent_results empty or not list")
        return articles

    for result in agent_results:
        if result.get('status') != 'success' or not result.get('results'):
            continue

        retriever_name = result.get('retriever', 'Unknown')
        results = result.get('results', [])

        for item in results:
            article = transform_single_result_to_article(item, retriever_name)
            if article:
                articles.append(article)

    return articles

def transform_single_result_to_article(item, source_retriever):
    """Transform a single retrieval result to article format"""
    try:
        if isinstance(item, dict):
            # Handle Tavily format which uses 'href' and 'body'
            url = item.get('url') or item.get('link') or item.get('href')
            content = item.get('content') or item.get('body', '')
            title = item.get('title') or item.get('headline')

            # If no title, extract from content or URL
            if not title:
                if content:
                    # Extract title from first sentence or first 100 chars
                    title = content.split('.')[0][:100] if content else 'Untitled Article'
                elif url:
                    # Extract title from URL
                    title = url.split('/')[-1].replace('-', ' ').replace('_', ' ')[:100]
                else:
                    title = 'Untitled Article'

            # Use actual source name from the article, not the retriever name
            actual_source = item.get('source')
            if not actual_source or actual_source == source_retriever:
                # If no source or source is just the retriever name, try to extract from URL
                if url:
                    actual_source = url.split("//")[-1].split("/")[0].replace("www.", "").title()
                else:
                    actual_source = source_retriever

            # Clean and format the preview content
            preview_text = item.get('summary') or item.get('description') or content or ""
            if preview_text:
                # Remove markdown formatting and clean up the text
                preview_text = preview_text.strip()
                # Remove leading dots, hashes, and other markdown artifacts
                preview_text = preview_text.lstrip('...').lstrip('#').lstrip('*').lstrip('-').strip()
                # Remove multiple spaces and newlines
                preview_text = ' '.join(preview_text.split())
                # Ensure it's not too long
                if len(preview_text) > 200:
                    preview_text = preview_text[:200].rsplit(' ', 1)[0] + "..."
                # If it's empty after cleaning, use fallback
                if not preview_text or len(preview_text) < 10:
                    preview_text = "Click to read full article..."
            else:
                preview_text = "Click to read full article..."

            return {
                "id": item.get('id') or f"{source_retriever}-{hash(str(item))}"[:16],
                "date": format_article_date(item.get('published_date') or item.get('date') or item.get('timestamp')),
                "title": title,
                "source": actual_source,
                "preview": preview_text,
                "sentiment": determine_sentiment(item.get('sentiment')),
                "tags": extract_tags_from_item(item),
                "url": url,
                "relevance_score": item.get('relevance_score') or item.get('score') or 0.5,
                "category": item.get('category') or 'General'
            }
        elif isinstance(item, str):
            return {
                "id": f"{source_retriever}-{hash(item)}"[:16],
                "date": "Today",
                "title": item[:100] + "..." if len(item) > 100 else item,
                "source": source_retriever,
                "preview": item,
                "sentiment": 'neutral',
                "tags": [],
                "url": None,
                "relevance_score": 0.3,
                "category": 'General'
            }
    except Exception as e:
        logger.error(f"Error transforming item to article: {e}")
        return None

def format_article_date(date_input):
    """Format various date inputs to frontend-compatible format"""
    if not date_input:
        return "Today"
    try:
        if isinstance(date_input, str):
            from dateutil import parser
            date_obj = parser.parse(date_input)
        else:
            date_obj = date_input

        now = datetime.now()
        diff = now - date_obj

        if diff.days == 0:
            return "Today"
        elif diff.days == 1:
            return "Yesterday"
        elif diff.days < 7:
            return f"{diff.days} days ago"
        else:
            return date_obj.strftime("%b %d")
    except:
        return "Today"

def determine_sentiment(sentiment_input):
    """Determine sentiment from various inputs"""
    if not sentiment_input:
        return 'neutral'

    if isinstance(sentiment_input, (int, float)):
        if sentiment_input > 0.1:
            return 'positive'
        elif sentiment_input < -0.1:
            return 'negative'
        else:
            return 'neutral'

    sentiment_str = str(sentiment_input).lower()
    if 'positive' in sentiment_str or 'bullish' in sentiment_str:
        return 'positive'
    elif 'negative' in sentiment_str or 'bearish' in sentiment_str:
        return 'negative'
    else:
        return 'neutral'

def extract_tags_from_item(item):
    """Extract tags from various item formats"""
    tags = []
    for field in ['tags', 'keywords', 'topics', 'symbols']:
        if field in item and item[field]:
            if isinstance(item[field], list):
                tags.extend([str(tag) for tag in item[field]])
            else:
                tags.append(str(item[field]))
    return list(set(tags))

def create_findings_summary(agent_results, articles):
    """Create a summary of findings for Gemini"""
    if not agent_results:
        return "No results found."

    summary_parts = []

    if isinstance(agent_results, list):
        successful = [r for r in agent_results if r.get('status') == 'success']
        summary_parts.append(f"Searched {len(agent_results)} sources, {len(successful)} successful.")

        if successful:
            sources = [r.get('retriever', 'Unknown') for r in successful]
            summary_parts.append(f"Active sources: {', '.join(set(sources))}")

    summary_parts.append(f"Found {len(articles)} relevant articles.")

    if articles:
        sample_titles = [a['title'] for a in articles[:3]]
        summary_parts.append(f"Key articles: {'; '.join(sample_titles)}")

    return "\n".join(summary_parts)

# Chat Route Functions
async def chat_about_news_streaming(request: ChatRequest, supabase_db):
    """Enhanced chat using news agent system with direct streaming thinking steps"""
    import json
    import uuid

    async def generate_stream():
        try:
            if not NEWS_AGENT_AVAILABLE or (not enhanced_news_agent and not news_agent):
                yield f"data: {json.dumps({'type': 'error', 'message': 'News research system unavailable'})}\n\n"
                return

            logger.info(f"Chat request: {request.message}")


            # Use streaming PlannerAgent execution
            try:
                # Stream the PlannerAgent execution with real-time progress
                async def stream_planner_execution():
                    import google.generativeai as genai
                    from news_agent.prompts import augment_query
                    from news_agent.actions.retriever import get_retriever_tasks
                    from news_agent.retrievers.EDGAR.EDGAR import EDGARRetriever

                    # Step 1: Query Analysis
                    yield f"data: {json.dumps({'type': 'thinking', 'step': 'Analyzing your query for search strategies...'})}\n\n"

                    # Step 2: Generate search strategies using PlannerAgent's method
                    model = genai.GenerativeModel('gemini-2.0-flash')
                    response = model.generate_content([augment_query(request.message)])
                    parse_queries = lambda s: [line.split('@@@', 1)[1] for line in s.strip().split('\n') if '@@@' in line]
                    augmented_queries = parse_queries(response.text)

                    yield f"data: {json.dumps({'type': 'thinking', 'step': f'Generated {len(augmented_queries)} targeted search strategies'})}\n\n"

                    # Step 3: Get retriever tasks using PlannerAgent's method
                    retriever_tasks = get_retriever_tasks(augmented_queries, genai)
                    retriever_tasks.append((EDGARRetriever, request.message))

                    yield f"data: {json.dumps({'type': 'thinking', 'step': f'Preparing {len(retriever_tasks)} data sources for search...'})}\n\n"

                    # Step 4: Execute retrievers with real-time updates
                    all_results = []
                    for i, (retriever, task) in enumerate(retriever_tasks, 1):
                        retriever_name = retriever.__name__

                        # Generate progress message using Gemini
                        progress_prompt = f"Generate a brief, professional progress message for searching {retriever_name} (step {i}/{len(retriever_tasks)}). Be specific about the data source type. Return only the message, no extra text."
                        try:
                            progress_response = model.generate_content([progress_prompt])
                            progress_msg = progress_response.text.strip()
                        except:
                            progress_msg = f"Searching {retriever_name} ({i}/{len(retriever_tasks)})..."

                        yield f"data: {json.dumps({'type': 'thinking', 'step': progress_msg})}\n\n"

                        # Use PlannerAgent's retriever execution method
                        try:
                            result = await news_agent._run_retriever_task(retriever, task)
                            all_results.append(result)

                            result_count = len(result.get('results', [])) if result else 0
                            yield f"data: {json.dumps({'type': 'thinking', 'step': f'Found {result_count} articles from {retriever_name}'})}\n\n"

                        except Exception as e:
                            logger.error(f"Error running {retriever_name}: {str(e)}")
                            yield f"data: {json.dumps({'type': 'thinking', 'step': f'Issue with {retriever_name}, continuing with other sources...'})}\n\n"
                            all_results.append({
                                "retriever": retriever_name,
                                "status": "error",
                                "error": str(e),
                                "results": []
                            })

                    # Step 5: Completion
                    successful_results = [r for r in all_results if r.get('status') == 'success']
                    total_articles = sum(len(r.get('results', [])) for r in successful_results)
                    yield f"data: {json.dumps({'type': 'thinking', 'step': f'Search complete: {total_articles} articles from {len(successful_results)} sources'})}\n\n"

                    # Yield results as a special marker
                    yield ("__RESULTS__", all_results)

                # Execute streaming PlannerAgent and collect results
                agent_results = []
                async for item in stream_planner_execution():
                    if isinstance(item, tuple) and item[0] == "__RESULTS__":
                        agent_results = item[1]
                        logger.info(f"Received agent results: {len(agent_results) if isinstance(agent_results, list) else 'not a list'}")
                        logger.info(f"Agent results type: {type(agent_results)}")
                        if isinstance(agent_results, list) and len(agent_results) > 0:
                            logger.info(f"First result sample: {list(agent_results[0].keys()) if isinstance(agent_results[0], dict) else type(agent_results[0])}")
                    else:
                        yield item

                logger.info(f"Final agent_results: {agent_results} items")

                # Process results with enhanced capabilities
                suggested_articles = []
                enhanced_summaries = []

                # Store articles in Supabase if configured (async parallel processing)
                try:
                    if supabase_db and hasattr(supabase_db, 'add_article_with_embedding'):
                        table_name = "Articles"  # You can make this configurable
                        articles_added = 0

                        # Collect all articles first
                        all_articles = []
                        for retriever_result in agent_results:
                            if retriever_result.get('status') == 'success' and retriever_result.get('results'):
                                articles = retriever_result.get('results', [])
                                all_articles.extend(articles)

                        logger.info(f"Processing {len(all_articles)} articles for storage...")

                        # Process articles in parallel batches to avoid overwhelming OpenAI API
                        async def process_article_batch(article_batch):
                            batch_results = []
                            for article in article_batch:
                                try:
                                    # Check if article already exists to avoid duplicates
                                    if hasattr(supabase_db, 'check_article_exists'):
                                        article_title = article.get('title', '')
                                        if article_title and supabase_db.check_article_exists(table_name, article_title):
                                            logger.debug(f"Article '{article_title}' already exists, skipping")
                                            continue

                                    # Add article with embedding (this includes OpenAI API call)
                                    result = supabase_db.add_article_with_embedding(table_name, article)
                                    if result:
                                        batch_results.append(True)
                                        logger.debug(f"Added article: {article.get('title', 'Unknown')}")
                                except Exception as article_error:
                                    logger.warning(f"Failed to add article {article.get('title', 'Unknown')}: {article_error}")
                            return len(batch_results)

                        # Process in batches of 3 to avoid rate limits
                        batch_size = 3
                        total_added = 0

                        for i in range(0, len(all_articles), batch_size):
                            batch = all_articles[i:i + batch_size]
                            try:
                                # Process this batch
                                batch_added = await process_article_batch(batch)
                                total_added += batch_added

                                # Small delay between batches to respect rate limits
                                if i + batch_size < len(all_articles):
                                    await asyncio.sleep(0.5)

                            except Exception as batch_error:
                                logger.warning(f"Batch processing error: {batch_error}")

                        logger.info(f"Added {total_added} new articles to Supabase")
                    else:
                        logger.warning("Supabase database not properly configured for article storage")
                except Exception as db_error:
                    logger.error(f"Supabase database storage error: {db_error}")

                # Transform raw results to articles first
                logger.info(f"About to transform agent_results: type={type(agent_results)}, length={len(agent_results) if isinstance(agent_results, (list, dict)) else 'N/A'}")
                suggested_articles = transform_agent_results_to_articles(agent_results)
                logger.info(f"Transformed {len(suggested_articles)} articles from raw results")

                if len(suggested_articles) == 0:
                    logger.warning("No articles were transformed! Checking agent_results structure...")
                    if isinstance(agent_results, list):
                        for i, result in enumerate(agent_results[:3]):  # Check first 3 items
                            logger.info(f"Result {i}: type={type(result)}, keys={list(result.keys()) if isinstance(result, dict) else 'not dict'}")
                            if isinstance(result, dict) and 'results' in result:
                                logger.info(f"Result {i} has 'results' key with {len(result['results'])} items")
                    else:
                        logger.info(f"agent_results is not a list: {type(agent_results)}")

                # If we have enhanced agent, get aggregated summaries separately
                if enhanced_news_agent and agent_results:
                    try:
                        yield f"data: {json.dumps({'type': 'thinking', 'step': 'Processing results with AI aggregation...'})}\n\n"
                        enhanced_summaries = []

                        # Convert PlannerAgent results to expected format for aggregation
                        formatted_results = convert_planner_to_aggregator_format(agent_results)
                        logger.info(f"Converted results for aggregation: {list(formatted_results.keys()) if formatted_results else 'None'}")

                        # Process with aggregator directly
                        if formatted_results and enhanced_news_agent.aggregator:
                            aggregation_result = enhanced_news_agent.aggregator.process_planner_results(
                                formatted_results
                            )

                            if aggregation_result and aggregation_result.clusters:
                                for cluster in aggregation_result.clusters:
                                    if cluster.summary:
                                        enhanced_summaries.append({
                                            'id': cluster.id,
                                            'title': f"Cluster Summary ({cluster.source_count} sources)",
                                            'summary': cluster.summary.summary,
                                            'key_points': cluster.summary.key_points,
                                            'confidence': cluster.summary.confidence,
                                            'source_count': cluster.source_count
                                        })

                                logger.info(f"Enhanced aggregation: {len(enhanced_summaries)} summaries generated")
                                yield f"data: {json.dumps({'type': 'thinking', 'step': f'Generated {len(enhanced_summaries)} AI-powered summaries'})}\n\n"
                            else:
                                logger.warning("Aggregation completed but no clusters/summaries generated")
                        else:
                            logger.warning("No formatted results or aggregator available for processing")

                        # Fallback: try the original method if no summaries generated
                        if not enhanced_summaries:
                            try:
                                enhanced_results = await enhanced_news_agent.run_async(request.message, return_aggregated=True)
                                if isinstance(enhanced_results, list) and len(enhanced_results) > 0:
                                    enhanced_result = enhanced_results[0]

                                    # Extract summaries if available
                                    if 'summaries' in enhanced_result and enhanced_result['summaries']:
                                        enhanced_summaries = enhanced_result['summaries']
                                        logger.info(f"Fallback aggregation: {len(enhanced_summaries)} summaries generated")
                                        yield f"data: {json.dumps({'type': 'thinking', 'step': f'Generated {len(enhanced_summaries)} AI-powered summaries'})}\n\n"
                                    else:
                                        logger.warning("No summaries found in fallback enhanced results")
                                else:
                                    logger.warning("Fallback enhanced results returned empty or invalid format")
                            except Exception as fallback_error:
                                logger.error(f"Fallback aggregation also failed: {fallback_error}")
                                enhanced_summaries = []
                    except Exception as aggregation_error:
                        logger.error(f"Enhanced aggregation failed: {aggregation_error}")
                        enhanced_summaries = []

                # Generate AI response
                yield f"data: {json.dumps({'type': 'thinking', 'step': 'Generating AI response...'})}\n\n"

                try:
                    findings_summary = create_findings_summary(agent_results, suggested_articles)
                    import google.generativeai as genai
                    model = genai.GenerativeModel('gemini-2.0-flash')
                    response = model.generate_content([
                        f"Based on the following news research findings for the user query '{request.message}', provide a helpful, conversational response. Focus on the key insights and mention that I've found relevant articles to review:\n\n{findings_summary}\n\nProvide a response as if you're a knowledgeable financial news assistant."
                    ])
                    ai_response = response.text
                except Exception as e:
                    logger.error(f"Gemini response error: {e}")
                    ai_response = f"I've researched your query about '{request.message}' and found several relevant articles. Please review the suggested articles below for the latest information."

                # Chat history can be saved to Supabase if needed
                logger.debug(f"Chat completed for query: {request.message[:50]}...")

                # Send final response with enhanced data
                final_response = {
                    'type': 'response',
                    'response': ai_response,
                    'suggested_articles': suggested_articles[:5]
                }

                # Add enhanced summaries if available
                if enhanced_summaries:
                    final_response['enhanced_summaries'] = enhanced_summaries[:3]  # Include top 3 summaries
                    final_response['aggregation_enabled'] = True
                    logger.info(f"Enhanced response with {len(enhanced_summaries)} summaries")
                else:
                    final_response['aggregation_enabled'] = False

                logger.info(f"FINAL RESPONSE ARTICLES: {len(final_response['suggested_articles'])} articles")

                yield f"data: {json.dumps(final_response)}\n\n"

            except Exception as e:
                logger.error(f"PlannerAgent execution error: {e}")
                yield f"data: {json.dumps({'type': 'thinking', 'step': 'Encountered an issue, providing basic response...'})}\n\n"

                # Fallback response
                fallback_response = {
                    'type': 'response',
                    'response': f"I encountered an error while researching your query about '{request.message}'. Please try rephrasing your question or try again later.",
                    'suggested_articles': []
                }
                yield f"data: {json.dumps(fallback_response)}\n\n"

        except Exception as e:
            logger.error(f"Chat endpoint error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Error processing your query'})}\n\n"

    return StreamingResponse(generate_stream(), media_type="text/plain")

# Removed unused chat_about_news function - now only using streaming version

async def enhanced_search_handler(request: EnhancedSearchRequest):
    """Enhanced search using the enhanced news agent system"""
    try:
        if not NEWS_AGENT_AVAILABLE or (not enhanced_news_agent and not news_agent):
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": "Enhanced news agent system not available",
                    "articles": [],
                    "search_method": "unavailable",
                    "sources_used": [],
                    "total_found": 0,
                    "aggregation_enabled": False
                }
            )

        logger.info(f"Enhanced search request: {request.query}")

        # Use the EnhancedPlannerAgent if available
        if enhanced_news_agent:
            agent_results = await enhanced_news_agent.run_async(request.query, return_aggregated=True)
            # Extract the first result for compatibility
            if isinstance(agent_results, list) and len(agent_results) > 0:
                agent_results = agent_results[0]
            search_method = "enhanced_planner_with_aggregation"
        else:
            # Fallback to basic PlannerAgent
            agent_results = await news_agent.run_async(request.query)
            search_method = "basic_planner_fallback"

        # Transform results to frontend format
        articles = transform_agent_results_to_articles(agent_results)

        # Limit results if needed
        if request.limit and len(articles) > request.limit:
            articles = articles[:request.limit]

        # Extract sources used and aggregation info
        sources_used = []
        enhanced_summaries = []
        aggregation_enabled = False

        if isinstance(agent_results, dict):
            # Extract sources from enhanced results structure
            if 'aggregation' in agent_results:
                aggregation_enabled = agent_results['aggregation'].get('enabled', False)
                sources_used = agent_results['aggregation'].get('sources_used', [])

            # Extract enhanced summaries
            if 'summaries' in agent_results:
                enhanced_summaries = agent_results['summaries']

            # Fallback for sources if not in aggregation section
            if not sources_used and isinstance(agent_results.get('results'), list):
                sources_used = [result.get('retriever', 'Unknown') for result in agent_results['results'] if result.get('status') == 'success']
        elif isinstance(agent_results, list):
            # Basic format
            sources_used = [result.get('retriever', 'Unknown') for result in agent_results if result.get('status') == 'success']

        response_content = {
            "success": True,
            "articles": articles,
            "search_method": search_method,
            "sources_used": list(set(sources_used)),
            "total_found": len(articles),
            "aggregation_enabled": aggregation_enabled
        }

        # Add enhanced summaries if available
        if enhanced_summaries:
            response_content["enhanced_summaries"] = enhanced_summaries[:5]  # Top 5 summaries
            response_content["summary_count"] = len(enhanced_summaries)

        return JSONResponse(content=response_content)

    except Exception as e:
        logger.error(f"Enhanced search error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "articles": [],
                "search_method": "error",
                "sources_used": [],
                "total_found": 0
            }
        )

# Function to add routes to FastAPI app
def add_chat_routes(app, shared_limiter, supabase_db):
    """Add chat routes to the FastAPI app"""

    @app.post("/api/chat/stream")
    @shared_limiter.limit("20/minute")
    async def chat_stream_endpoint(request: Request, chat_request: ChatRequest):
        logger.info(f"Chat stream request: {chat_request.message}")
        return await chat_about_news_streaming(chat_request, supabase_db)

    @app.post("/api/search/enhanced")
    @shared_limiter.limit("10/minute")
    async def enhanced_search(request: Request, search_request: EnhancedSearchRequest):
        return await enhanced_search_handler(search_request)

    logger.info("Chat routes added successfully")