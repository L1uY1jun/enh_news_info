from dotenv import load_dotenv
from openai import OpenAI
import ast
import json
import logging
import openai
import os
import re

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
logger = logging.getLogger(__name__)

REFINEMENT_PROMPT = """
Your task is to filter and refine the extracted information, ensuring its relevance to the given title and goal.

Instructions:
1. Analyze the provided key statistical and non-statistical facts.
    - Retain all relevant facts based on the goal and the bigger picture behind the title.
2. For statistical facts:
    - Identify numerical values, percentages, or counts, and ensure they are accompanied by their respective units for clarity.
    - Detect patterns or trends that are visually representable (e.g., time series, comparisons across categories).
    - Group only structurally similar data points together (e.g., same kind of metric across regions, years, or technologies), ensuring that each group contains data points with the same or comparable units of measurement. If units differ, convert them to a consistent unit for comparison.
    - Avoid ranges. If data points are provided as ranges, split them into distinct data points.
    - Each group must include:
        - `"group_title"`: A short, descriptive name
        - `"description"`: What the group of data is about
        - `"data_points"`: A list of dictionaries where each has:
            - `"X"`: A short label (e.g., year, category, method) that is consistent and comparable across the group. Use clear, well-defined ranges rather than vague or inconsistent categories.
            - `"Y"`: A single numeric value (no ranges)
            - `"unit"`: Unit of measurement (%, MW, $, etc.)
            - `"category"`: (Optional) Only include if the data is explicitly categorized (e.g., region, technology type).
        - Example structure:
            {{
                "group_title": "Cost Increase Over Time",
                "description": "Tracking the increase in costs over multiple years for a specific product or service.",
                "data_points": [
                    {{"X": "2019", "Y": "50", "unit": "$"}},
                    {{"X": "2020", "Y": "55", "unit": "$"}},
                    {{"X": "2021", "Y": "60", "unit": "$"}},
                    {{"X": "2022", "Y": "65", "unit": "$"}}
                ]
            }}
3. For non-statistical facts:
    - Retain key qualitative facts that add depth, context, or narrative.
    - Combine related facts into meaningful summaries where appropriate to improve clarity and remove redundancy.

Here is the given information:
- Goal: {goal}
- Title: {title}
- Key Statistical Facts: {stats}
- Key Non-Statistical Facts: {facts}

Output only the following in valid python dictionary format:
{{
    "key_facts": {{
        "statistical": [
            {{Grouped Statistical Facts 1}},
            {{Grouped Statistical Facts 2}},
            ...
        ],
        "non_statistical": ["Refined fact 1", "Refined fact 2", ...]
    }}
}}
"""

REFINEMENT_SYSTEM_PROMPT = """You are an expert at analyzing and generating insightful, relevant, and structured data. Your task is to analyze and refine the statistical and non-statistical facts as per the given instructions. 

The output must be a Python dictionary, delimited with triple backticks, and must strictly follow the format given in the user's instructions. There should be no additional text, Markdown formatting, or escape characters in the response.
"""

STRUCTURE_CHECK_USER_PROMPT = """
Your task is to validate and sanitize the data to ensure it is a well-structured, syntactically correct Python dictionary. Carefully inspect the content for formatting issues, structural inconsistencies, or invalid characters, and correct them as needed to produce clean, error-free output.

Instructions:
1. There must be no non-printable or special characters (e.g., U+00A0) in the output. Remove or replace accordingly any characters that are not standard printable characters.
2. All parentheses, brackets, and braces must match correctly. Verify that every opening parenthesis `(`, bracket `[`, and brace `{` has a corresponding closing one `)`, `]`, and `}`.
3. The dictionary structure must be valid, and there should be no malformed nodes or objects. The structure must follow standard Python syntax for dictionaries.
4. Each value in the dictionary is a string, and all keys are also enclosed in double quotes.
5. If any formatting errors, mismatched brackets, or unexpected characters are detected, provide a clean, corrected output without extra explanations or comments.
6. Do not alter or modify any content that is already correct. Only fix the parts that are broken, malformed, or non-compliant.
"""

STRUCTURE_CHECK_SYSTEM_PROMPT = """
You are a validation and formatting expert. Your task is to inspect, clean, and ensure the correctness of the generated output as per the given instructions.

The output must be a Python dictionary, delimited with triple backticks. There should be no additional text, Markdown formatting, or escape characters in the response.
"""

def manage_info(retrieved_info, user_goal):

    user_prompt = REFINEMENT_PROMPT.format(
        goal=user_goal,
        title=retrieved_info["title"],
        stats=retrieved_info["key_facts"]["statistical"],
        facts=retrieved_info["key_facts"]["non_statistical"]
    )

    while True:
        completion = client.chat.completions.create(
            model="gpt-4.5-preview",
            messages=[
                {"role": "system", "content": REFINEMENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,
            top_p=0.8,
            frequency_penalty=0.4
        )

        dirty_output = completion.choices[0].message.content.strip()

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": STRUCTURE_CHECK_SYSTEM_PROMPT},
                {"role": "user", "content": STRUCTURE_CHECK_USER_PROMPT},
                {"role": "user", "content": dirty_output}
            ],
            temperature=0.5,
            top_p=0.5
        )

        try: 
            response = completion.choices[0].message.content.strip()
            refined_data = ast.literal_eval(re.sub(r"^```(python|json)?|```$", "", response).strip())
            break
        except (SyntaxError, ValueError) as e:
            logger.warning(f"Encountered error parsing response: {e}")
            logger.info("Retrying...")
    
    refined_data["title"] = retrieved_info["title"]
    
    graph_data = generate_graph_data(retrieved_info["title"], retrieved_info["key_entities"], user_goal)
    
    refined_data["graph"] = graph_data

    color_scheme = generate_color_scheme(refined_data)
    refined_data["colors"] = color_scheme

    return refined_data

