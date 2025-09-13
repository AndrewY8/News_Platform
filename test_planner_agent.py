from news_agent.agent import PlannerAgent
from news_agent.integration.planner_aggregator import create_enhanced_planner
from dotenv import load_dotenv
import os
import json

load_dotenv();

planner = create_enhanced_planner(
    gemini_api_key=os.getenv("GEMINI_API_KEY"),
    max_retrievers=5,
    config_overrides={
        'clustering': {
            'min_cluster_size': 2,
            'similarity_threshold': 0.65
        }
    }
)

results = planner.run("Tesla new products")
# print("RESULTS")
# print(results)
print(f"SEC filings found: {len(results['sec_filings'])}")
print(results['sec_filings'])
print(f"Financial news: {len(results['financial_news'])}")
print(results['financial_news'])
print(f"Breaking news: {len(results['breaking_news'])}")
print(results['breaking_news'])
print(f"General news: {len(results['general_news'])}")
print(results['general_news'])
json.dump(results, open("test_output.json", "w"), indent=2)
