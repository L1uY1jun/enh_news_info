from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image
import io
import json
import logging
import matplotlib
matplotlib.use("Agg") 
import matplotlib.pyplot as plt
import openai
import os
import seaborn as sns
import re
import warnings

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
logger = logging.getLogger(__name__)

EMPTY_IMAGE = Image.new("RGB", (1, 1), (0, 0, 0))
MAX_THREADS = min(5, os.cpu_count())

def generate_figures(stats_data, color_scheme):
    figures = []

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = {
            executor.submit(generate_figure, stats, color_scheme): stats
            for stats in stats_data
        }

        for future in as_completed(futures):
            stats = futures[future]
            img, desc = future.result()
            if img == EMPTY_IMAGE:
                continue

            width, height = img.size
            img_specifications = {
                "description": desc,
                "size": [width, height],
                "proportion": width / height
            }
            figures.append({"figure": img, "specifications": img_specifications})
    return figures

FIGURE_PROMPT = """
Your task is to analyze the given statistical data and generate appropriate Python code to visualize them, strictly following the given color scheme.
    
Here is the given information:
- Statistical Data: {stats}
- Color Scheme: {color}

Instructions:
1. Import all necessary modules.
2. Create a figure and assign it to a variable named `fig`.
3. Use the `seaborn` library to generate the plot.
4. Do not render or display the figure inside the code.
5. Ensure the visualization includes:
    - Clear axis labels
    - A descriptive title
    - A well-formatted layout
6. Apply a professional, polished aesthetic.
7. Do not include the description inside the plot.
8. Reduce the length of the X label/category by summarizing, shortening, or abbreviating when application.
    - Include a full name in the legend only if using an abbreviation (e.g., SD for Standard Deviation).
    - Avoid having the legend take up excessive space by adjusting its position or size, ensuring it does not clutter the figure.
9. Swap the X and Y axes when applicable to create a more informative or aesthetically pleasing plot.
10. If the provided data is insufficient for a meaningful visualization, apply appropriate enhancement techniques such as interpolation, smoothing, or data augmentation to improve the plot's appearance.
11. Provide a concise, one-sentence description of the expected figure, delimited with `|` at the end.
12. If the statistical data is unsuitable for visualization, return only the phrase: `UNPLOTTABLE_DATA`
"""

FIGURE_SYSTEM_PROMPT = """You are an expert at data visualization. Your task is to generate python code to visualize the statistical data as per the given instructions.

The outputted Python code must be delimited with triple backticks, and should not include any additional text, Markdown formatting, or escape characters.
"""

def generate_figure(stats, color_scheme):
    
    user_prompt = FIGURE_PROMPT.format(stats=stats, color=color_scheme)

    while True:
        completion = client.chat.completions.create(
            model='o3-mini',
            messages=[
                {"role": "system", "content": FIGURE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
        )

        response = completion.choices[0].message.content.strip()
        if "UNPLOTTABLE_DATA" in response:
            return EMPTY_IMAGE, ""

        desc = re.findall(r'\|(.*?)\|', response)
        desc = desc[0] if desc else "No description provided"
        vis_code = re.sub(r'(\|.*?\||^```(python)?|```)', '', response).strip()

        try:
            warnings.filterwarnings("ignore")
            
            exec_vars = {}
            exec(vis_code, exec_vars)
            fig = exec_vars.get("fig")

            if fig is not None:
                fig.tight_layout()

                with io.BytesIO() as buffer:
                    fig.savefig(buffer, bbox_inches='tight')
                    buffer.seek(0)
                    img = Image.open(buffer)
                    img = img.copy()

                plt.close(fig)
                return img, desc
        except Exception as e:
            logger.warning(f"Encountered execution error: {e}")
            logger.info("Retrying...")
        finally:
            warnings.filterwarnings("default")

# Testing-------------------------------------------------------
if __name__ == "__main__":
    with open("./enh_news_info/test/test_refined_data.txt", "r") as f:
        test_refined_info = json.load(f)

    stats_data = test_refined_info["key_facts"]["statistical"]
    color_scheme = test_refined_info["colors"]
    figure_data = generate_figures(stats_data, color_scheme)

    # specs = []
    # save_path = "./enh_news_info/test/test_img/"
    # for idx, figure in enumerate(figure_data):
    #     f_name = f"figure_{idx}.png"
    #     figure["figure"].save(save_path + f_name)

    #     specifiations = figure["specifications"]
    #     specifiations["path"] = f"./test_img/{f_name}"
    #     specs.append(specifiations)

    # specs_file_name = "figure_desc.txt"
    # with open(save_path + specs_file_name, "w") as f:
    #     json.dump(specs, f, indent=4)
