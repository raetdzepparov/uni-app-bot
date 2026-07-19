🎓 Telegram Bot: Умный подбор университетов с ИИ
Бот для помощи абитуриентам в выборе высшего учебного заведения. Бот собирает данные пользователя (баллы ЕГЭ, желаемые профессии, города, бюджет), отправляет их на сервер, где нейросеть (Llama 3.3 70b через Groq API) анализирует информацию и подбирает топ-5 вузов с 3 подходящими программами в каждом. Результаты открываются в красивом Telegram Mini App.

🚀 Возможности
Пошаговый сбор данных (предметы, баллы, предпочтения).
Двухэтапный выбор профессии (сфера -> конкретная специальность).
ИИ-анализ соответствия сданных предметов выбранной специальности.
Генерация топ-5 вузов с разбивкой шансов на бюджет/платное.
Telegram Mini App (SPA) для просмотра результатов.
ИИ-суммаризатор реальных отзывов об университетах.
🛠 Технологии
Python 3.10+, Aiogram 3.x (Telegram Bot API)
FastAPI, Uvicorn (Backend сервер)
OpenAI API / Groq (LLM llama-3.3-70b-versatile)
HTML/CSS/JS (Telegram Web App)
aiohttp (асинхронные запросы)
⚙️ Установка и запуск
Клонируйте репозиторий:
git clone https://github.com/твой_ник/uni-mini-app-bot.gitcd uni-mini-app-bot
Создайте виртуальное окружение и установите зависимости:
bash

python -m venv venv
source venv/bin/activate  # Для Windows: venv\Scripts\activate
pip install -r requirements.txt
Создайте файл .env на основе .env.example и заполните его своими ключами:
bash

cp .env.example .env
Запустите сервер (в первом терминале):
bash

cd server
uvicorn server:app --reload
Запустите бота (во втором терминале):
bash

cd bot
python bot.py
Откройте бота в Telegram и отправьте команду /start.
