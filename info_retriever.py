from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from info_extractor import extract_info
from openai import OpenAI
import copy
import json
import os
import time

load_dotenv()
client = OpenAI(api_key=os.getenv("PERPLEXITY_API_KEY"), base_url=os.getenv("PERPLEXITY_URL"))

MIN_NUM_FACTS = 30
MIN_CITATIONS = 5
MAX_THREADS = min(5, os.cpu_count())

def retrieve_info(news_info, processed_urls, user_goal, threshold=MIN_NUM_FACTS):
    retrieved_info = copy.deepcopy(news_info)
    topic = retrieved_info["title"]
    key_facts = retrieved_info["key_facts"]
    additional_queries = retrieved_info["additional_queries"]
    key_entities = retrieved_info["key_entities"]

    while len(key_facts["statistical"]) < threshold or len(key_facts["non_statistical"]) < threshold:
        if not additional_queries:
            break

        query = additional_queries.pop(0)
        response = query_relevant_articles(query)
        new_urls = [url for url in response if url not in processed_urls]

        with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            futures = {
                executor.submit(extract_info, url, user_goal, topic): url
                for url in new_urls
            }

            for future in as_completed(futures):
                news_url = futures[future]
                extracted_info = future.result()

                processed_urls.add(news_url)

                key_facts["statistical"].extend(extracted_info["key_facts"]["statistical"])
                key_facts["non_statistical"].extend(extracted_info["key_facts"]["non_statistical"])
                key_entities.extend(extracted_info["key_entities"])
                additional_queries.extend(extracted_info["additional_queries"])

    retrieved_info.pop("additional_queries")
    return retrieved_info

def query_relevant_articles(query):
    completion = client.chat.completions.create(
        model="sonar-pro", 
        messages=[
            {"role": "user", "content": query}
        ],
        top_p=0.8
    )
    return completion.citations[:MIN_CITATIONS]

# Testing-------------------------------------------------------
if __name__ == "__main__":
    with open("./Agent-Model-Infographic-Generator/test/test_news_info.txt", "r") as f:
        test_news_info = json.load(f)

    processed_urls = set(["https://www.channelnewsasia.com/commentary/singapore-indonesia-floating-solar-farm-batam-clean-energy-electricity-4737861"])
    goal = "Highlight energy generation efficiency between floating solar and other forms of renewable energy used in Singapore, showing their environmental benefits and scalability."

    retrieved_info = retrieve_info(test_news_info, processed_urls, goal)
    print(retrieved_info)
    
    with open("./Agent-Model-Infographic-Generator/test/test_retrieved_info.txt", "w") as f:
        json.dump(retrieved_info, f, indent=4)
