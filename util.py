from pathlib import Path
from PIL import Image
import base64
import io
import json

TARGET_SCORE = 21

def reset_feedback(user_feedback):
    user_feedback.clear()
    user_feedback.update({
        "regen_layout": False,
        "modify_layout": False,
        "regen_content": False,
        "regen_figures": False,
        "regen_graph": False,
        "lack_content": False,
        "inputs": {}
    })

def report_evaluation(evaluation, target_score):
    """Returns the infographic evaluation as a formatted string."""
    output = []
    output.append("Current infographic ratings and suggestions:")
    
    total_score = 0
    for criteria, details in evaluation.items():
        if isinstance(details, dict):
            score = details.get("score", 0)
            total_score += score
            calculation = details.get("calculation", "")
            
            output.append(f"\n{criteria.capitalize()}: {score} / 10")
            output.append(f"Summary of Calculations: {calculation}")

    output.append(f"\nOverall score: {total_score} / 30  |  Target score: {target_score} / 30")
    
    suggestions = evaluation.get("suggestions", [])
    if suggestions:
        output.append("\nSuggestions for Improvement:")
        for i, suggestion in enumerate(suggestions, 1):
            output.append(f"    {i}. {suggestion}")
    else:
        output.append("\nNo suggestions available.")

    return "\n".join(output), suggestions

def encode_img(img):
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes = img_bytes.getvalue()

    utf8_img = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:image/png;base64,{utf8_img}"

def get_eval_score(evaluation):
    return sum(metric.get("score", 0) for metric in evaluation.values() if isinstance(metric, dict))

def save_figures(figure_data, out_dir):
    figure_specs = []

    for idx, figure in enumerate(figure_data):
        f_name = f"figure_{idx}.png"
        out_path = out_dir / f_name 
        
        figure["figure"].save(out_path)
        spec = figure["specifications"]
        spec["path"] = f_name
        figure_specs.append(spec)
    
    return figure_specs

def save_graph(graph_img, graph_spec, out_dir):
    g_name = "graph.png"
    out_path = out_dir / g_name
    graph_img.save(out_path)
    graph_spec["path"] = g_name

def save_infographic(info_img, info_metadata, out_dir):
    i_name = "infographic.png"
    out_path = out_dir / i_name
    info_img.save(out_path)

    out_file = out_dir / "metadata.txt"
    with out_file.open('w') as f:
        json.dump(info_metadata, f, indent=2)

def save_html(html_code, out_dir):
    h_name = "layout.html"
    out_path = out_dir / h_name
    with out_path.open("w") as f:
        f.write(html_code)
    
    return str(out_path.resolve()).replace("\\", "/")
