import uvicorn
import os
import logging
import json
import uuid
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import AsyncOpenAI

app = FastAPI(title="University Bot API", version="7.0 Multi-program")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

CACHE: Dict[str, Any] = {}
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_MODEL = os.getenv("LLM_MODEL")

class UserRequest(BaseModel):
    career_broad: str
    career_specific: str
    open_answers: str
    subjects_scores: Dict[str, int]
    total_score: int
    dorm: bool
    tuition: str
    max_budget: int
    cities: str
    extra_wishes: str

class ReviewRequest(BaseModel):
    university_name: str
    specialty_name: str

async def get_llm_recommendations(req: UserRequest) -> Dict[str, Any]:
    subjects_str = ", ".join([f"{k}: {v}" for k, v in req.subjects_scores.items()])

    prompt = f"""Ты — строгий эксперт по поступлению в ВУЗы России. 
    Твоя задача — подобрать РОВНО 5 лучших реальных университетов, на которые пользователь сможет поступить. 
    Внутри каждого вуза нужно подобрать РОВНО 3 разные программы (специальности), которые подходят под запрос абитуриента.

    Данные абитуриента:
    - Общая сфера: {req.career_broad}
    - Конкретная профессия: {req.career_specific}
    - Открытые ответы: {req.open_answers}
    - Сданные предметы ЕГЭ: {subjects_str}
    - Суммарный балл: {req.total_score}
    - Нуждается в общежитии: {'Да' if req.dorm else 'Нет'}
    - Форма обучения: {req.tuition} {f'(Макс. бюджет: {req.max_budget} руб/год)' if req.max_budget > 0 else ''}
    - Желаемые города: {req.cities}
    - Доп. пожелания: {req.extra_wishes}

    ПРАВИЛА АНАЛИЗА:
    1. СООТВЕТСТВИЕ СПЕЦИАЛЬНОСТИ: Программы должны МАКСИМАЛЬНО совпадать с тем, что выбрал пользователь.
    2. РАСЧЕТ ШАНСОВ: Для КАЖДОЙ программы рассчитай шанс на бюджет и шанс на платное. Они должны различаться (баллы на платное всегда ниже). Сравни балл абитуриента ({req.total_score}) с типичными проходными баллами этих программ. Для расчёта шансов нужно брать баллы, которые были для поступления в прошлых 2х годах в этом университете на эту специальность, предположить какие будут баллы в этом году исходя из прошлогодних и уже высчитанные баллы сравнить с теми, что дал пользователь
    3. АКТУАЛЬНОСТЬ: Стоимость обучения должна быть достоверной и актуальной для определённой специальности определённого университета.

    ТРЕБОВАНИЯ К ОТВЕТУ (СТРОГО):
    1. Верни ТОЛЬКО валидный JSON по структуре:
    {{"universities": [
        {{
            "name": "Название вуза",
            "uni_description": "Описание вуза" пиши около 2-4 предложений, информацию ищи на сайтах вузопедия и поступи.онлайн,
            "dormitory_available": true,
            "official_website_link": Официальный сайт вуза (ОБЯЗАТЕЛЬНО находи точные сайты нужного университета. Проверяй его достоверность и актуальность, если видишь, что сайт не активен или просто не верный - начинай поиск сайта заново. Сайты можно искать на платформах вузипедия и поступи.онлайн),
            "programs": [
                {{
                    "specialty_name": "Код и название специальности",
                    "specialty_description": "Описание программы" пиши около 2-4 предложений,
                    "chance_budget": "Высокий",
                    "chance_paid": "Высокий",
                    "explanation": "Объяснение шансов (1 предложение)",
                    "paid_tuition_price": Стоимость платного обучения в рублях за год (только цифры). Ищи эти значения на сайтах вузопедия и поступи.онлайн. Обязательно перепровыеряй информацию, чтобы стоимость была максимально достоверной и актуальной
                }},
                ... (ровно 3 объекта programs)
            ]
        }},
        ... (ровно 5 объектов universities)
    ]}}

    2. Шансы (chance_budget, chance_paid) должны быть строго: "Высокий", "Средний" или "Низкий".
    3. ОЧЕНЬ ВАЖНО: Внутри текстовых значений КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО использовать двойные кавычки ("). Если нужно выделить название, используй кавычки-ёлочки (« »).
    4. Не пиши никаких комментариев перед или после JSON.
    """

    try:
        client = AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.4
        )
        result = json.loads(response.choices[0].message.content)

        if result.get("error"):
            return {"error": True, "message": result.get("message")}

        universities = result.get("universities", [])

        while len(universities) < 5:
            universities.append({
                "name": "Дополнительный вуз", "uni_description": "Информация не найдена.",
                "dormitory_available": True, "official_website_link": "https://example.com",
                "programs": [
                    {"specialty_name": "Неизвестно", "specialty_description": "Нет данных", "chance_budget": "Средний",
                     "chance_paid": "Высокий", "explanation": "Нет данных", "paid_tuition_price": 0}]
            })

        universities = universities[:5]

        for uni in universities:
            link = uni.get("official_website_link", "")
            if link and not link.startswith("http"):
                link = "https://" + link
            uni["official_website_link"] = link

            while len(uni.get("programs", [])) < 3:
                uni["programs"].append({"specialty_name": "Доп. программа", "specialty_description": "Нет данных",
                                        "chance_budget": "Средний", "chance_paid": "Высокий",
                                        "explanation": "Нет данных", "paid_tuition_price": 0})

        return {"universities": universities}

    except Exception as e:
        logging.error(f"Ошибка LLM: {e}. Возврат заглушек.")
        return {"universities": [
            {
                "name": "МГТУ им. Н.Э. Баумана", "uni_description": "Ведущий технический вуз.",
                "dormitory_available": True, "official_website_link": "https://bmstu.ru",
                "programs": [
                    {"specialty_name": "09.03.01 Информатика и ВТ", "specialty_description": "Разработка ПО",
                     "chance_budget": "Средний", "chance_paid": "Высокий", "explanation": "Баллы близки к порогу.",
                     "paid_tuition_price": 350000},
                    {"specialty_name": "09.03.04 Программная инженерия", "specialty_description": "Архитектура ПО",
                     "chance_budget": "Низкий", "chance_paid": "Высокий", "explanation": "Высокий конкурс.",
                     "paid_tuition_price": 360000},
                    {"specialty_name": "10.05.01 Компьютерная безопасность",
                     "specialty_description": "Защита информации", "chance_budget": "Низкий", "chance_paid": "Средний",
                     "explanation": "Требуются профильные предметы.", "paid_tuition_price": 340000}
                ]
            }
        ][:5]}

