from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image
from util import encode_img, report_evaluation
import ast
import openai
import os
import re

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EVALUATION_USER_PROMPT = """
Your task is to rigorously evaluate the provided infographic image using the quantitative metrics and scoring algorithms described below. Base your assessment on visual analysis principles and simulate relevant calculations to justify your scoring.

Instructions:
- For each criterion, assign a score from 1 to 10 using the scoring guidelines.
- Simulate and summarize the calculation steps based on the algorithm provided.
- Provide overall constructive suggestions for improvement.
    - Do not provide suggestions for metrics scoring 9 or above.
    - Suggestions must be actionable within design constraints: the visual figures themselves are fixed and cannot be altered. Improvements must come from regenerating layout or adding contextual elements.
    - Suggestions may also address visual appeal of infographic, such as color adjustments.

Evaluation Criteria:
1. Overlap (10 points)
   - Algorithm:
        a. Identify the bounding boxes of all visual elements.
        b. Calculate the Intersection over Union (IoU) for each unique element pair.
        c. Compute the average IoU across all pairs.
        d. A lower average IoU corresponds to less overlap and a higher score.
   - Scoring Guidelines:
        - 1-3: Significant overlap, elements obstruct or crowd one another.
        - 4-6: Moderate overlap, legibility or layout is partially compromised.
        - 7-8: Minimal overlap with some minor visual congestion.
        - 9-10: No overlap, a clean and well-spaced layout.
2. Alignment (10 points)
   - Algorithm:
        a. Determine the center coordinates (x, y) of each element.
        b. Compare these centers to a consistent alignment grid (e.g., median x or y values).
        c. Measure average deviation from the grid.
        d. Lower deviation reflects better alignment.
   - Scoring Guidelines:
        - 1-3: Elements are poorly aligned, no visual harmony or grid adherence.
        - 4-6: Some elements align, but inconsistencies affect balance.
        - 7-8: Mostly aligned with minor misplacements.
        - 9-10: Strong alignment, grid adherence is clear and consistent.
3. Spacing (10 points)
   - Algorithm:
        a. Measure edge-to-edge distances between adjacent elements.
        b. Calculate the variance of these distances.
        c. Optionally compare against ideal spacing thresholds (e.g., < 0.05 * page dimensions).
        d. Low variance indicates consistent, intentional spacing.
   - Scoring Guidelines:
        - 1-3: Large or uneven gaps, visual rhythm is disrupted.  
        - 4-6: Noticeable inconsistencies in spacing.  
        - 7-8: Generally consistent with slight irregularities.  
        - 9-10: Even, well-proportioned spacing throughout.

Output only the following in valid Python dictionary format:
{
    "overlap": {
        "score": ...,
        "calculation": "brief simulated calculation summary"
    },
    "alignment": {
        "score": ...,
        "calculation": "brief simulated calculation summary"
    },
    "spacing": {
        "score": ...,
        "calculation": "brief simulated calculation summary"
    },
    "suggestions": [
        "suggestion 1",
        "suggestion 2",
        ...
    ]
}
"""

EVALUATION_SYSTEM_PROMPT = """
You are an expert at infographic image analysis and evaluation. Your task is to analyze and score the infographic based on the given design metrics and provide constructive feedback.

The output must be a Python dictionary, delimited with triple backticks, and should not include any additional text, Markdown formatting, or escape characters.
"""

def evaluate(infographic_img):
    utf8_img = encode_img(infographic_img)

    while True:
        completion = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {"role": "system", "content": EVALUATION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": EVALUATION_USER_PROMPT},
                        {"type": "image_url", "image_url": {"url": utf8_img}}
                    ],
                }
            ],
            temperature=0.8,
            top_p=0.9
        )

        try: 
            response = completion.choices[0].message.content.strip()
            evaluation = ast.literal_eval(re.sub(r"^```(python|json)?|```$", "", response).strip())
            return evaluation
        except (SyntaxError, ValueError) as e:
            print(f"[evaluator] error parsing response: {e}")
            print("[evaluator] retrying...")

# Testing-------------------------------------------------------
if __name__ == "__main__":
    info_path = "./Agent-Model-Infographic-Generator/test/test_infographic.png"
    info_img = Image.open(info_path)

    evaluation = evaluate(info_img)
    report_evaluation(evaluation, 21)
