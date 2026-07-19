import aiohttp
import asyncio
import logging
import os
from typing import Any, Dict, Optional

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import *
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEB_APP_DOMAIN = os.getenv("WEB_APP_DOMAIN", "https://raetdzepparov.github.io/uni-mini-app/").rstrip("/")
SERVER_URL = os.getenv("SERVER_URL", "http://127.0.0.1:8000")

if not BOT_TOKEN:
    raise ValueError("❌ Не указан BOT_TOKEN в файле .env!")

AVAILABLE_SUBJECTS = {
    "math": "Математика", "russian": "Русский язык", "physics": "Физика",
    "informatics": "Информатика", "chemistry": "Химия", "biology": "Биология",
    "history": "История", "social": "Обществознание",
}

BROAD_FIELDS = {
    "it": "💻 IT и Программирование",
    "medicine": "⚕️ Медицина (Врач)",
    "engineering": "⚙️ Инженерия и Техника",
    "economics": "📊 Экономика и Бизнес",
    "humanities": "📚 Гуманитарные науки",
    "teacher": "🎓 Образование (Учитель)",
    "unsure": "🤔 Не уверен(а)"
}

SPECIFIC_PROGRAMS = {
    "it": {
        "po_dev": "💻 Разработчик ПО", "web_dev": "🌐 Веб-разработчик", "ml": "🧠 ML-специалист / ИИ",
        "da": "📊 Аналитик данных", "cybersec": "🛡 Информационная безопасность", "game_dev": "🎮 Разработка игр",
        "sys_admin": "🖥 Сетевые технологии", "erp": "⚙️ ERP и 1С программирование", "unsure": "🤔 Не уверен(а)"
    },
    "medicine": {
        "general": "🩺 Лечебное дело", "dentist": "🦷 Стоматология", "pediatrics": "👶 Педиатрия",
        "pharmacy": "💊 Фармация", "med_bio": "🧬 Биоинженерия и биоинформатика", "clinical_psy": "🧠 Клиническая психология",
        "public_health": "🏥 Общественное здравоохранение", "nursing": "💉 Сестринское дело", "unsure": "🤔 Не уверен(а)"
    },
    "engineering": {
        "mech": "⚙️ Машиностроение", "robotics": "🤖 Робототехника", "civil": "🏗 Строительство",
        "aerospace": "✈ Авиа- и ракетостроение", "energy": "⚡ Энергетика и электротехника", "nanotech": "🔬 Нанотехнологии",
        "transport": "🚆 Транспортные системы", "architecture": "🏙 Архитектура", "unsure": "🤔 Не уверен(а)"
    },
    "economics": {
        "finance": "💰 Финансы и кредит", "management": "📈 Менеджмент", "marketing": "📣 Маркетинг и реклама",
        "accounting": "📒 Бухучет и аудит", "hr": "👥 Управление персоналом (HR)", "economics_world": "🌍 Мировая экономика",
        "business_inform": "💻 Бизнес-информатика", "logistics": "🚚 Логистика", "unsure": "🤔 Не уверен(а)"
    },
    "humanities": {
        "law": "⚖️ Юриспруденция", "linguistics": "🗣 Лингвистика и перевод", "psychology": "🧠 Психология",
        "sociology": "👥 Социология", "international": "🤝 Международные отношения", "history": "🏛 История",
        "media": "📰 Журналистика и PR", "design": "🎨 Дизайн", "unsure": "🤔 Не уверен(а)"
    },
    "teacher": {
        "history": "🏛 История", "math": "📐 Математика", "primary": "🧒 Начальные классы",
        "foreign_lang": "🗣 Иностранные языки", "russian_lang": "📖 Русский язык и литература",
        "informatics": "💻 Информатика и ИКТ", "physical_ed": "⚽ Физическая культура", "pedagogy": "🧠 Педагогика и психология", "unsure": "🤔 Не уверен(а)"
    }
}

class ApplicationForm(StatesGroup):
    waiting_for_subjects = State()
    waiting_for_score = State()
    waiting_for_broad_field = State()
    waiting_for_specific_program = State()
    waiting_for_open_questions = State()
    waiting_for_dormitory = State()
    waiting_for_tuition_type = State()
    waiting_for_max_tuition = State()
    waiting_for_cities = State()
    waiting_for_extra_wishes = State()
    waiting_for_confirmation = State()

router = Router(name="application_router")

