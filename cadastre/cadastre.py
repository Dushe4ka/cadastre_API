import  json
import requests
import starlette.status as status

from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from typing import Optional

from .constants import SERVER_URL
from .database import db, engine
from .models import Base, QueryModel
from .schemas import QuerySchema

Base.metadata.create_all(bind=engine)

cadastre = FastAPI()


def get_remote():
    """GET-запрос к удалённому серверу"""
    return requests.get(SERVER_URL + '/ping')


def post_remote(data):
    """POST-запрос к удалённому серверу"""
    return requests.post(SERVER_URL + '/get_answer', data)


def add_query(data):
    """
    Принимает данные запроса и ответ.
    Сохраняет запрос с результатами в базу данных.
    """
    query = QueryModel(cadastre_num=data['cadastre_num'],
                       latitude=data['latitude'],
                       longitude=data['longitude'],
                       created_at=datetime.now(),
                       answer=data['answer']
                       )
    db.add(query)
    db.commit()
    db.refresh(query)
    return query.id


@cadastre.get("/ping")
def ping():
    """Проверка работоспособности сервера"""
    response = get_remote()
    if response.ok:
        return "Сервер доступен"
    return "Сервер недоступен"


@cadastre.post("/query")
def query(query: QuerySchema):
    """Отправляет запрос на удалённый сервер и сохраняет результат в базу данных"""
    data = {
            "cadastre_num": query.cadastre_num,
            "latitude": query.latitude,
            "longitude": query.longitude
        }
    response = post_remote(json.dumps(data))
    if not response.ok:
        return RedirectResponse(
            "/cadastre/ping",
            status_code=status.HTTP_302_FOUND
        )
    data["answer"] = response.json()['result']
    query_id = add_query(data)
    return RedirectResponse(
        f"/cadastre/result/{query_id}",
        status_code=status.HTTP_302_FOUND
    )


@cadastre.get("/result/{query_id}")
def result(query_id):
    """Получает результат запроса по его ID"""
    query = db.query(QueryModel).filter(QueryModel.id == query_id).first()
    return query.answer


@cadastre.get("/history")
def history(cadastre_num: Optional[str] = None):
    """Получает историю запросов по номеру кадастрового участка"""
    result = db.query(QueryModel)
    if cadastre_num:
        return result.filter(QueryModel.cadastre_num == cadastre_num).all()
    return result.all()
