from datetime import datetime
from dotenv import load_dotenv
from figure_generator import generate_figure
from infogen import generate_infographic, modify_infographic
from io import BytesIO
from newspaper import Article
from newspaper import ArticleException
from pathlib import Path
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from util import *
import logging
import os
import sys
import telebot
import threading
import time

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logger = logging.getLogger(__name__)

DEFAULT_GOAL = "To extract key data and insights from the news article for creating a clear, engaging infographic with context to help viewers easily understand the broader topic."

ACTION_MENU = """How would you like to proceed? Please choose an action:
    1. Regenerate a section using existing data.
    2. Modify the infographic based on suggestions.
    3. Add more information by providing custom queries.
    4. Regenerate the entire infographic from scratch.
    5. Go back to the previous step.
Enter the number corresponding to your choice (1-5):"""

STEP_1_MENU = """Which section of the infographic would you like to be regenerated using existing data?
    1. Layout of infographic
    2. Figures only
    3. Graph only
    4. Return to the previous step.
Press the number corresponding to your choice (1-4)"""

STEP_1_2_MENU = """How would you like to regenerate the figures?
    1. Regenerate all figures
    2. Choose specific figures to regenerate
Press the number corresponding to your choice (1 or 2)"""

REWORK_FIGURE_MESSAGE = """
Please select the figures you'd like to regenerate by listing their numbers, separated by commas (e.g., 0, 3, 4, 5).
If you don't want to regenerate any figures, type: 'none'.
"""

STEP_2_MENU = """Please select how you would like to apply suggestions.
    1. Accept the generated suggestions.
    2. Enter your own custom suggestions.
    3. Return to the previous step.
Press the number corresponding to your choice (1-3) : """

TARGET_SCORE = 21

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}
chat_data = {}

OUTPUT_PATH = Path("./enh_news_info/out")

def reset_user(chat_id):
    user_data.pop(chat_id, None)
    chat_data.pop(chat_id, None)

@bot.message_handler(commands=["start"])
def start(message):
    out_dst = datetime.today().strftime('%Y_%m_%d_%H_%M')
    out_dir = OUTPUT_PATH / out_dst
    out_dir.mkdir(parents=True, exist_ok=True)

    chat_id = message.chat.id
    sent = bot.send_message(chat_id=chat_id, text="Hello! Please send me a news article URL.")
    user_data[chat_id] = {}
    user_data[chat_id]["user_feedback"] = {
        "regen_layout": False,
        "modify_layout": False,
        "regen_content": False,
        "regen_figures": False,
        "regen_graph": False,
        "lack_content": False,
        "inputs": {}
    }
    chat_data[chat_id] = {}
    chat_data[chat_id]["out_dir"] = out_dir
    chat_data[chat_id]["pass"] = 0
    bot.register_next_step_handler(sent, handle_url)

@bot.message_handler(commands=["shutdown"])
def shutdown(message):
    bot.send_message(message.chat.id, "Shutting down the bot...")
    sys.exit(0)

def handle_url(message):
    chat_id = message.chat.id
    url = message.text.strip()

    try:
        article = Article(url)
        article.download()
        article.parse()

        user_data[chat_id]["url"] = url

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("skip", callback_data="skip"))

        sent = bot.send_message(
            chat_id=chat_id,
            text="Got it! Now, optionally, describe what you'd like or a goal for the infographic. If you don't have one, click below to skip.",
            reply_markup=markup
        )
        chat_data[chat_id]['del_msg_id'] = sent.message_id
        bot.register_next_step_handler(sent, handle_goal)
    except ArticleException:
        sent = bot.send_message(chat_id, "That link doesn't seem valid. Double-check and try again.")
        return bot.register_next_step_handler(sent, handle_url)

def handle_goal(message):
    chat_id = message.chat.id

    if chat_data[chat_id].get("skipped"):
        return

    user_data[chat_id]["goal"] = message.text.strip()

    del_msg_id = chat_data[chat_id].get("del_msg_id")
    bot.delete_message(chat_id, del_msg_id)
    threading.Thread(target=handle_info_gen, args=(chat_id,), daemon=True).start()

