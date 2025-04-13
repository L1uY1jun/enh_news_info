from pathlib import Path
from PIL import Image
import base64
import io
import json

TARGET_SCORE = 21

# IDLE_PENDING = (False, False)
# IDLE_FINISHED = (False, True)
# ACTIVE_PENDING = (True, False)

# def get_user_feedback(info_img, evaluation, user_feedback, target_score):
#     """Gathers user feedback on an infographic and returns their preferences."""
#     reset_feedback(user_feedback)

#     info_img.show()
#     suggestions = report_evaluation(evaluation, target_score)

#     finished = False
#     try:
#         while not finished:
#             finished = user_feedback["end_session"] = get_end_session_response()
#             interacting = True
#             while interacting and not finished:
#                 interacting, finished = handle_action_selection(user_feedback, suggestions)
#     except ValueError as e:
#         print(e)
#         user_feedback["end_session"] = True

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

# def get_end_session_response():
#     end_session = prompt_input(
#         "Are you satisfied with the current infographic or do you wish to terminate the session? (y/n): ", 
#         {"y", "n", "yes", "no"}
#     )
#     return end_session == "y" or end_session == "yes"

# def handle_action_selection(user_feedback, suggestions):
#     next_step = prompt_input(ACTION_MENU, {"1", "2", "3", "4", "5"})
    
#     if next_step == "1":
#         return handle_step_1(user_feedback)
#     elif next_step == "2":
#         return handle_step_2(user_feedback, suggestions)
#     elif next_step == "3":
#         return handle_step_3(user_feedback)
#     elif next_step == "4":
#         return handle_step_4(user_feedback)
#     else:
#         return IDLE_PENDING

# def handle_step_1(user_feedback):
#     s1_option = STEP_1_MAPPING[prompt_input(STEP_1_MENU, {"1", "2", "3", "4"})]
#     if s1_option == "regen_graph":
#         edge_relation = prompt_input(
#             "Do you want to keep the edge relations? (y/n): ",
#             {"y", "n", "yes", "no"}
#         )
#         user_feedback["inputs"]["has_edge_relation"] = edge_relation == "y" or edge_relation == "yes"
#     elif s1_option == "return":
#         return ACTIVE_PENDING
#     user_feedback[s1_option] = True
#     return IDLE_FINISHED

# def handle_step_2(user_feedback, suggestions):
#     user_feedback["modify_html"] = True
#     s2_option = prompt_input(STEP_2_MENU, {"1", "2", "3"})
#     if s2_option == "3":
#         return ACTIVE_PENDING
#     user_feedback["inputs"]["suggestions"] = (
#         suggestions if s2_option == "1"
#         else get_custom_inputs(
#             "Please enter your custom suggestions. Type 'done' when finished.", 
#             "Your suggestion"
#         )
#     )
#     return IDLE_FINISHED

# def handle_step_3(user_feedback):
#     user_feedback["lack_content"] = True
#     user_feedback["inputs"]["additional_queries"] = get_custom_inputs(
#         "Share any additional ideas you'd like to explore to enhance the infographic. Type 'done' when finished.",
#         "Next query"
#     )
#     user_feedback["regen_figures"] = True
#     user_feedback["regen_graph"] = True
#     return IDLE_FINISHED

# def handle_step_4(user_feedback):
#     user_feedback["regen_content"] = True
#     user_feedback["regen_figures"] = True
#     user_feedback["regen_graph"] = True
#     return IDLE_FINISHED

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

# def prompt_input(prompt, valid_options, attempts=3):
#     """Gets user input, ensuring it is within valid options, with limited retries."""
#     options_string = "/".join(sorted(valid_options))
#     while attempts >= 0:
#         user_input = input(prompt).strip().lower()
#         if user_input in valid_options:
#             return user_input
#         print(f"Invalid input. Please enter one of {options_string}. {attempts} attempt(s) left.")
#         attempts -= 1

#     raise ValueError("Too many invalid attempts. Terminating process.")

# def get_custom_inputs(prompt_message, input_label):
#     """Collects custom inputs from the user until they type 'done'."""
#     custom_inputs = []
#     print(prompt_message)
#     while True:
#         user_input = input(f"{input_label}: ").strip()
#         if user_input == "":
#             print("Please enter something. Input cannot be empty.")
#             continue
#         if user_input.lower() == "done":
#             if not custom_inputs:
#                 print("You must enter at least one input before finishing.")
#                 continue
#             break
#         custom_inputs.append(user_input)
#     return custom_inputs

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

# if __name__ == "__main__":
#     info_path = "./Agent-Model-Infographic-Generator/test/test_infographic.png"
#     info_img = Image.open(info_path)

#     test_eval = {
#         "Content": {
#             "score": 8,
#             "suggestions": [
#                 "Include more statistics to support the key points."
#             ]
#         },
#         "Clarity": {
#             "score": 7,
#             "suggestions": [
#                 "Simplify the language in the introduction."
#             ]
#         },
#         "Readability": {
#             "score": 9,
#             "suggestions": [
#                 "Increase font size in key sections for better readability."
#             ]
#         },
#         "Visual Appeal": {
#             "score": 7,
#             "suggestions": [
#                 "Add more color contrast between sections for better separation."
#             ]
#         }
#     }

#     user_feedback = {
#         "end_session": False,
#         "modify_html": False,
#         "regen_info": False,
#         "regen_content": True,
#         "regen_figures": True,
#         "regen_graph": True,
#         "lack_content": False,
#         "inputs": {}
#     }

#     target_score = 30

#     get_user_feedback(info_img, test_eval, user_feedback, target_score)
#     print(user_feedback)
