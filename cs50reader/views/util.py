from util.helpers import login_required
from sqlalchemy import select, text, and_
import json

from flask import (
    Blueprint, Response, request, session, jsonify
)

from db.models import User, Feed, Article
from db.db import get_db

util_bp = Blueprint('util', __name__, url_prefix='/util')


@util_bp.route("/compact_db", methods=["POST"])
@login_required
async def compact_db():
    """ Compact the database """

    async with get_db() as db_session:
        try:
            await db_session.execute(text("VACUUM;"))
            await db_session.commit()
            await db_session.close()
            return Response(response=json.dumps({'status': 'success'}), status=200, mimetype='application/json')
        except Exception as e:
            await db_session.close()
            logger.info(e)

    return Response(response=json.dumps({'status': 'failure'}), status=400, mimetype='application/json')


@util_bp.route("/purge_articles", methods=["POST"])
@login_required
async def purge_articles():
    """ Purge old articles"""
    user_id = session["user_id"]
    request_data = request.get_json()

    feed_id = request_data.get('feed_id', -1)
    num_days = request_data.get('days', 30)
    async with get_db() as db_session:
        try:
            sub_query = (select(Feed.id).join(User, Feed.user_id == User.id).where(
                and_(Feed.id == feed_id, User.id == user_id)).scalar_subquery())
            result = await db_session.execute(delete(Article).where(
                and_(Article.published < datetime.now() - timedelta(num_days), Article.feed_id.in_(sub_query))))
            await db_session.commit()
            rowcount = result.rowcount
            await db_session.close()
            if rowcount:
                return Response(response=json.dumps({'status': 'success'}), status=200, mimetype='application/json')
        except Exception as e:
            await db_session.close()
            logger.log(e)

    return Response(response=json.dumps({'status': 'failure'}), status=400, mimetype='application/json')
