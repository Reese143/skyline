
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
import sqlite3

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

BASE = Path(__file__).resolve().parent
DB = BASE / "skyline_backup.db"

SEED = [
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


class PropertyCreate(BaseModel):
    title: str = Field(min_length=2, max_length=100)
    city: str = Field(min_length=2, max_length=60)
    district: str = Field(default="", max_length=80)
    type: Literal["apartment", "studio", "house"]
    price: int = Field(gt=0)
    rooms: int = Field(ge=1, le=30)
    area: int = Field(gt=0)
    floor: int = Field(ge=0)
    image: str = Field(default="", max_length=500)
    description: str = Field(default="", max_length=1000)
    featured: bool = False


def connect():
    connection = sqlite3.connect(DB, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def to_dict(row):
    result = dict(row)
    result["featured"] = bool(result["featured"])
    return result


@asynccontextmanager
async def lifespan(app: FastAPI):
    with connect() as connection:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(properties)")
        }

        if columns and "featured" not in columns:
            connection.execute(
                "ALTER TABLE properties ADD COLUMN featured INTEGER NOT NULL DEFAULT 0"
            )
        connection.execute(
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

        if connection.execute(
            "SELECT COUNT(*) FROM properties"
        ).fetchone()[0] == 0:
            connection.executemany(
                """
                INSERT INTO properties
                (
                    title, city, district, type, price,
                    rooms, area, floor, image, description, featured
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                SEED,
            )

    yield


app = FastAPI(
    title="Skyline API",
    description="Демо-каталог нерухомості",
    lifespan=lifespan,
)


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(BASE / "index.html")


@app.get("/style.css", include_in_schema=False)
def css():
    return FileResponse(
        BASE / "style.css",
        media_type="text/css",
    )


@app.get("/app.js", include_in_schema=False)
def javascript():
    return FileResponse(
        BASE / "app.js",
        media_type="application/javascript",
    )


@app.get("/api/properties")
def list_properties(
    search: str = Query(default="", max_length=100),
    type: str = "all",
    sort: str = "featured",
):
    if type not in ("all", "apartment", "studio", "house"):
        raise HTTPException(422, "Невідомий тип житла")

    if sort not in (
        "featured",
        "price_asc",
        "price_desc",
        "area_desc",
    ):
        raise HTTPException(422, "Невідоме сортування")

    where = []
    params = []

    if search.strip():
        where.append(
            "(city LIKE ? OR district LIKE ? OR title LIKE ?)"
        )
        term = f"%{search.strip()}%"
        params.extend([term, term, term])

    if type != "all":
        where.append("type = ?")
        params.append(type)

    order = {
        "featured": "featured DESC, id ASC",
        "price_asc": "price ASC",
        "price_desc": "price DESC",
        "area_desc": "area DESC",
    }[sort]

    sql = "SELECT * FROM properties"

    if where:
        sql += " WHERE " + " AND ".join(where)

    sql += " ORDER BY " + order

    with connect() as connection:
        rows = connection.execute(sql, params).fetchall()

    return [to_dict(row) for row in rows]


@app.get("/api/properties/{property_id}")
def get_property(property_id: int):
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM properties WHERE id = ?",
            (property_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(404, "Об’єкт не знайдено")

    return to_dict(row)


@app.post("/api/properties", status_code=201)
def create_property(data: PropertyCreate):
    payload = data.model_dump()
    payload["featured"] = int(payload["featured"])

    with connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO properties
            (
                title, city, district, type, price,
                rooms, area, floor, image, description, featured
            )
            VALUES
            (
                :title, :city, :district, :type, :price,
                :rooms, :area, :floor, :image,
                :description, :featured
            )
            """,
            payload,
        )

        row = connection.execute(
            "SELECT * FROM properties WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

    return to_dict(row)


@app.delete("/api/properties/{property_id}", status_code=204)
def delete_property(property_id: int):
    with connect() as connection:
        result = connection.execute(
            "DELETE FROM properties WHERE id = ?",
            (property_id,),
        )

        if result.rowcount == 0:
            raise HTTPException(404, "Об’єкт не знайдено")
