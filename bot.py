


import asyncio
import html
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN
from database import init_db, SessionLocal
from models import User
from sqlalchemy.future import select

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Состояния регистрации ---
class Register(StatesGroup):
    name = State()
    age = State()
    faculty = State()
    gender = State()
    target_gender = State()
    bio = State()
    photo = State()

# --- Главное меню ---
def main_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💞 Смотреть анкеты", callback_data="view_profiles")],
        [InlineKeyboardButton(text="👤 Моя анкета", callback_data="my_profile")],
        [InlineKeyboardButton(text="❤️ Лайки", callback_data="view_likes")]
    ])
    return kb

# --- START ---
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    async with SessionLocal() as session:
        user = await session.get(User, message.from_user.id)
        if user:
            await message.answer("С возвращением ❤️", reply_markup=main_menu())
            return

    await message.answer("Привет! Как тебя зовут?")
    await state.set_state(Register.name)

# --- Регистрация ---
@dp.message(Register.name)
async def reg_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Сколько тебе лет?")
    await state.set_state(Register.age)

@dp.message(Register.age)
async def reg_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Возраст должен быть числом.")
        return
    await state.update_data(age=int(message.text))
    await message.answer("Из какого ты факультета?")
    await state.set_state(Register.faculty)

@dp.message(Register.faculty)
async def reg_faculty(message: types.Message, state: FSMContext):
    await state.update_data(faculty=message.text)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🙋‍♂️ Я парень", callback_data="gender_male")],
        [InlineKeyboardButton(text="💁‍♀️ Я девушка", callback_data="gender_female")]
    ])
    await message.answer("Выбери свой пол:", reply_markup=kb)
    await state.set_state(Register.gender)

@dp.callback_query(Register.gender)
async def reg_gender(callback: types.CallbackQuery, state: FSMContext):
    gender = callback.data.split("_")[1]
    await state.update_data(gender=gender)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🙋‍♂️ Ищу парней", callback_data="target_male")],
        [InlineKeyboardButton(text="💁‍♀️ Ищу девушек", callback_data="target_female")]
    ])
    await callback.message.edit_text("Кого ты ищешь?", reply_markup=kb)
    await state.set_state(Register.target_gender)

@dp.callback_query(Register.target_gender)
async def reg_target(callback: types.CallbackQuery, state: FSMContext):
    target = callback.data.split("_")[1]
    await state.update_data(target_gender=target)
    await callback.message.edit_text("Расскажи немного о себе 📝")
    await state.set_state(Register.bio)

@dp.message(Register.bio)
async def reg_bio(message: types.Message, state: FSMContext):
    await state.update_data(bio=message.text)
    await message.answer("Отправь своё фото 📸")
    await state.set_state(Register.photo)

@dp.message(Register.photo, F.photo)
async def reg_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    async with SessionLocal() as session:
        new_user = User(
            id=message.from_user.id,
            name=data["name"],
            age=data["age"],
            faculty=data["faculty"],
            bio=data["bio"],
            gender=data["gender"],
            target_gender=data["target_gender"],
            photo_id=message.photo[-1].file_id,
            likes=[],
            dislikes=[],
            pending_likes=[]
        )
        session.add(new_user)
        await session.commit()
    await message.answer("Регистрация завершена ✅", reply_markup=main_menu())
    await state.clear()

# --- Главное меню ---
@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    await callback.message.answer("Главное меню 🏠", reply_markup=main_menu())

# --- Моя анкета ---
@dp.callback_query(F.data == "my_profile")
async def my_profile(callback: types.CallbackQuery):
    async with SessionLocal() as session:
        user = await session.get(User, callback.from_user.id)
        if not user:
            await callback.message.answer("Ты не зарегистрирован.")
            return
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Заполнить анкету заново", callback_data="re_register")],
            [InlineKeyboardButton(text="🗑 Удалить анкету", callback_data="delete_profile")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ])
        emoji = "🙋‍♂️" if user.gender == "male" else "💁‍♀️"
        caption = f"{emoji} <b>{user.name}</b>, {user.age}\n🎓 {user.faculty}\n\n📝 {user.bio}"
        await callback.message.answer_photo(user.photo_id, caption=caption, reply_markup=kb, parse_mode="HTML")

# --- Заполнить анкету заново ---
@dp.callback_query(F.data == "re_register")
async def re_register(callback: types.CallbackQuery, state: FSMContext):
    async with SessionLocal() as session:
        user = await session.get(User, callback.from_user.id)
        if user:
            await session.delete(user)
            await session.commit()

    await callback.message.answer("Начнём регистрацию заново! 💫")
    await start(callback.message, state)

# --- Удалить анкету ---
@dp.callback_query(F.data == "delete_profile")
async def delete_profile(callback: types.CallbackQuery):
    async with SessionLocal() as session:
        user = await session.get(User, callback.from_user.id)
        if user:
            await session.delete(user)
            await session.commit()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Заполнить анкету", callback_data="re_register")]
    ])
    await callback.message.answer("Ждём тебя снова 💫", reply_markup=kb)

# --- Смотреть анкеты ---
@dp.callback_query(F.data == "view_profiles")
async def view_profiles(callback: types.CallbackQuery):
    await show_next_profile(callback.from_user.id, callback.message)

