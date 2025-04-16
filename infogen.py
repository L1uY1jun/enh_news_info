from datetime import datetime
from pathlib import Path
from info_extractor import extract_info
from info_retriever import retrieve_info
from info_manager import manage_info
from figure_generator import generate_figures
from graph_generator import generate_graph
from layout_generator import *
from renderer import render
from evaluator import evaluate
from util import *
import copy
import json
import logging

TARGET_SCORE = 21

DEFAULT_FEEDBACK = {
    "regen_layout": True,
    "modify_layout": False,
    "regen_content": True,
    "regen_figures": True,
    "regen_graph": True,
    "lack_content": False,
    "inputs": {}
}

logger = logging.getLogger(__name__)

def generate_infographic(article_url, user_request, out_dir):
    logger.info("Extracting and analyzing news content...")
    news_info = extract_info(article_url, user_request)
    processed_urls = set([article_url])

    logger.info("Searching for additional information...")
    retrieved_data = retrieve_info(news_info, processed_urls, user_request)

    logger.info("Processing retrieved data...")
    refined_data = manage_info(retrieved_data, user_request)

    title = refined_data["title"]
    key_facts = refined_data["key_facts"]["non_statistical"]
    stats_data = refined_data["key_facts"]["statistical"]
    graph_data = refined_data["graph"]
    color_scheme = refined_data["colors"]
    
    logger.info("Visualizing statistical data...")
    figure_data = generate_figures(stats_data, color_scheme)
    figure_specs = save_figures(figure_data, out_dir)

    logger.info("Generating graph...")
    graph, graph_spec = generate_graph(
        graph_data, color_scheme
    )
    save_graph(graph, graph_spec, out_dir)

    info_img, html_code, evaluation = process_infographic(
        title=title, 
        key_facts=key_facts, 
        figure_specs=figure_specs, 
        graph_spec=graph_spec, 
        color_scheme=color_scheme, 
        suggestions=user_request,
        out_dir=out_dir
    )

    info_metadata = {
        "url": article_url,
        "title": title,
        "facts": key_facts,
        "stats": stats_data,
        "graph": graph_data,
        "color_scheme": color_scheme,
        "f_specs": figure_specs,
        "g_specs": graph_spec,
        "html": html_code
    }
    
    save_infographic(info_img, info_metadata, out_dir)

    forward_metadata = {
        "article_url": article_url,
        "user_request": user_request,
        "processed_urls": processed_urls,
        "retrieved_data": retrieved_data,
        "refined_data": refined_data,
        "figure_data": figure_data,
        "graph": graph,
        "graph_spec": graph_spec,
        "html_code": html_code
    }

    return info_img, forward_metadata, evaluation

