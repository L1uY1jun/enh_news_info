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

OUTPUT_PATH = Path("./Agent-Model-Infographic-Generator/out")
TARGET_SCORE = 21

DEFAULT_GOAL = "To extract key data and insights from the news article for creating a clear, engaging infographic with context to help viewers easily understand the broader topic."

user_feedback = {
    "end_session": False,
    "modify_html": False,
    "regen_info": False,
    "regen_content": True,
    "regen_figures": True,
    "regen_graph": True,
    "lack_content": False,
    "inputs": {}
}

def generate_infographic(article_url, user_request=None, user_feedback=user_feedback):
    out_dst = datetime.today().strftime('%Y_%m_%d_%H_%M')
    out_dir = OUTPUT_PATH / out_dst
    out_dir.mkdir(parents=True, exist_ok=True)

    user_request = user_request or DEFAULT_GOAL

    while not user_feedback["end_session"]:
        if user_feedback["regen_content"]:
            print("Extracting and analyzing news content...")
            news_info = extract_info(article_url, user_request)
            processed_urls = set([article_url])

            print("Searching for additional information...")
            retrieved_data = retrieve_info(news_info, processed_urls, user_request)

            print("Processing retrieved data...")
            refined_data = manage_info(retrieved_data, user_request)
        elif user_feedback["lack_content"]:
            temp = {
                "title": news_info["title"],
                "key_facts": {"statistical": [], "non_statistical": []},
                "key_entities": [],
                "additional_queries": user_feedback["inputs"]["additional_queries"]
            }

            print("Searching for additional information...")
            extra_data = retrieve_info(temp, user_request, 15)
            retrieved_data["key_facts"]["statistical"].extend(extra_data["key_facts"]["statistical"])
            retrieved_data["key_facts"]["non_statistical"].extend(extra_data["key_facts"]["non_statistical"])
            retrieved_data["key_entities"].extend(extra_data["key_entities"])

            print("Processing additional retrieved data...")
            refined_data = manage_info(retrieved_data, user_request)

        title = refined_data["title"]
        key_facts = refined_data["key_facts"]["non_statistical"]
        stats_data = refined_data["key_facts"]["statistical"]
        graph_data = refined_data["graph"]
        color_scheme = refined_data["colors"]
        
        if user_feedback["regen_figures"]:
            print("Visualizing statistical data...")
            figure_data = generate_figures(stats_data, color_scheme)
            figure_specs = save_figures(figure_data, out_dir)
        if user_feedback["regen_graph"]:
            print("Generating graph...")
            graph, graph_spec = generate_graph(
                graph_data, color_scheme, user_feedback["inputs"].get("has_edge_relation", True)
            )
            save_graph(graph, graph_spec, out_dir)

        info_img, html_code = process_infographic(
            out_dir, key_facts, figure_specs, graph_spec, 
            title, color_scheme, user_request, user_feedback
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
        out_file = out_dir / 'metadata.txt'
        with out_file.open('w') as f:
            json.dump(info_metadata, f, indent=2)
        
        save_infographic(info_img, out_dir)

def process_infographic(out_dir, title, key_facts, figure_specs, graph_spec, color_scheme, suggestions, user_feedback):
    suggestions = suggestions or "No suggestions yet"
    info_color_scheme = color_scheme["primary"]
    user_feedback["regen_info"] = True
    
    mod_tries = 3
    mod_hist = {
        "infographic_hist": [],
        "eval_hist": []
    }

    while user_feedback["regen_info"] or user_feedback["modify_html"]:
        if user_feedback["modify_html"]:
            print("Modifying current infographic...")
            suggestions = user_feedback["inputs"]["suggestions"]
            html_code = polish_layout(title, key_facts, figure_specs, graph_spec, html_code, suggestions)
        else:
            print("Processing infographic...")
            html_code = generate_layout(title, key_facts, figure_specs, graph_spec, info_color_scheme, suggestions)
        
        if verify_html(html_code):
            html_path = save_html(html_code, out_dir)
            info_img = render(html_path)
            evaluation = evaluate(info_img)

            eval_score = get_eval_score(evaluation)
            if eval_score < TARGET_SCORE:
                if mod_tries > 0:
                    reset_feedback(user_feedback)
                    user_feedback["modify_html"] = True
                    user_feedback["inputs"]["suggestions"] = evaluation["suggestions"]

                    mod_hist["infographic_hist"].append(info_img)
                    mod_hist["eval_hist"].append(evaluation)
                    mod_tries -= 1
                    print(f"Generated layout failed evaluation. Refining... (Attempts remaining: {mod_tries})")
                    continue
                else:
                    print("Generated layout failed evaluation. No refinement attempts remaining — returning best effort result.")
                    max_score_index = max(
                        range(len(mod_hist["eval_hist"])), 
                        key=lambda i: get_eval_score(mod_hist["eval_hist"][i])
                    )
                    info_img = mod_hist["infographic_hist"][max_score_index]
                    evaluation = mod_hist["eval_hist"][max_score_index]

            get_user_feedback(info_img, evaluation, user_feedback, TARGET_SCORE)

            mod_tries = 3
            mod_hist = {
                "infographic_hist": [],
                "eval_hist": []
            }
        else:
            print("HTML verification failed. Retrying...")

    return info_img, html_code

if __name__ == "__main__":
    article_url = "https://www.channelnewsasia.com/commentary/singapore-indonesia-floating-solar-farm-batam-clean-energy-electricity-4737861"

    info_img = generate_infographic(article_url)
    info_img.show()