@bot.callback_query_handler(func=lambda call: call.data == "skip")
def skip_goal(call):
    chat_id = call.message.chat.id

    user_data[chat_id]["goal"] = DEFAULT_GOAL
    chat_data[chat_id]["skipped"] = True

    bot.answer_callback_query(call.id)
    bot.delete_message(chat_id, call.message.message_id)
    threading.Thread(target=handle_info_gen, args=(chat_id,), daemon=True).start()

def handle_info_gen(chat_id):
    url = user_data[chat_id]["url"]
    goal = user_data[chat_id]["goal"]
    out_dir = chat_data[chat_id]["out_dir"]

    chat_data[chat_id]["pass"] += 1
    gen_pass = chat_data[chat_id]["pass"]
    info_dir = out_dir / f"gen_pass_{gen_pass:03}"
    info_dir.mkdir(parents=True, exist_ok=True)

    bot.send_message(chat_id, "Generating infographic...\nthis may take approximately 8 to 10 minutes. Thanks for your patience!")
    
    info_img, forward_metadata, evaluation = generate_infographic(url, goal, info_dir)
    report_msg, suggestions = report_evaluation(evaluation, TARGET_SCORE)

    chat_data[chat_id]["forward_metadata"] = forward_metadata
    user_data[chat_id]["gen_suggestions"] = suggestions

    bot.send_photo(
        chat_id=chat_id,
        photo=info_img,
        caption=report_msg
    )

    message = "Finished generation! Please review the infographic.\nAre you satisfied with the current infographic or do you wish to terminate the session?"
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("yes", callback_data="satisfied"),
        InlineKeyboardButton("no", callback_data="not-satisfied")]
    ])
    bot.send_message(chat_id=chat_id, text=message, reply_markup=markup)

def handle_info_mod(chat_id):
    forward_metadata = chat_data[chat_id]["forward_metadata"]
    user_feedback = user_data[chat_id]["user_feedback"]
    out_dir = chat_data[chat_id]["out_dir"]

    chat_data[chat_id]["pass"] += 1
    gen_pass = chat_data[chat_id]["pass"]
    info_dir = out_dir / f"gen_pass_{gen_pass:03}"
    info_dir.mkdir(parents=True, exist_ok=True)
    
    info_img, forward_metadata, evaluation = modify_infographic(forward_metadata, user_feedback, info_dir)
    report_msg, suggestions = report_evaluation(evaluation, TARGET_SCORE)

    chat_data[chat_id]["forward_metadata"] = forward_metadata
    user_data[chat_id]["gen_suggestions"] = suggestions
    
    bot.send_photo(
        chat_id=chat_id,
        photo=info_img,
        caption=report_msg
    )

    message = "Finished generation! Please review the infographic.\nAre you satisfied with the current infographic or do you wish to terminate the session?"
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("yes", callback_data="satisfied"),
        InlineKeyboardButton("no", callback_data="not-satisfied")]
    ])
    bot.send_message(chat_id=chat_id, text=message, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data != "skip")
