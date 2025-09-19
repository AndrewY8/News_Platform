'''

implementation of gemini with mcp where tavily acts as a tool

'''

import os
import requests
from dotenv import load_dotenv
from news_agent.retrievers.tavily.tavily_search import TavilyRetriever

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

retriever_declaration = {
    "name": "tavily_search",
    "description": "Conducts a web search using the tavily api to find sources for a given user query.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The query passed through to the tavily api that is then used to search for content. The search should be specific with regards to the types of sources being searched for. For example, 'reputable news' should always be search queries appended to whatever the user is requesting",
                "maxLength" : 400
            }
        },
        "required": ["query"],
    },
}

def tavily_search(query : str) -> str:
    '''
    this could be used as an abstraction layer where we make calls to tavily and get the intended results

    '''
    ret_obj = TavilyRetriever(query)
    result = ret_obj.search()
    if result is None:
        result = []
    
    return {            
            "status": "success",
            "results": result
        }            


think_about_query_declaration = {
    "name": "think_about_query",
    "description": "Generates a list of topics that the agent should think about using when conducting the agentic search. This is linked with the tavily retriever where the tavily retriever will automatically be called when this function is called.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The query originally passed through by the user that is sent to the agent for generating a list of possible responses",
            }
        },
        "required": ["query"],
    },
}

def think_about_query(query : str) -> str:
    '''
    this is used as the thinking agent layer where the agent thinks about how to reformat the user's queries
    '''
    contents = [
        types.Content(
            role = "user", parts= [types.Part(text="Your job is to take the initial user query that is sent from a user on a news app and think about possible related topics to pass back to an agent responsible for searching")]
        ),
        types.Content(
            role="user", parts = [types.Part(text="The queries should be specific with regards to the types of sources being searched for. For example, 'reputable news' should always be search queries appended to whatever the user is requesting")]
        ),
        types.Content(
            role = "user", parts = [types.Part(text=query)]
        )
    ]
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config={
            "response_mime_type" : "application/json",
            "response_schema" : {
                "type" : "array",
                "items" : {"type" : "string"}
            }
        },
    )

    return {"queries" : response.text}


newsapi_declaration = {
    "name": "newsapi_search",
    "description": "Query using newsapi to find articles corresponding to the news articles that the user may find interesting.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Keywords or phrases to search for in the article title and body. Advanced search is supported here:"
                'Surround phrases with quotes (") for exact match.'
                'Prepend words or phrases that must appear with a + symbol. Eg: +bitcoin'
                'Prepend words that must not appear with a - symbol. Eg: -bitcoin'
                'Alternatively you can use the AND / OR / NOT keywords, and optionally group these with parenthesis. Eg: crypto AND (ethereum OR litecoin) NOT bitcoin.'
                'The complete value for q must be URL-encoded. Max length: 500 chars.',
                "maxLength" : 500
            }
        },
        "required": ["query"],
    },
}

def newsapi_search(q : str, page_size : int = 5):
    """
    Query news_api after all of the other tasks have been completed to generate results that can then be used for streaming to the front end
    """
    url = "https://newsapi.org/v2/everything"

    params = {
        "q": q,
        "pageSize": page_size,
        "sortBy": "relevancy",   # or "publishedAt"
        "language": "en",
        "domains" : "nytimes.com,wsj.com,washingtonpost.com,latimes.com,"
                    "bbc.com,theguardian.com,reuters.com,ft.com,economist.com,"
                    "cnn.com,cnbc.com,bloomberg.com,forbes.com,npr.org,"
                    "abcnews.go.com,cbsnews.com,nbcnews.com,pbs.org,"
                    "aljazeera.com,dw.com,lemonde.fr,elpais.com,"
                    "techcrunch.com,wired.com,venturebeat.com,usatoday.com",
        "apiKey": NEWS_API_KEY,
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        return {"status": "error", "message": response.text}

    data = response.json()
    articles = [
        {
            "title": art.get("title"),
            "description": art.get("description"),
            "url": art.get("url"),
            "publishedAt": art.get("publishedAt"),
            "source": art.get("source", {}).get("name"),
            "content": art.get("content"),
        }
        for art in data.get("articles", [])
    ]

    return {"status": "ok", "results": articles}


from google import genai
from google.genai import types

# Configure the client and tools
client = genai.Client(api_key=GEMINI_API_KEY)
tools = types.Tool(function_declarations=[retriever_declaration, think_about_query_declaration, newsapi_declaration])
config = types.GenerateContentConfig(tools=[tools])


def run_agent(user_query : str, max_iters = 5):
    contents = [
        types.Content(
            role="user", parts=[types.Part(text="Use tavily to find reputable news source regarding the questions the user has. If the user query is unclear, ask for clarification.")]
        ),
        types.Content(
            role="user", parts=[types.Part(text="Call the think about query function to generate a list of topics that should be searched about additionally to the user query to generate better query ideas and to send multiple queries to tavily instead of just the original user query.")]
        ),
        types.Content(
            role="user", parts=[types.Part(text="Call the news_api search function to search for articles and obtain explicit titles and article names in addition to tavily searches. You can use this to initially query about the topic and find results.")]
        ),
        types.Content(
            role="user", parts=[types.Part(text="Help me find information regarding Nvidia's most recent collaboration with the US government.")]
        )
    ]

    all_results = []

    for i in range(max_iters):
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=config,
        )

        part = response.candidates[0].content.parts[0]

    if hasattr(part, "function_call"):
        tool_call = part.function_call
        
        if tool_call.name == "think_about_query":
            print("thinking tool called")
            result = think_about_query(**tool_call.args)
            refined_queries = result["queries"]
            search_results = []
            import json
            try:
                refined_queries = json.loads(refined_queries)
            except:
                refined_queries = []
            
            for rq in refined_queries:
                search_results.append(tavily_search(rq))
            result = {"refined_queries" : refined_queries, "search_results" : search_results}
            all_results.extend(search_results)
        
        elif tool_call.name == 'tavily_search':
            print("tavily explicitly called")
            result = tavily_search(**tool_call.args)
            all_results.append(result)
        
        elif tool_call.name == 'newsapi_search':
            print("newsapi_search called")
            result = newsapi_search(**tool_call.args)
            all_results.append(result)
            
        else:
            result = {"status" : "error", "reason" : "Unknown tool"}

            contents.append(response.candidates[0].content)
            contents.append(types.Content(
                role="function",
                parts=[types.Part.from_function_response(
                    name=tool_call.name,
                    response={"result": result},
                )]
            ))

    else:
        print("FINAL SUMMARY:\n", response.text)
        return all_results, response.text
    

    return all_results, "Max iterations reached — partial results."

if __name__ == "__main__":
    all_results, summary = run_agent("Help me find information regarding Nvidia's most recent collaboration with the US government.")
    print("\nAGGREGATED RESULTS:", all_results)