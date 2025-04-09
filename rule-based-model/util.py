from botocore.exceptions import ClientError
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from layout import *
import boto3
import logging
import matplotlib.pyplot as plt
import networkx as nx
import os
import pygraphviz
import random

load_dotenv()
generation_endpoint = os.environ.get("GENERATION_ENDPOINT")
aws_access_key_id = os.environ.get("AWS_S3_ACCESS_KEY")
aws_secret_access_key = os.environ.get("AWS_S3_SECRET_KEY")

def align_img_center(img, bounding_height, bounding_width, background_color='#FFFFFF'):
    width, height = img.size

    if height > bounding_height and width > bounding_width:
        return img
    offset_x = (bounding_width - width) // 2
    offset_y = (bounding_height - height) // 2
    
    centered_img = Image.new('RGB', (bounding_width, bounding_height), color=background_color)
    centered_img.paste(img, (offset_x, offset_y))
    return centered_img

def draw_optimal_text(
    text, max_font, min_font, max_height, max_width, 
    limited_text_wrap=False, font_color='#000000', background_color='#FFFFFF'
):
    dummy_img = Image.new('RGB', (1, 1), color=background_color)
    draw = ImageDraw.Draw(dummy_img, 'RGBA')

    words = text.split()
    for font_size in range(max_font, min_font - 1, -1):
        curr_words = []
        idx = 0

        while idx < len(words):
            curr_words.append(words[idx])
            idx += 1
            _, _, w, h = draw.multiline_textbbox((0, 0), rebuild_text(curr_words), font_size=font_size)

            if h > max_height:
                break
            if w > max_width and not (limited_text_wrap and should_skip_textwrap(curr_words[:-1], words[idx - 1:])):
                curr_words.pop()
                curr_words.append("\n")
                idx -= 1
        if idx >= len(words) and w <= max_width and h <= max_height:
            img = Image.new('RGB', (w, h), color=background_color)
            draw = ImageDraw.Draw(img, 'RGBA')
            draw.multiline_text((0, 0), rebuild_text(curr_words), fill=font_color, font_size=font_size)
            # Testing---------------------------------------
            # img.show()
            # ----------------------------------------------
            return img, h, w
    return None, None, None

def should_skip_textwrap(curr_words, rem_words):
    curr_lines = " ".join(curr_words).replace(" \n ", "\n").split("\n")
    estimated_max_line_len = max(len(line) for line in curr_lines)

    next_line = " ".join(rem_words)
    estimated_next_line_len = len(next_line)

    return estimated_next_line_len < 1 / 3 * estimated_max_line_len

def rebuild_text(words):
    result = []
    for w in words:
        if w == "\n":
            result.append(w)
        else:
            if result and not result[-1] == "\n":
                result.append(" ")
            result.append(w)
    return ''.join(result)

def resize_image(image, max_width, max_height):
    img_width, img_height = image.size
    width_height_ratio = img_width / img_height

    if width_height_ratio > 1:
        new_width = min(max_width, int(max_height * width_height_ratio))
        new_height = int(new_width / width_height_ratio)
    else:
        new_height = min(max_height, int(max_width / width_height_ratio))
        new_width = int(new_height * width_height_ratio)
    resized_image = image.resize((new_width, new_height))

    return resized_image

def draw_graph(graph_data, layout_prog='neato', edge_relation=True):
    G = nx.DiGraph()
    G.add_nodes_from(graph_data['nodes'])
    G.add_edges_from(graph_data['edges'])

    sizes = [d['occurence'] for n,d in G.nodes(data=True)]
    relations = {(u,v):d['relation'] for u,v,d in G.edges(data=True)}
    pos = nx.nx_agraph.graphviz_layout(G, prog=layout_prog)

    num_nodes = len(G.nodes())
    graph_width = max(8, num_nodes * 0.5)  # Minimum width is 8
    graph_height = max(6, num_nodes * 0.3)  # Minimum height is 6
    plt.figure(figsize=(graph_width, graph_height))

    nx.draw(
        G, pos=pos ,with_labels=True, node_size=sizes,
        node_color=S2LayoutRules.NODE_COLOR.value,
        font_size=S2LayoutRules.NODE_FONT_SIZE.value,
        font_color=S2LayoutRules.GRAPH_FONT_COLOR.value,
        font_family=S2LayoutRules.GRAPH_FONT_TYPE.value,
        edge_color=S2LayoutRules.EDGE_COLOR.value,
        width=S2LayoutRules.EDGE_WIDTH.value
    )
    if edge_relation:
        nx.draw_networkx_edge_labels(
            G, pos=pos, edge_labels=relations,
            font_size=S2LayoutRules.EDGE_FONT_SIZE.value,
            font_color=S2LayoutRules.GRAPH_FONT_COLOR.value,
            font_family=S2LayoutRules.GRAPH_FONT_TYPE.value
        )
    plt.margins(S2LayoutRules.GRAPH_MARGIN.value)
    # Testing---------------------------------------------------
    # plt.show()
    # ----------------------------------------------------------

    fig = plt.gcf()
    graph_img = convert_plt_to_img(fig)
    plt.clf()
    plt.close(fig)
    return graph_img

def convert_plt_to_img(fig):
    import io
    buffer = io.BytesIO()
    fig.savefig(buffer)
    buffer.seek(0)
    img = Image.open(buffer)
    return img

def convert_keys_str_to_int(d):
    new_d = {}
    for k in d:
        new_d[int(k)] = d[k]
    return new_d

def upload_fileobj(file_object, bucket, object_name):
    s3_client = boto3.client(
        's3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )
    try:
        response = s3_client.upload_fileobj(file_object, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True