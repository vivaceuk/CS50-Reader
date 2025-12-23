from __future__ import annotations
from typing import List
from datetime import datetime, timezone

from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import DateTime
from sqlalchemy import Sequence
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import relationship
from sqlalchemy.orm import WriteOnlyMapped
from sqlalchemy import UniqueConstraint
#from sqlalchemy  import ForeignKeyConstraint
from werkzeug.security import check_password_hash, generate_password_hash


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username"),
    )
    id: Mapped[int] = mapped_column(Integer, Sequence("user_id_seq"), autoincrement=True, primary_key=True)
    username: Mapped[str]  = mapped_column(String, unique=True, index=True, nullable=False)
    hash: Mapped[str]  = mapped_column(String, nullable=False)

    feeds: WriteOnlyMapped[List["JT_User_Feed"]] = relationship("JT_User_Feed", passive_deletes=True, cascade="all, delete, delete-orphan")

    def set_password(self, password):
        self.hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hash, password)

    def __repr__(self):
        return "<User(id='%s', username='%s')>" % (
            self.id,
            self.username
        )


class Feed(Base):
    __tablename__ = "feeds"
    __table_args__ = (
        #ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    id: Mapped[int] = mapped_column(Integer, Sequence("feed_id_seq"), autoincrement=True, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    icon_url: Mapped[str] = mapped_column(String, nullable=True)
    etag: Mapped[str] = mapped_column(String, nullable=True)
    last_modified: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=datetime.fromtimestamp(0, timezone.utc))
    last_updated: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=datetime.fromtimestamp(0, timezone.utc))
    purge_date: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=datetime.fromtimestamp(0, timezone.utc))

    articles: WriteOnlyMapped[List["Article"]] = relationship("Article", back_populates="feed", passive_deletes=True, cascade="all, delete, delete-orphan")
    user_feed: WriteOnlyMapped[List["JT_User_Feed"]] = relationship("JT_User_Feed", back_populates="feed", passive_deletes=True, cascade="all, delete, delete-orphan")

    def __repr__(self):
        return "<Feed(id='%s', title='%s', url='%s', description='%s')>" % (
            self.id,
            self.title,
            self.url,
            self.description
        )

    def to_dict(self):
        return {"id": self.id,
                "title": self.title}

    def is_empty(self):
        return self.url == ""


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (
        #ForeignKeyConstraint(["feed_id"], ["feeds.id"]),
    )
    id: Mapped[int] = mapped_column(Integer, Sequence("article_id_seq"), autoincrement=True, primary_key=True)
    title: Mapped[str] = mapped_column(String, unique=False, nullable=False)
    summary: Mapped[str] = mapped_column(Text, unique=False, nullable=False)
    link: Mapped[str] = mapped_column(String(255), unique=False, nullable=False)
    thumb_url: Mapped[str] = mapped_column(String, nullable=True)
    thumb_height: Mapped[int] = mapped_column(Integer, nullable=True)
    thumb_width: Mapped[int] = mapped_column(Integer, nullable=True)
    published: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.fromtimestamp(0, timezone.utc))
    guid: Mapped[str] = mapped_column(String, nullable=False)

    feed_id: Mapped[int]  = mapped_column(ForeignKey("feeds.id"), index=True, unique=False, nullable=False)

    feed: Mapped["Feed"] = relationship("Feed", back_populates="articles")
    feed_article: WriteOnlyMapped[List["JT_Feed_Article"]] = relationship("JT_Feed_Article", back_populates="article", passive_deletes=True, cascade="all, delete, delete-orphan")

    def __repr__(self):
        return "<Article(id='%s', title='%s', summary='%s', published='%s', guid='%s', feed_id='%i')>" % (
            self.id,
            self.title,
            self.summary,
            self.published,
            self.guid,
            self.feed_id
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
                "guid": self.guid}


class JT_User_Feed(Base):
    __tablename__ = "jt_user_feed"
    __table_args__ = (
        #
    )
    id: Mapped[int] = mapped_column(Integer, Sequence("jt_user_feed_seq"), autoincrement=True, primary_key=True)
    feed_id: Mapped[int] = mapped_column(ForeignKey("feeds.id"), index=True, unique=False, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, unique=False, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="feeds")
    feed: Mapped["Feed"] = relationship("Feed", back_populates="user_feed")
    articles: WriteOnlyMapped[List["JT_Feed_Article"]] = relationship("JT_Feed_Article", back_populates="feed", passive_deletes=True, cascade="all, delete, delete-orphan")


class JT_Feed_Article(Base):
    __tablename__ = "jt_feed_article"
    __table_args__ = (
        #
    )
    id: Mapped[int] = mapped_column(Integer, Sequence("jt_feed_article_seq"), autoincrement=True, primary_key=True)
    feed_id: Mapped[int] = mapped_column(ForeignKey("jt_user_feed.id"), unique=False, nullable=False)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"), unique=False, nullable=False)
    is_read: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    favourite: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    feed: Mapped["JT_User_Feed"] = relationship("JT_User_Feed", back_populates="articles")
    article: Mapped["Article"] = relationship("Article", back_populates="feed_article")
