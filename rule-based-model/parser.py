from datetime import datetime
from PIL import Image
from io import BytesIO

from sample_producer import sample_query_event_long
from util import *
import requests

SAMPLE_HTML_PATH = ".\\Infographic_Generator\\rule_based_model\\sample_html"
RELATED_ARTICLE_TEMPLATE = "{} ({}, src={})"

def parse_generation_event(event):
    request_id = event.request_id
    title = event.title
    desc = event.description
    
    img_url = getattr(event, "image", None)
    image = None
    if img_url:
        res = requests.get(img_url)
        if img_url and res.status_code == 200:
            image = Image.open(BytesIO(res.content))
    
    adj_list = convert_keys_str_to_int(event.adjlist)
    node_occ = convert_keys_str_to_int(event.node_occurrences)
    node_labels = convert_keys_str_to_int(event.entity_labels)
    relations = convert_keys_str_to_int(event.property_labels)

    nodes = [(node_labels[node], {"occurence": count * 100}) for node, count in node_occ.items()]
    edges = []
    for src_id in adj_list:
        for dst_info in adj_list[src_id]:
            dst_id, relation_id = dst_info
            edges.append((node_labels[src_id], node_labels[dst_id], {"relation": relations[relation_id]}))

    related_articles = event.related_articles
    related_facts = event.related_facts

    params = {
        "request_id": request_id,
        "title": title,
        "excerpt": desc,
        "graph": {
            "nodes": nodes,
            "edges": edges
        },
        "related_facts": related_facts
    }

    parsed_data = params.copy()
    layout_params = params.copy()
    if img_url:
        parsed_data["image"] = image
        layout_params["img_url"] = event.image

    layout_params["info_url"] = event.url
    layout_params["related_articles"] = related_articles
    return parsed_data, layout_params

def parse_generation_event_v2(event):
    request_id = event.request_id
    title = event.title
    desc = event.description
    
    img_url = getattr(event, "image", None)
    image = None
    if img_url:
        res = requests.get(img_url)
        if img_url and res.status_code == 200:
            image = Image.open(BytesIO(res.content))
    
    adj_list = convert_keys_str_to_int(event.adjlist)
    node_occ = convert_keys_str_to_int(event.node_occurrences)
    node_labels = convert_keys_str_to_int(event.entity_labels)
    relations = convert_keys_str_to_int(event.property_labels)

    nodes = [(node_labels[node], {"occurence": count * 100}) for node, count in node_occ.items()]
    edges = []
    for src_id in adj_list:
        for dst_info in adj_list[src_id]:
            dst_id, relation_id = dst_info
            edges.append((node_labels[src_id], node_labels[dst_id], {"relation": relations[relation_id]}))
    graph = {
        "nodes": nodes,
        "edges": edges
    }

    # related_articles = []
    # for related_article in event.related_articles:
    #     article_url = related_article['url']
    #     article_title = related_article['title']
    #     article_desc = related_article['description']
    #     related_articles.append(RELATED_ARTICLE_TEMPLATE.format(article_desc, article_title, article_url))
    related_facts = event.related_facts

    content = {
        "title": title,
        "excerpt": desc,
        "image_url": event.image,
        "image_prop": image.size[0] / image.size[1],
        "graph": graph,
        "related_facts": related_facts
    }
    return content