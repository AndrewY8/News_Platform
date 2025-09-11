from news_agent.agent import PlannerAgent
from dotenv import load_dotenv
import json

load_dotenv();

planner = PlannerAgent()
results = planner.run("Tesla Q3 earnings SEC filings")
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