def callback_inline(call):
    bot.answer_callback_query(call.id)
    if call.message:
        chat_id = call.message.chat.id

        if call.data == "satisfied":
            message = "Thanks! Finishing now."
            update_message(call, message)
        elif call.data in ["not-satisfied", "step_1_4", "step_2_3"]:
            action_markup = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(text="1", callback_data="action_1"),
                    InlineKeyboardButton(text="2", callback_data="action_2"),
                    InlineKeyboardButton(text="3", callback_data="action_3"),
                    InlineKeyboardButton(text="4", callback_data="action_4"),
                    InlineKeyboardButton(text="5", callback_data="action_5"),
                ]
            ])
            update_message(call, ACTION_MENU, action_markup)
        elif call.data == "action_1":
            step_1_markup = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(text="1", callback_data="step_1_1"),
                    InlineKeyboardButton(text="2", callback_data="step_1_2"),
                    InlineKeyboardButton(text="3", callback_data="step_1_3"),
                    InlineKeyboardButton(text="4", callback_data="step_1_4")
                ]
            ])
            update_message(call, STEP_1_MENU, step_1_markup)
        elif call.data == "step_1_1":
            message = "Regenerating infographic layout with same data..."
            update_message(call, message)
            reset_feedback(user_data[chat_id]["user_feedback"])
            user_data[chat_id]["user_feedback"]["regen_layout"] = True
            threading.Thread(target=handle_info_mod, args=(chat_id,), daemon=True).start()
        elif call.data == "step_1_2":
            step_1_2_markup = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(text="1", callback_data="regen_figures"),
                    InlineKeyboardButton(text="2", callback_data="figure_rework")
                ]
            ])
            update_message(call, STEP_1_2_MENU, step_1_2_markup)
        elif call.data == "regen_figures":
            message = "Regenerating figures with same data..."
            update_message(call, message)
            reset_feedback(user_data[chat_id]["user_feedback"])
            user_data[chat_id]["user_feedback"]["regen_figures"] = True
            user_data[chat_id]["user_feedback"]["regen_layout"] = True
            threading.Thread(target=handle_info_mod, args=(chat_id,), daemon=True).start()
        elif call.data == "figure_rework":
            message = "Here is a breakdown of the current figures:"
            update_message(call, message)
            handle_figure_rework(chat_id)
        elif call.data == "step_1_3":
            message = "Regenerating graph with same data..."
            update_message(call, message)
            reset_feedback(user_data[chat_id]["user_feedback"])
            user_data[chat_id]["user_feedback"]["regen_graph"] = True
            threading.Thread(target=handle_info_mod, args=(chat_id,), daemon=True).start()
        elif call.data == "action_2":
            step_2_markup = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(text="1", callback_data="step_2_1"),
                    InlineKeyboardButton(text="2", callback_data="step_2_2"),
                    InlineKeyboardButton(text="3", callback_data="step_2_3")
                ]
            ])
            update_message(call, STEP_2_MENU, step_2_markup)
        elif call.data == "step_2_1":
            message = "Regenerating infographic with generated suggestions..."
            update_message(call, message)
            reset_feedback(user_data[chat_id]["user_feedback"])
            user_data[chat_id]["user_feedback"]["modify_layout"] = True
            user_data[chat_id]["user_feedback"]["inputs"]["suggestions"] = user_data[chat_id]["gen_suggestions"]
            threading.Thread(target=handle_info_mod, args=(chat_id,), daemon=True).start()
        elif call.data == "step_2_2":
            bot.delete_message(chat_id=chat_id, message_id=call.message.message_id)
            user_data[chat_id]["user_feedback"]["modify_layout"] = True
            user_data[chat_id]["user_feedback"]["inputs"]["suggestions"] = []

            message = "Please enter your custom suggestions. Type 'done' when finished."
            sent = bot.send_message(chat_id=chat_id, text=message)
            bot.register_next_step_handler(sent, collect_custom_suggestions)
        elif call.data == "action_3":
            bot.delete_message(chat_id=chat_id, message_id=call.message.message_id)
            user_data[chat_id]["user_feedback"]["inputs"]["additional_queries"] = []
            user_data[chat_id]["user_feedback"]["lack_content"] = True
            user_data[chat_id]["user_feedback"]["regen_figures"] = True
            user_data[chat_id]["user_feedback"]["regen_graph"] = True
            user_data[chat_id]["user_feedback"]["regen_layout"] = True

            message = "Share any additional ideas you'd like to explore to enhance the infographic. Type 'done' when finished."
            sent = bot.send_message(chat_id=chat_id, text=message)
            bot.register_next_step_handler(sent, collect_custom_queries)
        elif call.data == "action_4":
            bot.delete_message(chat_id=chat_id, message_id=call.message.message_id)
            threading.Thread(target=handle_info_gen, args=(chat_id,), daemon=True).start()
        elif call.data == "action_5":
            message = "Finished generation! Please review the infographic.\nAre you satisfied with the current infographic or do you wish to terminate the session?"
            markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("yes", callback_data="satisfied"),
                InlineKeyboardButton("no", callback_data="not-satisfied")]
            ])
            update_message(call, message, markup)

def update_message(call, text, markup=None):
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        reply_markup=markup
    )