@app.post("/api/generate-recommendations")
async def generate_recommendations(req: UserRequest):
    result = await get_llm_recommendations(req)

    if result.get("error"):
        return {"error": True, "message": result["message"]}

    universities = result["universities"]
    session_id = str(uuid.uuid4())
    CACHE[session_id] = {
        "total_score": req.total_score,
        "career_broad": req.career_broad,
        "career_specific": req.career_specific,
        "tuition": req.tuition,
        "dorm": req.dorm,
        "universities": universities
    }
    return {"session_id": session_id}

@app.get("/api/get-session/{session_id}")
async def get_session(session_id: str):
    if session_id in CACHE:
        return CACHE[session_id]
    raise HTTPException(status_code=404, detail="Session not found")

@app.post("/api/summarize-reviews")
async def summarize_reviews(req: ReviewRequest):
    prompt = f"""
        Ты — ИИ-помощник студента. Ты анализируешь все реальные отзывы
        об университете '{req.university_name}' по специальности '{req.specialty_name}' на сайтах табитуриент, вузопедия, поступи.онлайн и остальных похожих проверенных источниках .
        Ответь на русском языке, нейтральным тоном по данной схеме:
        "Преимущества университета:
        (тут будут все основные приемущества и отличительные черты, которые ты находишь засчёт выжимки всех прочитанных отзывов)
        Недостатки университета:
        (тут будут все основные недостатки и плохие черты выбранного вузаб , которые ты находишь засчёт выжимки всех прочитанных отзывов)"
        Ни в коем случае ты не выходишь за рамки описанной выше схемы и не придумываешь своих данных и слов. Пишешь чётко и без всякихдополнений со своей стороны. Не нужно здороваться или писать какое-либо втупление. Сразу пишешь положительные и отрицательные стороны университета по схеме
        """
    try:
        client = AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8
        )
        return {"summary": response.choices[0].message.content}
    except Exception as e:
        logging.error(f"Ошибка суммаризации: {e}")
        return {"summary": "Не удалось загрузить отзывы. Попробуйте позже."}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)