def modify_infographic(forward_metadata, user_feedback, out_dir):
    article_url = forward_metadata["article_url"]
    user_request = forward_metadata["user_request"]
    processed_urls = forward_metadata["processed_urls"]
    retrieved_data = forward_metadata["retrieved_data"]
    refined_data = forward_metadata["refined_data"]
    figure_data = forward_metadata["figure_data"]
    graph = forward_metadata["graph"]
    graph_spec = forward_metadata["graph_spec"]
    html_code = forward_metadata["html_code"]

    if user_feedback["regen_content"]:
        logger.info("Extracting and analyzing news content...")
        news_info = extract_info(article_url, user_request)
        processed_urls = set([article_url])

        logger.info("Searching for additional information...")
        retrieved_data = retrieve_info(news_info, processed_urls, user_request)

        logger.info("Processing retrieved data...")
        refined_data = manage_info(retrieved_data, user_request)
    elif user_feedback["lack_content"]:
        temp = {
            "title": retrieved_data["title"],
            "key_facts": {"statistical": [], "non_statistical": []},
            "key_entities": [],
            "additional_queries": user_feedback["inputs"]["additional_queries"]
        }

        logger.info("Searching for additional information...")
        extra_data = retrieve_info(temp, processed_urls, user_request, 15)
        retrieved_data["key_facts"]["statistical"].extend(extra_data["key_facts"]["statistical"])
        retrieved_data["key_facts"]["non_statistical"].extend(extra_data["key_facts"]["non_statistical"])
        retrieved_data["key_entities"].extend(extra_data["key_entities"])

        logger.info("Processing additional retrieved data...")
        refined_data = manage_info(retrieved_data, user_request)

    title = refined_data["title"]
    key_facts = refined_data["key_facts"]["non_statistical"]
    stats_data = refined_data["key_facts"]["statistical"]
    graph_data = refined_data["graph"]
    color_scheme = refined_data["colors"]
    
    if user_feedback["regen_figures"]:
        logger.info("Visualizing statistical data...")
        figure_data = generate_figures(stats_data, color_scheme)

    figure_specs = save_figures(figure_data, out_dir)

    if user_feedback["regen_graph"]:
        logger.info("Generating graph...")
        graph, graph_spec = generate_graph(
            graph_data, color_scheme
        )
    
    save_graph(graph, graph_spec, out_dir)

    info_img, html_code, evaluation = process_infographic(
        title=title, 
        key_facts=key_facts, 
        figure_specs=figure_specs, 
        graph_spec=graph_spec, 
        color_scheme=color_scheme, 
        suggestions=user_request,
        out_dir=out_dir,
        user_feedback=user_feedback, 
        html_code=html_code
    )

    info_metadata = {
        "url": article_url,
        "title": title,
        "facts": key_facts,
        "stats": stats_data,
        "graph": graph_data,
        "color_scheme": color_scheme,
        "f_specs": figure_specs,
        "g_specs": graph_spec,
        "html": html_code
    }
    
    save_infographic(info_img, info_metadata, out_dir)

    forward_metadata = {
        "article_url": article_url,
        "user_request": user_request,
        "processed_urls": processed_urls,
        "retrieved_data": retrieved_data,
        "refined_data": refined_data,
        "figure_data": figure_data,
        "graph": graph,
        "graph_spec": graph_spec,
        "html_code": html_code
    }

    return info_img, forward_metadata, evaluation

def process_infographic(
    title, key_facts, figure_specs, graph_spec, color_scheme, 
    suggestions, out_dir, user_feedback=DEFAULT_FEEDBACK, html_code=None
    ):
    info_color_scheme = color_scheme["primary"]
    
    mod_tries = 3
    mod_hist = {
        "infographic_hist": [],
        "eval_hist": []
    }

    while mod_tries > 0:
        if user_feedback["modify_layout"]:
            logger.info("Modifying current infographic...")
            suggestions = user_feedback["inputs"]["suggestions"]
            html_code = polish_layout(title, key_facts, figure_specs, graph_spec, html_code, suggestions)
        elif user_feedback["regen_layout"]:
            logger.info("Processing infographic...")
            html_code = generate_layout(title, key_facts, figure_specs, graph_spec, info_color_scheme, suggestions)
        
        if verify_html(html_code):
            html_path = save_html(html_code, out_dir)
            info_img = render(html_path)
            evaluation = evaluate(info_img)

            eval_score = get_eval_score(evaluation)
            if eval_score < TARGET_SCORE:
                if mod_tries > 0:
                    reset_feedback(user_feedback)
                    user_feedback["modify_layout"] = True
                    user_feedback["inputs"]["suggestions"] = evaluation["suggestions"]

                    mod_hist["infographic_hist"].append(info_img)
                    mod_hist["eval_hist"].append(evaluation)
                    mod_tries -= 1
                    logger.info(f"Generated layout failed evaluation. Refining... (Attempts remaining: {mod_tries})")
                    continue
                else:
                    logger.info("Generated layout failed evaluation. No refinement attempts remaining — returning best effort result.")
                    max_score_index = max(
                        range(len(mod_hist["eval_hist"])), 
                        key=lambda i: get_eval_score(mod_hist["eval_hist"][i])
                    )
                    info_img = mod_hist["infographic_hist"][max_score_index]
                    evaluation = mod_hist["eval_hist"][max_score_index]

            break
        else:
            logger.info("HTML verification failed. Retrying...")

    return info_img, html_code, evaluation
