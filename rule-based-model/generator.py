from bs4 import BeautifulSoup
from dotenv import load_dotenv
from layout import DynamicLayoutRules
from openai import OpenAI
from parser import *
from sample_producer import *
from util import *
import os
import openai
import re
import webbrowser

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

GRAPH_QUERY_TEMPLATE = """
Objective: Generate and return only the layout program for graphviz based on the provided graph data:
    {}
    The layout must ensure clarity by positioning nodes and edges in a way that avoids overlapping or clutter, particularly considering node names.
"""

CONTENT_QUERY_TEMPLATE = """
Objective: Generate a clean and responsive HTML template for an infographic using the provided content and layout specifications. The layout should be creative.

Content:
    Description: The HTML output must use the following content variables as-is.:
     - news_url: The URL of the news the infographic is based on.
     - title: The main title of the infographic.
     - excerpt: A brief description or summary.
     - image_url: The URL of the main image.
     - image_prop: The aspect ratio of the image, calculated as width divided by height. Image dimensions must follow aspect ratio.
     - graph_url: The URL of the graph image.
     - graph_prop: The aspect ratio of the graph, calculated as width divided by height. Graph dimensions must follow aspect ratio.
     - related_facts: A list of key facts related to the infographic, sorted by decreasing relevance.
     - related_articles: A list of related articles for additional context, sorted by decreasing relevance.
    Defined Content Variables: {}
"""

HTML_TEMPLATE = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Infographic</title>
        <style>
            :root {
                --page-width: (...)px;
                --page-height: (...)px;

                --margin-x-ratio: (...);
                --margin-y-ratio: (...);

                --padding-x-ratio: (...);
                --padding-y-ratio: (...);

                --title-height-ratio: (...);
                --excerpt-height-ratio: (...);
                --image-height-ratio: (...);
                --graph-height-ratio: (...);
                --related-articles-height-ratio: (...);

                --margin-x: calc(var(--margin-x-ratio) * var(--page-width));
                --margin-y: calc(var(--margin-y-ratio) * var(--page-height));
                --padding-x: calc(var(--padding-x-ratio) * var(--page-width));
                --padding-y: calc(var(--padding-y-ratio) * var(--page-height));
                --title-height: calc(var(--title-height-ratio) * var(--page-height));
                --excerpt-height: calc(var(--excerpt-height-ratio) * var(--page-height));
                --image-height: calc(var(--image-height-ratio) * var(--page-height));
                --graph-height: calc(var(--graph-height-ratio) * var(--page-height));
                --related-article-height: calc(var(--related-articles-height-ratio) * var(--page-height));
            }
            body {
                padding: 0;
                margin: var(--margin-y) var(--margin-x);
                font-family: (...);
                line-height: 1.25;
                color: (...);
                background-color: (...);
                width: var(--page-width);
                height: var(--page-height);
                display: flex;
                flex-direction: (...);
                align-items: center;
            }
            header {
                text-align: center;
                font-size: (...)px;
                color: (...);
                padding: var(--padding-y) var(--padding-x);
                height: var(--title-height);
                width: calc(var(--page-width) - 2 * var(--margin-x) - 2 * var(--padding-x));
            }
            header h1{
                margin: 0;
            }
            .excerpt {
                text-align: justify;
                font-size: (...)px;
                color: (...);
                padding: var(--padding-y) var(--padding-x);
                height: var(--excerpt-height);
                width: calc(var(--page-width) - 2 * var(--margin-x) - 2 * var(--padding-x));
            }
            .image {
                text-align: center;
                padding: var(--padding-y) var(--padding-x);
                height: var(--image-height);
                width: calc(var(--page-width) - 2 * var(--margin-x) - 2 * var(--padding-x));
            }
            .graph {
                text-align: center;
                padding: var(--padding-y) var(--padding-x);
                height: var(--graph-height);
                width: calc(var(--page-width) - 2 * var(--margin-x) - 2 * var(--padding-x));
            }
            .related-facts {
                padding: var(--padding-y) var(--padding-x);
                margin: 0;
                height: var(--related-article-height);
                width: calc(var(--page-width) - 2 * var(--margin-x) - 2 * var(--padding-x));
                list-style-type: disc;
                overflow: hidden;
            }
            .related-facts li {
                font-size: (...)px;
                color: #999;
                margin-bottom: calc(var(--padding-y) / 2);
            }
            .related-facts:empty {
                display: none;
            }
        </style>
    </head>
    <body>
        <header>
            <h1>...</h1>
        </header>
        <section class="excerpt">
            <p>...</p>
        </section>
        <section class="image">
            <img src="..." style="max-width: 100%; max-height: 100%; object-fit: contain;">
        </section>
        <section class="graph">
            <img src="..." style="max-width: 100%; max-height: 100%; object-fit: contain;">
        </section>
        <section class="related-facts">
            ...
        </section>
    </body>
    </html>
