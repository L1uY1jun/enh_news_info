from dotenv import load_dotenv
from infogen import generate_infographic
from newspaper import Article
from newspaper import ArticleException
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import threading
import time

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEFAULT_GOAL = "To extract key data and insights from the news article for creating a clear, engaging infographic with context to help viewers easily understand the broader topic."

bot = telebot.TeleBot(BOT_TOKEN)

user_data = {}
chat_data = {}

def reset_user(chat_id):
    user_data.pop(chat_id, None)
    chat_data.pop(chat_id, None)

@bot.message_handler(commands=["start"])
def start(message):
    chat_id = message.chat.id
    sent = bot.send_message(chat_id=chat_id, text="Hello! Please send me a news article URL.")
    user_data[chat_id] = {}
    chat_data[chat_id] = {}
    bot.register_next_step_handler(sent, handle_url)

@bot.message_handler(commands=["cancel"])
def cancel(message):
    reset_user(message.chat.id)
    bot.send_message(message.chat.id, "The conversation has been canceled.")

def handle_url(message):
    chat_id = message.chat.id
    url = message.text.strip()

    try:
        article = Article(url)
        article.download()
        article.parse()

        user_data[chat_id]['url'] = url

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

    if chat_data[chat_id].get('skipped'):
        return

    user_data[chat_id]['goal'] = message.text.strip()

    del_msg_id = chat_data[chat_id].get('del_msg_id')
    bot.delete_message(chat_id, del_msg_id)
    threading.Thread(target=handle_info_gen, args=(chat_id,)).start()

@bot.callback_query_handler(func=lambda call: call.data == "skip")
def skip_goal(call):
    chat_id = call.message.chat.id

    user_data[chat_id]['goal'] = DEFAULT_GOAL
    chat_data[chat_id]['skipped'] = True

    bot.answer_callback_query(call.id)
    bot.delete_message(chat_id, call.message.message_id)
    threading.Thread(target=handle_info_gen, args=(chat_id,)).start()

def handle_info_gen(chat_id):
    url = user_data[chat_id]['url']
    goal = user_data[chat_id]['goal']

    bot.send_message(chat_id, f"Generating infographic based on:\nGoal: {goal}\nURL: {url}")
    
    # TODO: handle infographic generation here
    time.sleep(5)

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="yes", callback_data="satisfied"))
    markup.add(InlineKeyboardButton(text="no", callback_data="not-satisfied"))
    sent = bot.send_message(
        chat_id=chat_id,
        text="Finished generation! Please review the infographic.\nAre you satisfied with the current infographic or do you wish to terminate the session?",
        reply_markup=markup
    )
    chat_data[chat_id]['del_msg_id'] = sent.message_id

@bot.callback_query_handler(func=lambda call: call.data != 'skip')
def callback_inline(call):
    if call.message:
        chat_id = call.message.chat.id

        if call.data == "satisfied":
            del_msg_id = chat_data[chat_id].get('del_msg_id')
            bot.delete_message(chat_id, del_msg_id)
            bot.send_message(chat_id, "Thanks! Finishing now.")
        elif call.data == "not-satisfied":
            bot.send_message(chat_id, "Well, how can I improve it?")

def run_bot():
    print("Bot is running...")
    bot.infinity_polling()

if __name__ == '__main__':
    run_bot()