def build_subjects_keyboard(selected_subjects: Dict[str, int]) -> InlineKeyboardMarkup:
    rows = []
    for key, label in AVAILABLE_SUBJECTS.items():
        if key in selected_subjects:
            btn_text = f"✅ {label}: {selected_subjects[key]}"
        else:
            btn_text = label
        rows.append([InlineKeyboardButton(text=btn_text, callback_data=f"subj:{key}")])
    rows.append([InlineKeyboardButton(text="➡️ Продолжить", callback_data="subj_done")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_choice_keyboard(options: Dict[str, str], callback_prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label, callback_data=f"{callback_prefix}:{key}")]
        for key, label in options.items()
    ])

async def finalize_form(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    subjects_scores = data.get("subjects_scores", {})
    total_score = sum(subjects_scores.values())

    payload = {
        "career_broad": data.get("career_broad", "Не указано"),
        "career_specific": data.get("career_specific", "Не указано"),
        "open_answers": data.get("open_answers", "Нет"),
        "subjects_scores": subjects_scores,
        "total_score": total_score,
        "dorm": data.get("needs_dormitory"),
        "tuition": data.get("tuition_type"),
        "max_budget": data.get("max_tuition_fee") or 0,
        "cities": data.get("cities", "Не указано"),
        "extra_wishes": data.get("extra_wishes", "Особых пожеланий нет")
    }

    await state.clear()
    error_msg = None
    session_id = None

    try:
        async with aiohttp.ClientSession() as http_session:
            async with http_session.post(f"{SERVER_URL}/api/generate-recommendations", json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("error"):
                        error_msg = result.get("message", "Ошибка подбора.")
                    else:
                        session_id = result.get("session_id")
    except Exception as e:
        logging.error(f"Failed to connect to server: {e}")
        error_msg = "Не удалось связаться с сервером."

    if error_msg:
        await message.answer(f"❌ <b>{error_msg}</b>\n\nПожалуйста, начните заново (/start) и выберите другую специальность или добавьте нужные предметы ЕГЭ.", parse_mode="HTML")
        return

    if not session_id:
        await message.answer("❌ Произошла неизвестная ошибка. Попробуйте позже.")
        return

    mini_app_url = f"{WEB_APP_DOMAIN}/?session_id={session_id}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎓 Посмотреть топ-5 вузов", web_app=WebAppInfo(url=mini_app_url))]
    ])

    await message.answer("✅ <b>ИИ проанализировал ваши данные!</b>\n\nМы подобрали 5 лучших университетов. Нажмите на кнопку ниже, чтобы открыть результат.", parse_mode="HTML", reply_markup=keyboard)

def parse_score(text: str) -> Optional[int]:
    text = text.strip()
    if not text.lstrip("-").isdigit():
        return None
    val = int(text)
    if 0 <= val <= 100:
        return val
    return None

def parse_tuition_fee(text: str) -> Optional[int]:
    text = text.strip()
    if not text.lstrip("-").isdigit():
        return None
    val = int(text)
    if val > 0:
        return val
    return None

