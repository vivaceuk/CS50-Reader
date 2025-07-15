from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, select, insert, update, delete, text, exists, literal, and_, or_

from models import Base, User, Feed, Article

engine = create_engine("sqlite:///cs50reader2.db")
session_factory = sessionmaker(bind=engine, autoflush=False)
DBSession = scoped_session(session_factory)

Base.metadata.create_all(bind=engine)