# --- Показ анкет ---
async def show_next_profile(user_id, message):
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        result = await session.execute(select(User))
        all_users = result.scalars().all()
        seen = set((user.likes or []) + (user.dislikes or []))
        candidates = [u for u in all_users if u.id != user_id and u.gender == user.target_gender and u.id not in seen]

        if not candidates:
            await message.answer("Пока что новые анкеты закончились 😢", reply_markup=main_menu())
            return

        profile = candidates[0]
        emoji = "🙋‍♂️" if profile.gender == "male" else "💁‍♀️"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❤️", callback_data=f"profile_like_{profile.id}"),
             InlineKeyboardButton(text="👎", callback_data=f"profile_dislike_{profile.id}")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
        ])
        caption = f"{emoji} <b>{profile.name}</b>, {profile.age}\n🎓 {profile.faculty}\n\n📝 {profile.bio}"
        await message.answer_photo(profile.photo_id, caption=caption, reply_markup=kb, parse_mode="HTML")

# --- Раздел "Лайки" ---
@dp.callback_query(F.data == "view_likes")
async def view_likes_callback(callback: types.CallbackQuery):
    await view_likes(callback)

async def view_likes(callback, remove_current=False):
    async with SessionLocal() as session:
        user = await session.get(User, callback.from_user.id)
        likes_list = user.pending_likes or []

        if not likes_list:
            await callback.message.answer("❤️ Пока больше никто не лайкнул твою анкету.", reply_markup=main_menu())
            return

        target_id = likes_list[0]
        target = await session.get(User, target_id)
        emoji = "🙋‍♂️" if target.gender == "male" else "💁‍♀️"

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❤️ Взаимно", callback_data=f"like_{target.id}")],
            [InlineKeyboardButton(text="👎 Дизлайк", callback_data=f"dislike_{target.id}")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
        ])
        caption = f"{emoji} <b>{target.name}</b>, {target.age}\n🎓 {target.faculty}\n\n📝 {target.bio}"
        await callback.message.answer_photo(target.photo_id, caption=caption, reply_markup=kb, parse_mode="HTML")

        if remove_current:
            likes_list.pop(0)
            user.pending_likes = likes_list
            await session.commit()

# --- Лайк ---
@dp.callback_query(lambda c: c.data.startswith("like_") or c.data.startswith("profile_like_"))
async def like_user(callback: types.CallbackQuery):
    target_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    is_profile = callback.data.startswith("profile_like_")

    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        target = await session.get(User, target_id)

        if target_id not in (user.likes or []):
            user.likes = list(user.likes or []) + [target_id]

        # --- Взаимный лайк ---
        if user_id in (target.likes or []):
            user.pending_likes = [uid for uid in (user.pending_likes or []) if uid != target_id]
            target.pending_likes = [uid for uid in (target.pending_likes or []) if uid != user_id]
            await session.commit()

            # --- ссылки ---
            try:
                target_chat = await bot.get_chat(target_id)
                target_link = f"https://t.me/{target_chat.username}" if target_chat.username else f"tg://user?id={target_id}"
            except:
                target_link = f"tg://user?id={target_id}"

            try:
                user_chat = await bot.get_chat(user_id)
                user_link = f"https://t.me/{user_chat.username}" if user_chat.username else f"tg://user?id={user_id}"
            except:
                user_link = f"tg://user?id={user_id}"

            # --- Для target ---
            emoji_user = "🙋‍♂️" if user.gender == "male" else "💁‍♀️"
            caption = (
                f"💘 Тебя взаимно лайкнул {emoji_user} <a href=\"{user_link}\">{html.escape(user.name)}</a>!\n\n"
                f"<b>{html.escape(user.name)}</b>, {user.age}\n🎓 {html.escape(user.faculty)}\n\n📝 {html.escape(user.bio)}"
            )
            kb_full = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💬 Написать", url=user_link)],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
            ])
            await bot.send_photo(target_id, user.photo_id, caption=caption, reply_markup=kb_full, parse_mode="HTML")

            # --- Для user ---
            msg = f"🎉 Поздравляем!!! Вперед пиши: <a href=\"{target_link}\">{html.escape(target.name)}</a>"
            kb_short = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💬 Написать", url=target_link)],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
            ])
            await bot.send_message(user_id, msg, reply_markup=kb_short, parse_mode="HTML")
        else:
            if user_id not in (target.pending_likes or []):
                target.pending_likes = list(target.pending_likes or []) + [user_id]
                await session.commit()
                try:
                    await bot.send_message(target_id, "💌 Тебя кто-то лайкнул! Проверь раздел «Лайки» ❤️")
                except:
                    pass

    await callback.answer("Лайк 💞")

    if is_profile:
        await show_next_profile(user_id, callback.message)
    else:
        await view_likes(callback, remove_current=True)

# --- Дизлайк ---
@dp.callback_query(lambda c: c.data.startswith("dislike_") or c.data.startswith("profile_dislike_"))
async def dislike_user(callback: types.CallbackQuery):
    target_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    is_profile = callback.data.startswith("profile_dislike_")

    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if target_id not in (user.dislikes or []):
            user.dislikes = list(user.dislikes or []) + [target_id]

        if user.pending_likes:
            user.pending_likes = [uid for uid in user.pending_likes if uid != target_id]
        await session.commit()

    await callback.answer("Пропущено 👎")

    if is_profile:
        await show_next_profile(user_id, callback.message)
    else:
        await view_likes(callback, remove_current=True)

# --- MAIN ---
async def main():
    print("🚀 Бот запущен...")
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
