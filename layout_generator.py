from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
from layout_rules import InfographicLayoutRules
from openai import OpenAI
from PIL import Image
from util import encode_img
import io
import json
import openai
import os
import re
import webbrowser

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SPECIFICATION_RULES = {name: member.value for name, member in InfographicLayoutRules.__members__.items()}

GENERATE_HTML_PROMPT = """
Your task is to generate a professional and visually appealing infographic layout in HTML code based on the provided data.

Instructions:
1. Use Bootstrap grid system to arrange the elements in a visually appealing way. Avoid simply stacking elements vertically. Arrange them dynamically using both vertical and horizontal alignment, making sure to use grid classes where appropriate.
2. Do not generate any new content. Use only the provided data. Avoid adding extra details, placeholders, or filler content beyond what is explicitly given.
3. Integrate figure images and a graph image cohesively within the grid. 
    - The provided specs include size, proportions (width/height), and content details. Use this information to position and scale the images properly within the grid for a balanced layout.
    - Use the figure descriptions to assess relative importance. Allocate more grid space to the more significant figures, ensuring visual hierarchy without overcrowding.
    - Do not include the figure descriptions in the captions as they are only for layout guidance.
4. Group related layout elements, regardless of type (e.g., figures, graphs, key facts), into clearly defined sections based on shared topics or themes. Each section should feel cohesive and self-contained within the grid, enhancing clarity and narrative flow.
    - Convey structure visually through layout and spacing rather than adding subtitles or section headers for every group.
5. Position each grouped section in relation to its relevance to the title or main topic. Elements that are most directly relevant should appear more prominently or earlier in the layout, while supporting sections can be positioned further down or to the side.
6. You are not required to use all provided elements (e.g. figures), only use the most relevant information to maintain clarity and readability, optimizing space effectively.
7. Strictly apply the provided color scheme consistently throughout the layout.

Here is the data:
- Infographic Title: {title}
- Key Facts: {facts}
- Figure Images: {f_spec}
- Graph Image: {g_spec}
- Color scheme: {color}
- Suggestions: {suggest}

The output layout should be in HTML code.
"""

GENERATE_HTML_SYSTEM_PROMPT = """
You are an expert infographic designer and HTML developer. Your task is to generate professional, visually appealing infographic layouts in HTML based on the data as per the given instructions. Ensure that the given constraints are followed.

Constraints:
Follow these predefined rules strictly: {rules}
1. Page height and width are specified in pixels.
2. Margin and padding ratios (X and Y) are relative to the respective page dimensions.
3. The infographic should be enclosed within a container element with the class "infographic-container".

The outputted HTML code must be delimited with triple backticks, and should not include any additional text, Markdown formatting, or escape characters.
"""

def generate_layout(title, key_facts, figure_specs, graph_spec, color_scheme, suggestions):
    user_prompt = GENERATE_HTML_PROMPT.format(
        title=title,
        facts=key_facts,
        f_spec=figure_specs,
        g_spec=graph_spec,
        color=color_scheme,
        suggest=suggestions,
        rules=SPECIFICATION_RULES
    )
    
    completion = client.chat.completions.create(
        model='gpt-4o',
        messages=[
            {"role": "system", "content": GENERATE_HTML_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
    )

    response = completion.choices[0].message.content.strip()
    return re.sub(r"^```(html)?|```$", "", response).strip()

POLISH_HTML_PROMPT = """
Your task is to polish and adjust the HTML code based on the user requests.

HTML code: 
{html}

User request: 
{req}

Below is the reference data used to create this infographic. Please reference these sources if any changes are requested:
- Title: {title}
- Key Facts: {facts}
- Figures: {f_spec}
- Graphs: {g_spec}

The output layout should be in HTML code.
"""

POLISH_HTML_SYSTEM_PROMPT = """
You are an expert infographic designer and HTML developer. Your task is to refine and optimize existing HTML code based on user requests. Ensure that the given constraints are followed.

Constraints:
Follow these predefined rules strictly: {rules}
1. Page height and width are specified in pixels.
2. Margin and padding ratios (X and Y) are relative to the respective page dimensions.
3. The infographic should be enclosed within a container element with the class "infographic-container".

The outputted HTML code must be delimited with triple backticks, and should not include any additional text, Markdown formatting, or escape characters.
"""

def polish_layout(title, key_facts, figure_specs, graph_spec, html_code, user_request):
    user_prompt = POLISH_HTML_PROMPT.format(
        html=html_code,
        req=user_request,
        facts=key_facts,
        f_spec=figure_specs,
        g_spec=graph_spec,
        rules=SPECIFICATION_RULES
    )

    completion = client.chat.completions.create(
        model='gpt-4o',
        messages=[
            {"role": "system", "content": POLISH_HTML_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
    )

    response = completion.choices[0].message.content.strip()
    return re.sub(r"^```(html)?|```$", "", response).strip()

def verify_html(html_code):
    return bool(BeautifulSoup(html_code, 'lxml').find(class_='infographic-container'))

# Testing-------------------------------------------------------
if __name__ == "__main__":
    with open("./Agent-Model-Infographic-Generator/test/test_refined_data.txt", "r") as f:
        refined_data = json.load(f)

    title = refined_data["title"]
    key_facts = refined_data["key_facts"]["non_statistical"]
    color_scheme = refined_data["colors"]["primary"]
    
    desc_file_name ="figure_desc.txt"
    graph_desc_file_name = "test_graph_desc.txt"

    in_path = "./Agent-Model-Infographic-Generator/test/test_img/"
    with open(in_path + desc_file_name, "r") as f:
        figure_specs = json.load(f)
    with open(in_path + graph_desc_file_name, "r") as f:
        graph_spec = json.load(f)
    
    html_code = generate_layout(title, key_facts, figure_specs, graph_spec, color_scheme, "")
    html_path = "./Agent-Model-Infographic-Generator/test/sample_html.html"

    if verify_html(html_code):
        print("The HTML contains the 'infographic-container' class and is valid.")
    else:
        print("The HTML does not contain the 'infographic-container' class. Please check the structure.")

    with open(html_path, "w") as f:
        f.write(html_code)
