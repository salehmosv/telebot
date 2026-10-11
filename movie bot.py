import telebot
from telebot import types
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from thefuzz import process
from bson import ObjectId

load_dotenv()

Token = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(Token)

MONGO_URL = os.getenv("MONGO_URL")
client = MongoClient(MONGO_URL)

db = client["movies_saleh"]
collecction = db["videos"]

@bot.channel_post_handler(content_types=["video"])
def handle_channel_post(message):
    if message.chat.username == os.getenv("POST_CHANNEL"):
        collecction.insert_one({
            "file_id": message.video.file_id,
            "caption": message.caption
        })

@bot.message_handler(commands=['start'])
def start(message):
    welcome_text = (
        "👋 *Welcome to Movie Bot!*\n\n"
        "I Can Help You Find Your Favorite Movies And Videos."
        "Just send me the name of a movie, and I'll search our library for you!\n\n"
        "💡 *Tip:* Try searching for keywords like 'Action' 'Marvel', or 'Horror'."
    )
    bot.send_message(message.chat.id, welcome_text,parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def all_message(message):
    query = message.text

    cursor = collecction.find({"caption": {"$regex": query, "$options": "i"}}).limit(10)
    results = list(cursor)

    if not results:
        all_movies = list (collecction.find ({}, {"caption": 1, "_id": 1}))
        if all_movies:
            captions = [m["caption"] for m in all_movies]
            fuzzy_resultes = process.extract(query, captions, limit=5)

        for title, score in fuzzy_resultes:
            if score > 50:
                for movie in all_movies:
                    if movie["caption"] == title:
                        results.append(movie)
                        break

    if results:
        markup = types.InlineKeyboardMarkup()
        unique_results = {str(res["_id"]): res for res in results}.values()

        for movie in list(unique_results)[:10]:
            title = (movie["caption"][:40] + "...") if len(movie["caption"]) > 40 else movie["caption"]
            markup.add(types.InlineKeyboardButton(text=f"🎬 {title}", callback_data=f"vid_{movie['_id']}"))

        bot.send_message(
            message.chat.id,
            f"🔍 *Search Results for* '{query}':",
            reply_markup=markup,
            parse_mode="markdown"
        )   
    else:
        bot.send_message(message.chat.id, f"❌ No movies found matching '{query}'.try anither name!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("vid_"))
def send_video_callback(call):
    movie_id = call.data.split("_")[1]
    movie = collecction.find_one({"_id": ObjectId(movie_id)})

    if movie:
        bot.send_video(
            call.message.chat.id,
            movie["file_id"],
            caption=movie["caption"]
        )

        bot.answer_callback_query(call.id)
    else:
        bot.answer_callback_query(call.id, text="movie not found!")

bot.polling(non_stop=True)