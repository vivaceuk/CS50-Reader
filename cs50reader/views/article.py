from util.helpers import login_required
from sqlalchemy import select, update, and_
import json, html

from flask import (
    Blueprint, Response, request, session, jsonify
)

from db.models import User, Feed, Article, JT_User_Feed, JT_Feed_Article
from db.db import get_db

article_bp = Blueprint('article', __name__, url_prefix='/article')


@article_bp.route("/mark_article_read", methods=["POST"])
@login_required
async def mark_article_read():
    """ Mark the specified article as read """
    user_id = session["user_id"]
    request_data = request.get_json()

    feed_id = request_data.get('feed_id', -1)
    article_id = request_data.get('article_id', -1)

    async with get_db() as db_session:
        try:
            sub_query = (select(JT_User_Feed.id).join(User, JT_User_Feed.user_id == User.id).where(
                and_(JT_User_Feed.feed_id == feed_id, User.id == user_id)).scalar_subquery())
            await db_session.execute(update(JT_Feed_Article).values(is_read=1).where(
                and_(JT_Feed_Article.article_id == article_id, and_(JT_Feed_Article.feed_id.in_(sub_query)))))

            await db_session.commit()
            await db_session.close()
            return Response(response=json.dumps({'status': 'success'}), status=200, mimetype='application/json')
        except:
            pass

        await db_session.close()

        return Response(response=json.dumps({'status': 'failure'}), status=400, mimetype='application/json')


@article_bp.route("/fetch_articles", methods=["POST"])
@login_required
async def fetch_articles():
    """ Get the list of articles for the feed """
    user_id = session["user_id"]
    request_data = request.get_json()
    feed_id = request_data.get('feed_id', None)
    offset = int(request_data.get('offset', 0))
    limit = int(request_data.get('limit', 20))
    article_ids = request_data.get('article_ids', None)
    try:
        show_type = int(request_data.get('show_type'))
    except:
        show_type = 0

    articles = list()
    entries = list()
    async with get_db() as db_session:

        # get the articles for the given feed.

        if article_ids is not None and article_ids != "" and len(article_ids) > 0:
            entries = await db_session.execute(select(Article, JT_Feed_Article.is_read, JT_Feed_Article.favourite).join(JT_Feed_Article, JT_Feed_Article.article_id == Article.id).join(JT_User_Feed, JT_Feed_Article.feed_id == JT_User_Feed.id).join(User, JT_User_Feed.user_id == User.id).where(and_(and_(
                JT_User_Feed.feed_id == feed_id, Article.id.in_(article_ids)), User.id == user_id)).order_by(Article.published.desc(), Article.guid.desc()))
        else:
            if show_type < 2:
                entries = await db_session.execute(select(Article, JT_Feed_Article.is_read, JT_Feed_Article.favourite).join(JT_Feed_Article, JT_Feed_Article.article_id == Article.id).join(JT_User_Feed, JT_Feed_Article.feed_id == JT_User_Feed.id).join(User, JT_User_Feed.user_id == User.id).where(and_(and_(JT_User_Feed.feed_id == feed_id,
                                                                                                                                                            JT_Feed_Article.is_read == show_type), User.id == user_id)).order_by(Article.published.desc(), Article.guid.desc()).offset(offset).limit(limit))
            else:
                entries = await db_session.execute(select(Article, JT_Feed_Article.is_read, JT_Feed_Article.favourite).join(JT_Feed_Article, JT_Feed_Article.article_id == Article.id).join(JT_User_Feed, JT_Feed_Article.feed_id == JT_User_Feed.id).join(User, JT_User_Feed.user_id == User.id).where(and_(
                    JT_User_Feed.feed_id == feed_id, User.id == user_id)).order_by(Article.published.desc(), Article.guid.desc()).offset(offset).limit(limit))

        result = entries.all()
        articles = [(x[0].to_dict() | {"is_read" : x[1], "favourite": x[2]}) for x in result] # Merge JT_Feed_Article.is_read and JT_Feed_Article.favourite into the existing Article dict
        await db_session.close()

    # remove HTML escaping from the article for display (it was escaped for storage)
    for a in articles:
        a['title'] = html.unescape(a['title'])
        a['summary'] = html.unescape(a['summary'])

    return jsonify(articles)
