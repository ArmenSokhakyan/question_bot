import asyncio
import logging
import sys
import random
import json
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

TOKEN = "7595011311:AAFRmsvGrXDPboyipgf7tLuWPBKShje6gSo"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

games = {
    -1002009840380: {"is_game_active": False, "player_scores": {}, "current_index": 0, "reserve_list": [], "timer_task": None},
    -1002372051836: {"is_game_active": False, "player_scores": {}, "current_index": 0, "reserve_list": [], "timer_task": None}
}

categories = {
    "mlbb": "Mobile Legends",
    "movies": "Фильмы",
    "series": "Сериалы",
    "anime": "Аниме"
}

with open("anime_list.json", "r", encoding="utf-8") as file:
    anime_list = json.load(file)

with open("mlbb.json", "r", encoding="utf-8") as file:
    mlbb_list = json.load(file)

with open("films.json", "r", encoding="utf-8") as file:
    films = json.load(file)

with open("serials.json", "r", encoding="utf-8") as file:
    serials = json.load(file)

def create_hint_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подсказка", callback_data="hint")]
    ])

# buttons with categories
def create_category_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="MLBB", callback_data="category_mlbb")],
        [InlineKeyboardButton(text="Фильмы", callback_data="category_movies")],
        [InlineKeyboardButton(text="Сериалы", callback_data="category_series")],
        [InlineKeyboardButton(text="Аниме", callback_data="category_anime")]
    ])

@dp.message(Command('kain_start'))
async def command_start_handler(message: Message) -> None:
    global games

    if message.chat.id not in games:
        await message.answer("Для использования этого бота обращаться к @GagikAbovyan")
        return

    await message.answer("Выберите категорию:", reply_markup=create_category_keyboard())

@dp.callback_query(lambda c: c.data.startswith("category_"))
async def handle_category(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    category_key = callback.data.split("_")[1]

    if category_key not in categories:
        await callback.answer("Неизвестная категория!")
        return

    if games.get(chat_id, {}).get("is_game_active"):
        await callback.answer("Игра уже идет! Завершите текущую игру перед выбором новой категории.")
        return

    category_name = categories[category_key]
    reserve_list = []
    if category_key == "anime":
        reserve_list = anime_list.copy()
    elif category_key == "mlbb":
        reserve_list = mlbb_list.copy()
    elif category_key == "movies":
        reserve_list = films.copy()
    elif category_key == "series":
        reserve_list = serials.copy()

    if not reserve_list:
        reserve_list = []

    games[chat_id] = {
        "is_game_active": True,
        "category": category_key,
        "current_index": 0,
        "reserve_list": reserve_list.copy(),
        "player_scores": {},
        "timer_task": None  # Инициализация timer_task
    }

    await callback.message.edit_text(
        f"Вы выбрали категорию: {category_name}. Игра начинается!",
        reply_markup=None
    )
    await callback.answer()

    await asyncio.sleep(1)
    await callback.message.answer(
        "Добро пожаловать. Я провожу игры. Давай проведем время вместе!"
    )

    if category_key:
        games[chat_id]["current_index"] = random.randrange(len(games[chat_id]["reserve_list"]))
        await send_anime_description(callback.message)
    else:
        await callback.message.answer("Список пуст.")

async def send_anime_description(message: Message):
    chat_id = message.chat.id

    if games[chat_id]["reserve_list"]:
        games[chat_id]["hint_given"] = False

        anime = games[chat_id]["reserve_list"][games[chat_id]["current_index"]]
        await message.answer(f"Угадай {categories[games[chat_id]['category']]} по описанию:\n{anime['description']}")

        # cancel prev timer
        if games[chat_id]["timer_task"]:
            games[chat_id]["timer_task"].cancel()

        # load new timer
        games[chat_id]["timer_task"] = asyncio.create_task(wait_for_answer(message))
    else:
        await message.answer(f"Все {categories[games[chat_id]['category']]} были угаданы! Игра завершена.")
        await stop(message)

async def wait_for_answer(message: Message):
    chat_id = message.chat.id
    await asyncio.sleep(60)  # Ждем 60 секунд перед подсказкой

    if games[chat_id]["is_game_active"] and not games[chat_id]["hint_given"]:
        games[chat_id]["hint_given"] = True  # Фиксируем, что подсказка уже была дана
        await message.answer("Время вышло! Вот подсказка:", reply_markup=create_hint_keyboard())

@dp.callback_query(F.data == "hint")
async def handle_hint(callback: CallbackQuery):
    chat_id = callback.message.chat.id

    if not games[chat_id]["is_game_active"]:
        return

    # take current answer
    if games[chat_id]["reserve_list"]:
        current_answer = games[chat_id]["reserve_list"][games[chat_id]["current_index"]]
        await callback.message.answer(
            f"Подсказка: Первые буквы названия — {current_answer['name'][:2]}..."
        )

    games[chat_id]["hint_given"] = True  # Устанавливаем флаг, чтобы подсказка не дублировалась
    await callback.answer()

@dp.message(Command('kain_stop'))
async def stop(message: Message):
    global games
    if message.chat.id not in games:
        await message.answer("Для использования этого бота обращаться к @GagikAbovyan")
        return
    games[message.chat.id]["is_game_active"] = False
    await message.answer(f"Каин больше с Вами не играет!")

    # send players rate
    if games[message.chat.id]["player_scores"]:
        ranking = sorted(games[message.chat.id]["player_scores"].items(), key=lambda x: x[1], reverse=True)
        ranking_message = "Рейтинг игроков:\n"
        for player, score in ranking:
            ranking_message += f"@{player}: {score} очков\n"
        await message.answer(ranking_message)
    else:
        if "category" in games[message.chat.id]:
            await message.answer(f"Не было угадано ни одного {categories[games[message.chat.id]["category"]]}.")
    games[message.chat.id]["player_scores"] = {}

@dp.message()
async def echo(message: Message) -> None:
    chat_id = message.chat.id

    if games[chat_id]["is_game_active"]:
        if games[chat_id]["reserve_list"]:
            answer = message.text.strip().lower()
            current_anime = games[chat_id]["reserve_list"][games[chat_id]["current_index"]]
            correct_answer = current_anime["name"].lower()

            if answer == correct_answer:
                player_name = message.from_user.username or message.from_user.first_name
                games[chat_id]["player_scores"][player_name] = games[chat_id]["player_scores"].get(player_name, 0) + 1
                await message.answer(f"@{player_name} Каин гордится тобой, правильно. 🎉")

                # Cancel timer if answer is correct
                if games[chat_id]["timer_task"]:
                    games[chat_id]["timer_task"].cancel()

                games[chat_id]["reserve_list"].pop(games[chat_id]["current_index"])

                if games[chat_id]["reserve_list"]:
                    games[chat_id]["current_index"] = random.randrange(len(games[chat_id]["reserve_list"]))
                    await send_anime_description(message)
                else:
                    await message.answer(f"Каин тобой доволен! Все ${categories[games[chat_id]["category"]]} угаданы.")
                    await stop(message)
        else:
            await stop(message)

async def main() -> None:
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
