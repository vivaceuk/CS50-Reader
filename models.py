from __future__ import annotations
from typing import List

from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import DateTime
from sqlalchemy import Sequence
from sqlalchemy import Column
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, Sequence("user_id_seq"), autoincrement=True, primary_key=True)
    username: Mapped[str]  = mapped_column(String)
    hash: Mapped[str]  = mapped_column(String)

    feeds: Mapped[List["Feed"]] = relationship("Feed", cascade="all, delete, delete-orphan")

    def __repr__(self):
        return "<User(id='%s', username='%s')>" % (
            self.id,
            self.username
        )


class Feed(Base):
    __tablename__ = "feeds"
    id: Mapped[int] = mapped_column(Integer, Sequence("feed_id_seq"), autoincrement=True, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    url: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    icon_url: Mapped[str] = mapped_column(String)
    etag: Mapped[str] = mapped_column(String)
    last_modified: Mapped[str] = mapped_column(String)
    last_updated: Mapped[str] = mapped_column(String)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    user: Mapped["User"] = relationship("User", back_populates="feeds")
    articles: Mapped[List["Article"]] = relationship("Article", cascade="all, delete, delete-orphan")

    def __repr__(self):
        return "<Feed(id='%s', title='%s'')>" % (
            self.id,
            self.title,
        )

    def to_dict(self):
        return {"id": self.id,
                "title": self.title}

    def is_empty(self):
        return self.url == ""


class Article(Base):
    __tablename__ = "articles"
    id: Mapped[int] = mapped_column(Integer, Sequence("article_id_seq"), autoincrement=True, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    summary: Mapped[str] = mapped_column(String)
    link: Mapped[str] = mapped_column(String)
    thumb_url: Mapped[str] = mapped_column(String)
    thumb_height: Mapped[int] = mapped_column(Integer)
    thumb_width: Mapped[int] = mapped_column(Integer)
    published: Mapped[str] = mapped_column(String)
    is_read: Mapped[int] = mapped_column(Integer, default=0)
    guid: Mapped[str] = mapped_column(String)

    feed_id: Mapped[int]  = mapped_column(ForeignKey("feeds.id"))

    feed: Mapped["Feed"] = relationship("Feed", back_populates="articles")

    def __repr__(self):
        return "<User(id='%s', title='%s', summary='%s')>" % (
            self.id,
            self.title,
            self.summary,
        )

    def to_dict(self):
        return {"id": self.id,
                "title": self.title,
                "summary": self.summary,
                "link":  self.link,
                "thumb_height": self.thumb_height,
                "thumb_width": self.thumb_width,
                "thumb_url": self.thumb_url,
                "published": self.published,
                "is_read": self.is_read,
                "guid": self.guid}
