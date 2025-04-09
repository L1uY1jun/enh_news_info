from datetime import datetime
from dotenv import load_dotenv
from layout_rules import GraphLayoutRules
from io import BytesIO
from openai import OpenAI
from PIL import Image
import ast
import io
import json
import matplotlib.pyplot as plt
import networkx as nx
import openai
import os
import pygraphviz
import re

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DEFAULT_LAYOUT_PARAMS = {
    "layout": "neato",
    "node_color": GraphLayoutRules.NODE_COLOR.value,
    "edge_color": GraphLayoutRules.EDGE_COLOR.value,
    "font_color": GraphLayoutRules.GRAPH_FONT_COLOR.value,
    "background": GraphLayoutRules.GRAPH_BACKGROUND_COLOR.value
}

FIG_MIN_WIDTH = 8
FIG_MIN_HEIGHT = 6

def generate_graph(graph_data, color_scheme, has_edge_relation):
    layout = generate_graph_layout(graph_data, color_scheme)
    return draw_graph(graph_data, layout, has_edge_relation)

GRAPH_PROMPT = """
Your task is to generate and return only the best suitable Graphviz layout program and an optimal color scheme for visualizing the provided graph data.

Instructions:
1. Select the Graphviz Layout
    - Choose a layout that ensures clarity by avoiding overlapping and clutter, particularly considering node names and edge connections. Iterate through the graph to gain a deeper understanding of its underlying structure and relationships.
    - If the graph is dense, use "neato", "sfdp", or "fdp".
    - If the graph has circular arrangements, use "circo".
    - If the graph has central nodes and radial patterns, use "twopi".
    - If the graph has a strict hierarchical order, use "dot".
2. Apply the Provided Color Scheme
    - Node colors: Select an appropriate color from the provided palette that aligns with the graph's data, overall theme, and categories represented by the nodes. Ensure the color enhances visual impact and clarity.
    - Edge colors: Select a color from the provided palette that complements well with the node colors, maintaining clear visibility and readability. Ensure the chosen color harmonize with the graph's data and overall theme.

Here is the given information:
- Graph Data: {graph}
- Color Palette: {color}

Output only the following in valid python dictionary format:
{{
    "layout": "chosen_graphviz_layout",
    "node_color": "hex_code",
    "edge_color": "hex_code"
}}
"""

GRAPH_SYSTEM_PROMPT = """
You are an expert graph layout analyst. Your task is to analyse graph data and determine the most suitable graphviz layout and optimal color scheme as per the given instructions.

The output must be a Python dictionary, delimited with triple backticks, and should not include any additional text, Markdown formatting, or escape characters.
"""

def generate_graph_layout(graph_data, color_scheme):
    
    user_prompt = GRAPH_PROMPT.format(graph=graph_data, color=color_scheme)

    while True:
        completion = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {"role": "system", "content": GRAPH_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            top_p=0.8
        )

        try:
            response = completion.choices[0].message.content.strip()
            layout = ast.literal_eval(re.sub(r"^```(python|json)?|```$", "", response).strip())
            break
        except (SyntaxError, ValueError) as e:
            print(f"[graph_generator] encountered error parsing graph layout: {e}")
            print("[graph_generator] retrying...")
    
    layout["font_color"] = color_scheme["primary"]["text"]
    layout["background"] = color_scheme["primary"]["background"]
    return layout

def draw_graph(graph_data, layout_params=DEFAULT_LAYOUT_PARAMS, edge_relation=True):
    G = nx.DiGraph()
    G.add_nodes_from(graph_data['nodes'])
    G.add_edges_from(graph_data['edges'])
    num_nodes = len(G.nodes())

    sizes = [d['relevance'] * max(100, (num_nodes * 12)) for n,d in G.nodes(data=True)]
    relations = {(u,v):d['relation'] for u,v,d in G.edges(data=True)}
    pos = nx.nx_agraph.graphviz_layout(G, prog=layout_params["layout"])

    graph_width = max(FIG_MIN_WIDTH, num_nodes * GraphLayoutRules.WIDTH_SCALING_FACTOR.value)
    graph_height = max(FIG_MIN_HEIGHT, num_nodes * GraphLayoutRules.HEIGHT_SCALING_FACTOR.value)
    plt.figure(figsize=(graph_width, graph_height))

    nx.draw(
        G, pos=pos,
        with_labels=True, node_size=sizes,
        node_color=layout_params["node_color"],
        font_size=GraphLayoutRules.NODE_FONT_SIZE.value,
        font_color=layout_params["font_color"],
        font_family=GraphLayoutRules.GRAPH_FONT_TYPE.value,
        edge_color=layout_params["edge_color"],
        width=GraphLayoutRules.EDGE_WIDTH.value
    )

    if edge_relation:
        nx.draw_networkx_edge_labels(
            G, pos=pos, edge_labels=relations,
            font_size=GraphLayoutRules.EDGE_FONT_SIZE.value,
            font_color=layout_params["font_color"],
            font_family=GraphLayoutRules.GRAPH_FONT_TYPE.value,
            bbox=dict(
                facecolor=layout_params["background"],
                edgecolor='none',
                pad=2
            )
        )
    plt.margins(GraphLayoutRules.GRAPH_MARGIN.value)

    fig = plt.gcf()
    buf = BytesIO()
    fig.savefig(buf, format='png', facecolor=layout_params["background"], 
                bbox_inches='tight', pad_inches=0)
    buf.seek(0)
    graph_img = Image.open(buf)
    plt.clf()
    plt.close(fig)

    width, height = graph_img.size
    specs = {
        "description": "The figure is a relationship graph describing key entites",
        "size": [width, height],
        "proportion": width / height
    }
    return graph_img, specs

def convert_plt_to_img(fig):
    buffer = io.BytesIO()
    fig.savefig(buffer)
    buffer.seek(0)
    img = Image.open(buffer)
    return img

# Testing-------------------------------------------------------
if __name__ == "__main__":
    with open("./Agent-Model-Infographic-Generator/test/test_refined_data.txt", "r") as f:
        refined_data = json.load(f)
        graph_data = refined_data["graph"]
        color_scheme = refined_data["colors"]

    graph_layout = generate_graph_layout(graph_data, color_scheme)
    graph_img, specs = draw_graph(graph_data, graph_layout)

    # graph_img.show()
    
    save_path = "./Agent-Model-Infographic-Generator/test/test_img/"
    img_file_name = "test_graph.png"
    graph_img.save(save_path + img_file_name)

    specs["path"] = f"./test_img/{img_file_name}"
    specs_file_name = "test_graph_desc.txt"
    with open(save_path + specs_file_name, "w") as f:
        json.dump(specs, f, indent=4)