"""

HTML_QUERY_TEMPLATE = f"""
HTML Template: The output HTML code must follow this template, fill in the empty (...) spaces: {HTML_TEMPLATE}
     NOTE: You may only modify the template by altering the orientation of the infographic. For example, you can stack two elements horizontally instead of vertically by placing them in a container and adjusting the flex properties. Ensure all code is properly updated to reflect these orientation changes.
"""

SPECIFICATION_RULES = {name: member.value for name, member in DynamicLayoutRules.__members__.items()}

SPECIFICATION_QUERY_TEMPLATE = f"""
Specifications:
    Defined Specification Variables: {SPECIFICATION_RULES}
    These additional specifications must also be met:
     1. The sum of all margin ratios comprising of the entire page dimensions in x and y must be strictly less than 1.0.
     2. Font size of title > Font size of excerpt > Font size of related facts and articles
     3. Related facts are optional and should be presented in pointers. Do not include more than what will fit into the space.
     4. Be creative with the colors (3 different colors at maximum).
     5. Keep the infographic compact, do not have excessive white space.
"""

DEFAULT_TEMPERATURE = 0.7
SAMPLE_HTML_PATH = ".\\Infographic_Generator\\layout_model\\sample_html"
MARGIN_OF_ERROR = 0.05

def generate_query_results(infographic_content):
    graph = infographic_content['graph']

    layout_prog = generate_graph_layout(graph)
    graph_img = draw_graph(graph, layout_prog)
    graph_url = "graph_" + datetime.now().strftime("%Y_%m_%d") + ".png"
    graph_img.save(SAMPLE_HTML_PATH + "\\" + graph_url, format="PNG")

    infographic_content.pop('graph')
    infographic_content['graph_url'] = graph_url
    infographic_content['graph_prop'] = graph_img.size[0] / graph_img.size[1]

    html_code = generate_html_code(infographic_content)
    while not is_valid_html(html_code):
        print("not valid")
        html_code = generate_html_code(infographic_content)

    verified = False
    iterations = 5
    while not verified and iterations > 0:
        print(iterations)
        verified, content_errors = verify_html_content(html_code, infographic_content)
        print(content_errors)
        if not verified:
            html_code = try_fix_html_code(html_code, content_errors, rule_errors)
            iterations -= 1
            continue
        verified, rule_errors = verify_html_rules(html_code, SPECIFICATION_RULES)
        print(rule_errors)
        if not verified:
            html_code = try_fix_html_code(html_code, content_errors, rule_errors)
            iterations -= 1
        iterations -= 1
    
    html_url = "sample_html_" + datetime.now().strftime("%Y_%m_%d") + ".html"
    html_path = SAMPLE_HTML_PATH + "\\" + html_url
    with open(html_path, "w") as f:
        f.write(html_code)

    abs_path = os.path.abspath(html_path)
    file_url = f"file://{abs_path}"
    webbrowser.open(file_url)

def generate_graph_layout(graph):
    graph_query = GRAPH_QUERY_TEMPLATE.format(graph)

    completion = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            {"role": "system", "content": "You are an expert graph layout analyst. Your task is to analyse graph data and determine the most suitable graphviz layout. Output only the layout parameter."},
            {"role": "user", "content": graph_query}
        ]
    )
    return completion.choices[0].message.content.strip()

def generate_html_code(content):
    content_query = CONTENT_QUERY_TEMPLATE.format(content)

    completion = client.chat.completions.create(
        model='gpt-4o',
        messages=[
            {"role": "system", "content": "You are a creative infographic designer. Your task is to generate clean, responsive, and valid HTML code for a creative infographic design based on the provided content and layout rules. Return only the HTML code, without any explanatory text or comments."},
            {"role": "user", "content": content_query},
            {"role": "user", "content": HTML_QUERY_TEMPLATE},
            {"role": "user", "content": SPECIFICATION_QUERY_TEMPLATE}
        ],
        temperature=DEFAULT_TEMPERATURE
    )
    return completion.choices[0].message.content.strip()

def is_valid_html(html_code):
    is_valid = True
    try:
        soup = BeautifulSoup(html_code, 'html.parser')
    except Exception as e:
        is_valid = False
    return is_valid

def try_fix_html_code(html_code, content_errors, rule_errors):
    errors_msg = f"""
        The errors identified in the code are as follows:
        {json.dumps(content_errors, indent=2)}
        {json.dumps(rule_errors, indent=2)}
    """

    completion = client.chat.completions.create(
        model='gpt-4o',
        messages=[
            {"role": "system", "content": "You are an expert HTML code analyst. Your task is to review the provided HTML code, identify and resolve the specified errors, and ensure compliance with the given specification rules. Return only the corrected HTML code, without any explanatory text or comments."},
            {"role": "user", "content": html_code},
            {"role": "user", "content": errors_msg},
            {"role": "user", "content": SPECIFICATION_QUERY_TEMPLATE}
        ],
        temperature=DEFAULT_TEMPERATURE
    )
    return completion.choices[0].message.content.strip()

def verify_html_content(html_code, content):
    soup = BeautifulSoup(html_code, 'lxml')
    verification_results = {'status': True, 'errors': {}}

    elements_to_verify = {
        'title': {
            'selector': 'h1',
            'get_content': lambda el: el.get_text(),
            'expected': content['title']
        },
        'excerpt': {
            'selector': '.excerpt p',
            'get_content': lambda el: el.get_text(),
            'expected': content['excerpt']
        },
        'image': {
            'selector': '.image img',
            'get_content': lambda el: el['src'],
            'expected': content['image_url']
        },
        'graph': {
            'selector': '.graph img',
            'get_content': lambda el: el['src'],
            'expected': content['graph_url']
        }
    }

    for key, info in elements_to_verify.items():
        element = soup.select_one(info['selector'])
        if not element:
            verification_results['status'] = False
            verification_results['errors'][key] = f"{key} element is missing in the HTML."
        else:
            actual_content = info['get_content'](element)
            verify_content(actual_content, info['expected'], key, verification_results)

    related_facts_section = soup.find(class_='related-facts')
    if not related_facts_section:
        verification_results['status'] = False
        verification_results['errors']['related_facts'] = "related facts section is missing in the HTML."
    else:
        related_facts = [fact.get_text() for fact in related_facts_section.find_all('li')]
        expected_related_facts = content['related_facts']
        if related_facts != expected_related_facts[:len(related_facts)]:
            verification_results['status'] = False
            verification_results['errors']['related_facts'] = (
                "related facts does not match the expected content or order."
            )
    return verification_results['status'], verification_results['errors']

def verify_content(element, expected_value, error_key, verification_results):
    if element != expected_value:
        verification_results['status'] = False
        verification_results['errors'][error_key] = f"{error_key} does not match given content"

def verify_html_rules(html_code, rules):
    soup = BeautifulSoup(html_code, 'lxml')
    css_content = soup.find('style').get_text()

    root_match = re.search(r":root\s*{([^}]*)}", css_content)
    if root_match:
        root_css = root_match.group(1)
        reg_exp = r"([\w-]+-ratio|--page-\w+):\s*([^;]+)(?=;)"
        matches = re.findall(reg_exp, root_css)
        css_dict = {}

        for var, value in matches:
            if 'px' in value:
                value = re.sub(r'px', '', value.strip())
            css_dict[var] = value.strip()
    
    header_font_match = re.search(r"header\s*{[^}]*font-size:\s*([0-9.]+)px;", css_content)
    if header_font_match:
        css_dict['header-font-size'] = header_font_match.group(1)
    
    excerpt_font_match = re.search(r".excerpt\s*{[^}]*font-size:\s*([0-9.]+)px;", css_content)
    if excerpt_font_match:
        css_dict['excerpt-font-size'] = excerpt_font_match.group(1)
    
    related_article_font_match = re.search(r".related-facts li\s*{[^}]*font-size:\s*([0-9.]+)px;", css_content)
    if related_article_font_match:
        css_dict['related-article-font-size'] = related_article_font_match.group(1)
        
    verification_results = {'status': True, 'errors': {}}

    str_to_key_mapping = {
        '--page-width': 'PAGE_WIDTH_RANGE',
        '--page-height': 'PAGE_HEIGHT_RANGE',
        '--margin-x-ratio': 'MARGIN_X_RATIO',
        '--margin-y-ratio': 'MARGIN_Y_RATIO',
        '--padding-x-ratio': 'PADDING_X_RATIO',
        '--padding-y-ratio' : 'PADDING_Y_RATIO',
        '--title-height-ratio': 'TITLE_HEIGHT_RATIO',
        '--title-width-ratio': 'TITLE_WIDTH_RATIO',
        '--excerpt-height-ratio': 'EXCERPT_HEIGHT_RATIO',
        '--excerpt-width-ratio': 'EXCERPT_WIDTH_RATIO',
        '--image-height-ratio': 'IMAGE_HEIGHT_RATIO',
        '--image-width-ratio': 'IMAGE_WIDTH_RATIO',
        '--graph-height-ratio': 'GRAPH_HEIGHT_RATIO',
        '--graph-width-ratio': 'GRAPH_WIDTH_RATIO',
        '--related-articles-height-ratio': 'RELATED_ARTICLES_HEIGHT_RATIO',
        '--related-articles-width-ratio': 'RELATED_ARTICLES_WIDTH_RATIO',
        'header-font-size': 'TITLE_FONT_RANGE',
        'excerpt-font-size': 'EXCERPT_FONT_RANGE',
        'related-article-font-size': 'RELATED_ARTICLE_FONT_RANGE'
    }

    for css_var, value in css_dict.items():
        value_range = SPECIFICATION_RULES[str_to_key_mapping[css_var]]
        value = float(value)
        if value < value_range[0]:
            verification_results['status'] = False
            verification_results['errors'][css_var] = f"{css_var} is lower than the allowed range of values."
        elif value > value_range[1]:
            verification_results['status'] = False
            verification_results['errors'][css_var] = f"{css_var} is higher than the allowed range of values."

    return verification_results['status'], verification_results['errors']

if __name__ == '__main__':
    content = parse_generation_event_v2(sample_query_event_long)
    generate_query_results(content)

    # with open(SAMPLE_HTML_PATH + "\\test.html", "r") as f:
    #     test_html_code = f.read()
    # with open(SAMPLE_HTML_PATH + "\\test_content.txt", "r") as f:
    #     test_content = json.load(f)
    # print(verify_html_rules(test_html_code, SPECIFICATION_RULES))
