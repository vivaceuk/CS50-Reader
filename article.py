from cs50reader.helpers import login_required
from sqlalchemy import select, update, and_
import json

from flask import (
    Blueprint, Response, request, session
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


