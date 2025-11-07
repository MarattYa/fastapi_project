from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel,Field

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, scoped_session, Mapped, mapped_column, Session
from sqlalchemy import select
app = FastAPI()

engine = create_async_engine('sqlite+aiosqlite:///books.db', echo=True)

new_session = async_sessionmaker(engine, expire_on_commit=False)


#асинхронная сессия с БД, FastAPI будет вставлять
# в эндпоинст через Depends
async def get_session():
    async with new_session() as session:
        yield session

SessionDep = Annotated[AsyncSession, Depends(get_session)]



class Base(DeclarativeBase):
    pass

#work with alchemy
class BookModel(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title:Mapped[str]
    author:Mapped[str]

@app.post("/setup")
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)# все данные таблиц
    return {"success": True}

#work with pydantic
class BookAddSchema(BaseModel):
    title: str
    author: str

class BookSchema(BookAddSchema):
    id: int

@app.post("/books")
async def add_book(data: BookAddSchema, session: SessionDep):
    new_book = BookModel(
        title=data.title,
        author=data.author
    )
    session.add(new_book)
    await session.commit()
    return {"ok": True}

class PassinationParams(BaseModel):
    limit: int = Field(5,ge=0,le=100,description="count pages")
    offset: int = Field(0,ge=0,description="where start page")

PaginationDep = Annotated[PassinationParams, Depends(PassinationParams)]


@app.get("/books")
async def get_books(
        session: SessionDep,
        pagination: PaginationDep,
) -> list[BookSchema]:
    query = (
        select(BookModel) # SELECT * FROM books
        .limit(pagination.limit) # пагинация
        .offset(pagination.offset)# пагинация
    )
    result = await session.execute(query) # отправка  SQL в SQLite
    return result.scalars().all() # результат список объектов BookModel