@router.message(CommandStart())
@router.message(Command("reset"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.update_data(subjects_scores={})
    await message.answer("👋 Добро пожаловать!\n\n📝 Выберите предметы ЕГЭ. Когда закончите, нажмите «Продолжить».", reply_markup=build_subjects_keyboard({}))
    await state.set_state(ApplicationForm.waiting_for_subjects)

@router.callback_query(ApplicationForm.waiting_for_subjects, F.data.startswith("subj:"))
async def process_subject_selection(callback: CallbackQuery, state: FSMContext) -> None:
    subject_key = callback.data.split(":", 1)[1]
    await state.update_data(current_subject=subject_key)
    await callback.message.edit_text(f"📊 Введите балл (от 0 до 100) по предмету <b>{AVAILABLE_SUBJECTS.get(subject_key)}</b>:", parse_mode="HTML")
    await state.set_state(ApplicationForm.waiting_for_score)
    await callback.answer()

@router.callback_query(ApplicationForm.waiting_for_subjects, F.data == "subj_done")
async def process_subjects_done(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if not data.get("subjects_scores"):
        await callback.answer("❌ Выберите хотя бы один предмет!", show_alert=True)
        return
    await callback.message.edit_text("✅ Предметы сохранены!\n\n🌍 Выберите <b>общую сферу интересов</b>:", parse_mode="HTML", reply_markup=build_choice_keyboard(BROAD_FIELDS, "broad"))
    await state.set_state(ApplicationForm.waiting_for_broad_field)
    await callback.answer()

@router.message(ApplicationForm.waiting_for_score)
async def process_score_input(message: Message, state: FSMContext) -> None:
    score = parse_score(message.text or "")
    if score is None:
        await message.answer("❌ Неверный балл. Введите целое число от 0 до 100.")
        return
    data = await state.get_data()
    current_subject_key = data.get("current_subject")
    if not current_subject_key:
        return
    subjects_scores = data.get("subjects_scores", {})
    subjects_scores[current_subject_key] = score
    await state.update_data(subjects_scores=subjects_scores)
    await state.set_state(ApplicationForm.waiting_for_subjects)

    try:
        await message.delete()
    except:
        pass

    await message.answer("✅ Балл сохранен! Выберите следующий предмет или нажмите «Продолжить».", reply_markup=build_subjects_keyboard(subjects_scores))

@router.callback_query(ApplicationForm.waiting_for_broad_field, F.data.startswith("broad:"))
async def process_broad_field(callback: CallbackQuery, state: FSMContext) -> None:
    broad_key = callback.data.split(":", 1)[1]
    broad_label = BROAD_FIELDS.get(broad_key)
    await state.update_data(career_broad=broad_label)

    if broad_key == "unsure":
        await callback.message.edit_text("🤔 <b>Давайте подберем направление вместе!</b>\n\nКакие предметы вам даются легче всего и чем вы увлекаетесь в свободное время?", parse_mode="HTML")
        await state.set_state(ApplicationForm.waiting_for_open_questions)
    else:
        specs = SPECIFIC_PROGRAMS.get(broad_key, {})
        await callback.message.edit_text(f"✅ Сфера: <b>{broad_label}</b>\n\n🎯 Выберите <b>конкретную профессию</b>:", parse_mode="HTML", reply_markup=build_choice_keyboard(specs, "spec"))
        await state.set_state(ApplicationForm.waiting_for_specific_program)
    await callback.answer()

@router.callback_query(ApplicationForm.waiting_for_specific_program, F.data.startswith("spec:"))
async def process_specific_program(callback: CallbackQuery, state: FSMContext) -> None:
    spec_key = callback.data.split(":", 1)[1]
    data = await state.get_data()
    broad_label = data.get("career_broad")

    if spec_key == "unsure":
        await callback.message.edit_text(f"🤔 Понял вас!\n\nЧто именно вас привлекает в сфере «{broad_label}»? (Например: хочу создавать сайты, лечить людей, работать с цифрами и т.д.)", parse_mode="HTML")
        await state.set_state(ApplicationForm.waiting_for_open_questions)
    else:
        broad_key = [k for k, v in BROAD_FIELDS.items() if v == broad_label][0]
        spec_label = SPECIFIC_PROGRAMS[broad_key][spec_key]
        await state.update_data(career_specific=spec_label)
        await ask_dormitory(callback.message, state)
    await callback.answer()

@router.message(ApplicationForm.waiting_for_open_questions)
async def process_open_questions(message: Message, state: FSMContext) -> None:
    answer = message.text.strip()
    if not answer:
        await message.answer("❌ Пожалуйста, опишите ваши интересы текстом.")
        return
    await state.update_data(open_answers=answer, career_specific="Не уверен(а) (определяет ИИ)")
    await ask_dormitory(message, state)

async def ask_dormitory(message: Message, state: FSMContext) -> None:
    await state.set_state(ApplicationForm.waiting_for_dormitory)
    msg = message.message if isinstance(message, CallbackQuery) else message
    await msg.answer("🏠 Вам требуется <b>общежитие</b>?", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Да", callback_data="dorm:yes"), InlineKeyboardButton(text="❌ Нет", callback_data="dorm:no")]]))

@router.callback_query(ApplicationForm.waiting_for_dormitory, F.data.startswith("dorm:"))
async def process_dormitory(callback: CallbackQuery, state: FSMContext) -> None:
    needs_dorm = callback.data.split(":", 1)[1] == "yes"
    await state.update_data(needs_dormitory=needs_dorm)
    await callback.message.edit_text(f"✅ Общежитие: {'Да' if needs_dorm else 'Нет'}\n\n💰 Выберите <b>форму обучения</b>:", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆓 Только бюджет", callback_data="tuition:budget")],
        [InlineKeyboardButton(text="💳 Платное", callback_data="tuition:paid")],
        [InlineKeyboardButton(text="🔄 Любое", callback_data="tuition:both")],
    ]))
    await state.set_state(ApplicationForm.waiting_for_tuition_type)
    await callback.answer()

@router.callback_query(ApplicationForm.waiting_for_tuition_type, F.data.startswith("tuition:"))
async def process_tuition_type(callback: CallbackQuery, state: FSMContext) -> None:
    tuition_choice = callback.data.split(":", 1)[1]
    tuition_labels = {"budget": "Только бюджет", "paid": "Платное", "both": "Любое"}
    await state.update_data(tuition_type=tuition_labels.get(tuition_choice))
    if tuition_choice in ("paid", "both"):
        await callback.message.edit_text(f"💸 Укажите <b>макс. стоимость</b> в год (руб)?\n<i>Пример: 250000</i>", parse_mode="HTML")
        await state.set_state(ApplicationForm.waiting_for_max_tuition)
    else:
        await state.update_data(max_tuition_fee=None)
        await ask_cities(callback.message, state)
    await callback.answer()

@router.message(ApplicationForm.waiting_for_max_tuition)
async def process_max_tuition(message: Message, state: FSMContext) -> None:
    fee = parse_tuition_fee(message.text or "")
    if fee is None:
        await message.answer("❌ Неверная сумма. Введите положительное целое число.")
        return
    await state.update_data(max_tuition_fee=fee)
    await ask_cities(message, state)

async def ask_cities(message: Message, state: FSMContext) -> None:
    await state.set_state(ApplicationForm.waiting_for_cities)
    msg = message.message if isinstance(message, CallbackQuery) else message
    await msg.answer("🏙 В каком <b>городе</b> вы хотите учиться? \n<i>Можно перечислить несколько или написать «Любой».</i>", parse_mode="HTML")

@router.message(ApplicationForm.waiting_for_cities)
async def process_cities(message: Message, state: FSMContext) -> None:
    cities = message.text.strip()
    if not cities:
        await message.answer("❌ Пожалуйста, введите город или напишите «Любой».")
        return
    await state.update_data(cities=cities)
    await message.answer("💭 <b>Какие ещё пожелания есть по выбору университета?</b>\n\n<i>Например: «Тихий город», «Сильная IT-школа», «Военная кафедра». Если их нет — напишите «Нет».</i>", parse_mode="HTML")
    await state.set_state(ApplicationForm.waiting_for_extra_wishes)

@router.message(ApplicationForm.waiting_for_extra_wishes)
async def process_extra_wishes(message: Message, state: FSMContext) -> None:
    wishes = message.text.strip()
    if not wishes:
        wishes = "Нет особых пожеланий"
    await state.update_data(extra_wishes=wishes)

    data = await state.get_data()
    subjects = ", ".join([f"{AVAILABLE_SUBJECTS.get(k, k)}: {v}" for k, v in data.get("subjects_scores", {}).items()])

    max_fee = data.get("max_tuition_fee")
    if max_fee:
        tuition_str = f"{data.get('tuition_type')} (до {max_fee} руб)"
    else:
        tuition_str = data.get('tuition_type')

    summary_text = (
        "📋 <b>Проверьте ваши данные:</b>\n\n"
        f"👤 Сфера: {data.get('career_broad', 'Не указано')}\n"
        f"🎯 Профессия: {data.get('career_specific', 'Не указано')}\n"
        f"📝 Баллы ЕГЭ: {subjects} (Сумма: {sum(data.get('subjects_scores', {}).values())})\n"
        f"🏠 Общежитие: {'Да' if data.get('needs_dormitory') else 'Нет'}\n"
        f"💰 Обучение: {tuition_str}\n"
        f"🏙 Город: {data.get('cities')}\n"
        f"💭 Пожелания: {data.get('extra_wishes')}\n\n"
        "Всё верно?"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, подобрать вузы", callback_data="confirm:yes")],
        [InlineKeyboardButton(text="🔄 Заполнить заново", callback_data="confirm:no")]
    ])

    await message.answer(summary_text, parse_mode="HTML", reply_markup=keyboard)
    await state.set_state(ApplicationForm.waiting_for_confirmation)

@router.callback_query(ApplicationForm.waiting_for_confirmation, F.data.startswith("confirm:"))
async def process_confirmation(callback: CallbackQuery, state: FSMContext) -> None:
    choice = callback.data.split(":", 1)[1]
    if choice == "no":
        await state.clear()
        await cmd_start(callback.message, state)
    else:
        await callback.message.edit_text("⏳ ИИ анализирует ваши данные и подбирает лучшие вузы...\nЭто займет около 10-15 секунд.")
        await finalize_form(callback.message, state)
    await callback.answer()

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    if await state.get_state() is None:
        await message.answer("Нечего отменять. Отправьте /start, чтобы начать.")
        return
    await state.clear()
    await message.answer("🚫 Анкета отменена. Отправьте /start, чтобы начать заново.")

async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    try:
        await bot.get_me()
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_chat_menu_button(menu_button=MenuButtonDefault())
        await bot.set_my_commands([
            BotCommand(command="start", description="🚀 Начать подбор университета"),
            BotCommand(command="reset", description="🔄 Заполнить анкету заново"),
            BotCommand(command="cancel", description="❌ Отменить текущее действие")
        ])
        logging.info("Бот успешно запущен!")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())