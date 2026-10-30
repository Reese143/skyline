
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
import sqlite3

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "skyline_render.db"

PROPERTIES = [
    (
        "Світлий простір", "Київ", "Шевченківський",
        "apartment", 2850000, 2, 56, 7,
        "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=1100&q=85",
        "Світла квартира з просторою вітальнею, поруч із парком.", 1
    ),
    (
        "Панорама міста", "Київ", "Печерський",
        "apartment", 4200000, 3, 87, 12,
        "https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?w=1100&q=85",
        "Сучасне планування, панорамні вікна та затишна кухня.", 1
    ),
    (
        "Тиха студія", "Київ", "Солом’янський",
        "studio", 1950000, 1, 38, 8,
        "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?w=1100&q=85",
        "Компактна студія з продуманим зонуванням.", 0
    ),
    (
        "Дім біля саду", "Львів", "Сихівський",
        "house", 6100000, 4, 142, 2,
        "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=1100&q=85",
        "Приватний будинок з терасою та місцем для відпочинку.", 1
    ),
    (
        "Затишний мінімалізм", "Житомир", "Центр",
        "apartment", 2380000, 2, 63, 4,
        "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=1100&q=85",
        "Теплі відтінки, великі вікна та зручна локація.", 0
    ),
    (
        "Квартира з характером", "Одеса", "Приморський",
        "apartment", 3650000, 3, 79, 5,
        "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?w=1100&q=85",
        "Простора квартира для комфортного міського життя.", 1
    ),
]


class PropertyOut(BaseModel):
    id: int
    title: str
    city: str
    district: str
    type: str
    price: int
    rooms: int
    area: int
    floor: int
    image: str
    description: str
    featured: bool


def get_connection():
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def serialize_property(row):
    result = dict(row)
    result["featured"] = bool(result["featured"])
    return result


@asynccontextmanager
async def lifespan(app: FastAPI):
    with get_connection() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS properties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                city TEXT NOT NULL,
                district TEXT NOT NULL,
                type TEXT NOT NULL,
                price INTEGER NOT NULL,
                rooms INTEGER NOT NULL,
                area INTEGER NOT NULL,
                floor INTEGER NOT NULL,
                image TEXT NOT NULL,
                description TEXT NOT NULL,
                featured INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        count = db.execute(
            "SELECT COUNT(*) FROM properties"
        ).fetchone()[0]

        if count == 0:
            db.executemany(
                """
                INSERT INTO properties (
                    title, city, district, type,
                    price, rooms, area, floor,
                    image, description, featured
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                PROPERTIES,
            )

    yield


app = FastAPI(
    title="Skyline Real Estate API",
    description="Публічний демонстраційний каталог нерухомості",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(BASE_DIR / "index.html")


@app.get("/style.css", include_in_schema=False)
def css():
    return FileResponse(
        BASE_DIR / "style.css",
        media_type="text/css",
    )


@app.get("/app.js", include_in_schema=False)
def javascript():
    return FileResponse(
        BASE_DIR / "app.js",
        media_type="application/javascript",
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "skyline"}


@app.get(
    "/api/properties",
    response_model=list[PropertyOut],
)
def list_properties(
    search: str = Query(default="", max_length=100),
    type: Literal[
        "all", "apartment", "studio", "house"
    ] = "all",
    sort: Literal[
        "featured",
        "price_asc",
        "price_desc",
        "area_desc",
    ] = "featured",
):
    conditions = []
    params = []

    if search.strip():
        conditions.append(
            "(title LIKE ? OR city LIKE ? OR district LIKE ?)"
        )

        value = f"%{search.strip()}%"
        params.extend([value, value, value])

    if type != "all":
        conditions.append("type = ?")
        params.append(type)

    order_by = {
        "featured": "featured DESC, id ASC",
        "price_asc": "price ASC, id ASC",
        "price_desc": "price DESC, id ASC",
        "area_desc": "area DESC, id ASC",
    }[sort]

    sql = "SELECT * FROM properties"

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " ORDER BY " + order_by

    with get_connection() as db:
        rows = db.execute(sql, params).fetchall()

    return [serialize_property(row) for row in rows]


@app.get(
    "/api/properties/{property_id}",
    response_model=PropertyOut,
)
def get_property(property_id: int):
    with get_connection() as db:
        row = db.execute(
            "SELECT * FROM properties WHERE id = ?",
            (property_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Об'єкт не знайдено",
        )

    return serialize_property(row)
