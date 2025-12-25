from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy import text
import asyncio
import sqlite3
from datetime import datetime

import click

import os, inspect

from flask import current_app, g

from db.models import Base

async_session = None

engine = None


def init_db():
    db = get_db()

    #with current_app.open_resource('schema.sql') as f:
    #    db.executescript(f.read().decode('utf8'))

    # Base.metadata.create_all(bind=engine)
    async def init_models():
        global engine
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_models())


@click.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')


async def compact_db():
    async with get_db() as db_session:
        try:
            await db_session.execute(text("VACUUM;"))
            await db_session.commit()
            await db_session.close()
            print('Compacted the database.')
        except Exception as e:
            await db_session.close()
            print(e)


@click.command('compact-db')
def compact_db_command():
    """Compact the database."""
    asyncio.run(compact_db())


sqlite3.register_converter(
    "timestamp", lambda v: datetime.fromisoformat(v.decode())
)


def close_db(exception):
        db = g.pop('db', None)

        async def wrapped():
            if db is not None:
                await db.close()

        asyncio.run(wrapped())


def init_app(app):
    with app.app_context():
        app.teardown_appcontext(close_db)
        app.cli.add_command(init_db_command)
        app.cli.add_command(compact_db_command)
        global engine
        try:
            from cs50reader import config
            engine = create_async_engine(config.DATABASE)
        except:
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

