from dotenv import load_dotenv
from newspaper import Article
from newspaper.article import ArticleException
from openai import OpenAI
import ast
import json
import logging
import os
import openai
import re

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EMPTY_EXTRACTED_INFO = {
    "title": "",
    "key_facts": {
        "statistical": [],
        "non_statistical": []
    },
    "key_entities": [],
    "additional_queries": []
}

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """Your task is to refine the information extracted from a news article.

The goal of the extraction is as follows: {goal}

Instructions:
1. Transform the news title into an infographic-style title that is a single, concise sentence without colons (:), subtitles, or introductory phrases. Ensure it retains the core message of the original text.
2. Read through the entire article text carefully and extract key facts.
    - Statistical key facts: Identify claims supported by numerical data (e.g., percentages, financial figures, scientific measurements, population statistics).
    - Non-statistical key facts: Identify significant qualitative insights, key events, statements that provide essential context or meaning.
3. Gather a list of key entities by extracting main subjects, relevant topics, or contextual factors related to the article title.
4. Generate additional queries that explore broader background information or comparative insights beyond the immediate news topic. These queries should:
    - Focus on the goal of the user, ensuring relevance of the query to the user's objectives.
    - Ask questions that drive deeper context and not just repeating information.
    - Compare the main topic with other related topics to provide a broader understanding.
    - Explore how the main topic relates to global trends.

Here is the extracted information:
- Article Title: {title}
- Article Text: {text}

Output only the following in valid python dictionary format:
{{
    "title": "..."
    "key_facts": {{
        "statistical": ["Fact 1", "Fact 2" ...],
        "non_statistical": ["Fact 1", "Fact 2" ...]
    }},
    "key_entities": ["Entity 1", "Entity 2", ...],
    "additional_queries": ["Query 1", "Query 2", ...]
}}
"""

RELEVANT_EXTRACTION_PROMPT = """Your task is to extract relevant information from a news article with reference to a topic.

The goal of the extraction is as follows: {goal}

Instructions:
1. Understand the content of the topic
    - Based on this topic, analyze the provided text and extract relevant facts, key entities, and additional insights.
2. Read through the entire article text carefully and extract key facts.
    - Statistical key facts: Identify claims supported by numerical data (e.g., percentages, financial figures, scientific measurements, population statistics).
    - Non-statistical key facts: Identify significant qualitative insights, key events, statements that provide essential context or meaning that could support the topic.
3. Gather a list of relevant key entities by extracting main subjects, relevant topics, or contextual factors related to the main topic.
4. Generate additional queries that explore broader background information or comparative insights beyond the immediate news topic. These queries should:
    - Focus on the goal of the user, ensuring relevance of the query to the user's objectives.
    - Ask questions that drive deeper context and not just repeating information.
    - Compare the main topic with other related topics to provide a broader understanding.
    - Explore how the main topic relates to global trends.

Here is the provided information:
- Main Topic: {topic}
- Article Text: {text}

Output only the following in valid python dictionary format:
{{
    "key_facts": {{
        "statistical": ["Fact 1", "Fact 2" ...],
        "non_statistical": ["Fact 1", "Fact 2" ...]
    }},
    "key_entities": ["Entity 1", "Entity 2", ...],
    "additional_queries": ["Query 1", "Query 2", ...]
}}
"""

SYSTEM_PROMPT = """You are an expert in data extraction. Your task is to carefully analyze the provided news article and extract information as per the given instructions.

The output must be a Python dictionary, delimited with triple backticks, and should not include any additional text, Markdown formatting, or escape characters.
"""

def extract_info(news_url, user_goal, topic=None):
    article = Article(news_url)

    try:
        article.download()
        article.parse()
    except ArticleException as e:
        logger.error(f"ArticleException: Failed to process article at {news_url}")
        return EMPTY_EXTRACTED_INFO
    except Exception as e:
        logger.error(f"Unexpected error processing article at {news_url}")
        return EMPTY_EXTRACTED_INFO

    if topic:
        user_prompt = RELEVANT_EXTRACTION_PROMPT.format(goal=user_goal, topic=topic, text=article.text)
    else:
        user_prompt = EXTRACTION_PROMPT.format(goal=user_goal, title=article.title, text=article.text)

    while True:
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            top_p=0.9,
            presence_penalty=1.5
        )

        try: 
            response = completion.choices[0].message.content.strip()
            return ast.literal_eval(re.sub(r"^```(python|json)?|```$", "", response).strip())
        except (SyntaxError, ValueError) as e:
            logger.warning(f"Encountered error parsing response: {e}")
            logger.info("Retrying...")

# Testing-------------------------------------------------------
if __name__ == "__main__":
    news_url = "https://www.channelnewsasia.com/commentary/singapore-indonesia-floating-solar-farm-batam-clean-energy-electricity-4737861"
    goal = "Compare energy generation efficiency of floating solar to other forms of renewable energy used in Singapore."

    info = extract_info(news_url, goal)
    
    # with open("./enh_news_info/test/test_news_info.txt", "w") as f:
    #     json.dump(info, f, indent=4)