def handle_figure_rework(chat_id):
    figure_data = chat_data[chat_id]["forward_metadata"]["figure_data"]
    batch_size = 10
    total_figures = len(figure_data)

    for start in range(0, total_figures, batch_size):
        end = start + batch_size
        batch = figure_data[start:end]
        media_group = []

        for idx, fig in enumerate(batch, start=start):
            img = fig["figure"]
            desc = fig["specifications"]["description"]
            caption = f"Figure {idx}: {desc}"

            img_io = BytesIO()
            img.save(img_io, format='PNG')
            img_io.seek(0)

            media = InputMediaPhoto(media=img_io, caption=caption)
            media_group.append(media)

        bot.send_media_group(chat_id, media=media_group)

    sent = bot.send_message(chat_id, REWORK_FIGURE_MESSAGE)
    bot.register_next_step_handler(sent, handle_figure_regen)

def handle_figure_regen(message):
    chat_id = message.chat.id
    text = message.text.strip()
    forward_metadata = chat_data[chat_id]["forward_metadata"]
    num_figures = len(forward_metadata["figure_data"])
    refined_data = forward_metadata["refined_data"]

    try:
        raw_ids = [int(x.strip()) for x in text.split(",")]

        if any(fid < 0 or fid >= num_figures for fid in raw_ids):
            raise ValueError
        
        figure_ids = sorted(set(raw_ids))
    except ValueError:
        error_message = "Invalid input. Please enter numbers separated by commas (e.g. 1, 2, 3), within the valid range — or type 'none' to skip."
        sent = bot.send_message(chat_id=chat_id, text=error_message)
        return bot.register_next_step_handler(sent, handle_figure_regen)
    
    bot.send_message(chat_id, f"Regenerating figures: {', '.join(str(fid) for fid in figure_ids)}")

    stats_data = refined_data["key_facts"]["non_statistical"]
    color_scheme = refined_data["colors"]

    for idx in figure_ids:
        stats = stats_data[idx]
        img, desc = generate_figure(stats, color_scheme)

        width, height = img.size
        img_specifications = {
            "description": desc,
            "size": [width, height],
            "proportion": width / height
        }

        forward_metadata["figure_data"][idx]["figure"] = img
        forward_metadata["figure_data"][idx]["specifications"] = img_specifications
    
    threading.Thread(target=handle_info_mod, args=(chat_id,), daemon=True).start()

def collect_custom_suggestions(message):
    chat_id = message.chat.id
    text = message.text.strip()
    suggestions = user_data[chat_id]["user_feedback"]["inputs"]["suggestions"]

    if text.lower() == "done":
        if not suggestions:
            msg = bot.send_message(chat_id, "You must enter at least one suggestion before finishing.")
            return bot.register_next_step_handler(msg, collect_custom_suggestions)
        
        bot.send_message(chat_id, "Thanks! Your suggestions have been recorded.")
        return threading.Thread(target=handle_info_mod, args=(chat_id,), daemon=True).start()

    if text == "":
        msg = bot.send_message(chat_id, "Please enter something. Input cannot be empty.")
        return bot.register_next_step_handler(msg, collect_custom_suggestions)

    suggestions.append(text)
    msg = bot.send_message(chat_id, "Got it. Enter another suggestion, or type 'done' to finish.")
    bot.register_next_step_handler(msg, collect_custom_suggestions)

def collect_custom_queries(message):
    chat_id = message.chat.id
    text = message.text.strip()
    queries = user_data[chat_id]["user_feedback"]["inputs"]["additional_queries"]

    if text.lower() == "done":
        if not queries:
            msg = bot.send_message(chat_id, "You must enter at least one query before finishing.")
            return bot.register_next_step_handler(msg, collect_custom_queries)
        
        bot.send_message(chat_id, "Thanks! Your queries have been recorded.")
        return threading.Thread(target=handle_info_mod, args=(chat_id,), daemon=True).start()

    if text == "":
        msg = bot.send_message(chat_id, "Please enter something. Input cannot be empty.")
        return bot.register_next_step_handler(msg, collect_custom_queries)

    queries.append(text)
    msg = bot.send_message(chat_id, "Got it. Enter another query, or type 'done' to finish.")
    bot.register_next_step_handler(msg, collect_custom_queries)

def run_bot():
    logger.info("Bot is running...")
    bot.infinity_polling()

if __name__ == '__main__':
    run_bot()
