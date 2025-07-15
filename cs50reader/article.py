from cs50reader.helpers import login_required
from sqlalchemy import select, update, and_
import json, html

from flask import (
    Blueprint, Response, request, session, jsonify
)

from cs50reader.models import User, Feed, Article
from cs50reader.db import get_db

bp = Blueprint('article', __name__, url_prefix='/article')


@bp.route("/mark_article_read", methods=["POST"])
@login_required
async def mark_article_read():
    """ Mark the specified article as read """
    user_id = session["user_id"]
    request_data = request.get_json()

    feed_id = request_data.get('feed_id', -1)
    article_id = request_data.get('article_id', -1)

    async with get_db() as db_session:
        try:
            sub_query = (select(Feed.id).join(User, Feed.user_id == User.id).where(
                and_(Feed.id == feed_id, User.id == user_id)).scalar_subquery())
            await db_session.execute(update(Article).values(is_read=1).where(
                and_(Article.id == article_id, and_(Article.feed_id.in_(sub_query)))))

            await db_session.commit()
            await db_session.close()
            return Response(response=json.dumps({'status': 'success'}), status=200, mimetype='application/json')
        except:
            pass

        await db_session.close()

        return Response(response=json.dumps({'status': 'failure'}), status=400, mimetype='application/json')


@bp.route("/fetch_articles", methods=["POST"])
@login_required
async def fetch_articles():
    """ Get the list of articles for the feed """
    user_id = session["user_id"]
    request_data = request.get_json()
    feed_id = int(request_data.get('feed_id', None))
    offset = request_data.get('offset', 0)
    limit = request_data.get('limit', 20)
    article_ids = request_data.get('article_ids', None)
    try:
        show_type = int(request_data.get('show_type'))
    except:
        show_type = 0

    articles = list()
    async with get_db() as db_session:

        # get the articles for the given feed.

        if article_ids:
            entries = await db_session.execute(select(Article).join(Feed, Article.feed_id == Feed.id).join(User, Feed.user_id == User.id).where(and_(and_(
                Feed.id == feed_id, Article.id.in_(article_ids)), User.id == user_id)).order_by(Article.published.desc(), Article.guid.desc()))
        else:
            if show_type < 2:
                entries = await db_session.execute(select(Article).join(Feed, Article.feed_id == Feed.id).join(User, Feed.user_id == User.id).where(and_(and_(Feed.id == feed_id,
                                                                                                                                                            Article.is_read == show_type), User.id == user_id)).order_by(Article.published.desc(), Article.guid.desc()).offset(offset).limit(limit))
            else:
                entries = await db_session.execute(select(Article).join(Feed, Article.feed_id == Feed.id).join(User, Feed.user_id == User.id).where(and_(
                    Feed.id == feed_id, User.id == user_id)).order_by(Article.published.desc(), Article.guid.desc()).offset(offset).limit(limit))

        articles = [row.to_dict() for row in entries.scalars().fetchall()]
        await db_session.close()

    # remove HTML escaping from the article for display (it was escaped for storage)
    for a in articles:
        a['title'] = html.unescape(a['title'])
        a['summary'] = html.unescape(a['summary'])

    return jsonify(articles)