GRAPH_PROMPT = """
 Your task is to analyze key entities and generate graph data, ensuring relevance to the given title and goal.

Instructions:
1. Evaluate each entity:
    - Remove overly specific entities (e.g., countries, individual names, scientific terms) that do not contribute to the general concept or framework of the broader topic.
    - Assign a relevance score between 1 and 10 based on how well the entity contributes to understanding the broader topic (i.e., systems, technologies, methodologies, key concepts).
    - Limit entity names to 20 characters or fewer, using abbreviations where necessary.
2. Create relation edges between related entities, specifying the relationship between them.
    - Keep relationship descriptions brief, with a maximum of 4 words.

Here is the given Information:
- Goal: {goal}
- Title: {title}
- Key Entities: {key_entities}

Output only the following in valid python dictionary format:
{{
    "nodes": [
        ["entity_1", {{"relevance": value_1}}],
        ["entity_2", {{"relevance": value_2}}],
        ["entity_3", {{"relevance": value_3}}],
        ...
    ],
    "edges": [
        ["entity_1", "entity_2", {{"relation": "relation_1"}}],
        ["entity_1", "entity_3", {{"relation": "relation_2"}}],
        ["entity_2", "entity_4", {{"relation": "relation_3"}}],
        ...
    ]
}}
"""

GRAPH_SYSTEM_PROMPT = """You are an expert at information analysis and relationship graph design. Your task is to analyze and process key entities as per the given instructions.

The output must be a Python dictionary, delimited with triple backticks, and should not include any additional text, Markdown formatting, or escape characters.

Every entity must be connected, meaning there is a path between every pair of entities in the graph.
"""

def generate_graph_data(title, key_entities, user_goal):

    user_prompt = GRAPH_PROMPT.format(
        goal=user_goal,
        title=title,
        key_entities=key_entities
    )

    while True:
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": GRAPH_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,
            top_p=0.8
        )

        try: 
            response = completion.choices[0].message.content.strip()
            return ast.literal_eval(re.sub(r"^```(python|json)?|```$", "", response).strip())
        except (SyntaxError, ValueError) as e:
            logger.warning(f"Encountered error parsing graph data: {e}")
            logger.info("Retrying...")

COLOR_SCHEME_PROMPT = """
Your task is to analyze the given infographic data and suggest an appropriate color scheme that enhances clarity and visual appeal while matching the theme and overall message.

Instructions:
1. Review the title, context, and key data points to understand the infographic's overall message and trends.
2. Create a cohesive color palette that matches the theme of the infographic and highlights important trends, categories, and relationships in the data. Ensure the colors enhance the visual appeal and clarity.
3. Ensure sufficient contrast between text and background for readability. 
4. Use only well-established, accessible color palettes (such as those from sources like Adobe Spectrum, ColorBrewer, or Material Design) to ensure clear and distinct color choices. Pay special attention to sequential palettes, ensuring lighter shades have enough contrast to stand out against the background.

Here is the given information: {info}

Output only the following in valid python dictionary format:
{{
    "primary": {{
        "background": "#hex_code",
        "text": "#hex_code",
        "accent": "#hex_code"
    }},
    "data_viz": {{
        "sequential_palette": ["#hex_code1", "#hex_code2", "#hex_code3", ...],
        "categorical_palette": ["#hex_code1", "#hex_code2", "#hex_code3", ...]
    }}
}}
"""

COLOR_SCHEME_SYSTEM_PROMPT = """
You are an expert infographic designer. Your task is to generate an appropriate color palette for the infographic that enhances clarity and visual appeal as per the instructions.

The output must be a Python dictionary, delimited with triple backticks, and should not include any additional text, Markdown formatting, or escape characters.
"""

def generate_color_scheme(refined_info):
    
    user_prompt = COLOR_SCHEME_PROMPT.format(info=refined_info)

    while True:
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": COLOR_SCHEME_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            top_p=0.5
        )

        try: 
            response = completion.choices[0].message.content.strip()
            return ast.literal_eval(re.sub(r"^```(python|json)?|```$", "", response).strip())
        except (SyntaxError, ValueError) as e:
            logger.warning(f"Encountered error parsing color scheme: {e}")
            logger.info("Retrying...")

# Testing-------------------------------------------------------
if __name__ == "__main__":
    with open("./enh_news_info/test/test_retrieved_info.txt", "r") as f:
        test_retrieved_info = json.load(f)

    goal = "Highlight energy generation efficiency between floating solar and other forms of renewable energy used in Singapore, showing their environmental benefits and scalability."

    refined_data = manage_info(test_retrieved_info, goal)

    with open("./enh_news_info/test/test_refined_data.txt", "w") as f:
        json.dump(refined_data, f, indent=4)
