from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
import asyncio

from flask import current_app, g

engine = None
async_session = None


def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        global engine
        engine = create_async_engine(current_app.config["DATABASE"])
    global async_session
    async_session = async_sessionmaker(engine, autoflush=False, expire_on_commit=False)


def get_db():
    global async_session
    if not async_session:
        async_session = async_sessionmaker(engine, autoflush=False, expire_on_commit=False)
    if 'db' not in g:
        g.db = async_session()

    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    async def wrapped():
        if db is not None:
            await db.close()
    asyncio.run(wrapped())
