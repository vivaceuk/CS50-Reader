from cs50reader.helpers import login_required
from sqlalchemy import select, insert, update, delete, and_, or_
import html, dateutil, json
from datetime import datetime, timedelta

from flask import (
    Blueprint, redirect, Response, request, session, jsonify
)

import feedparser
from bs4 import BeautifulSoup
from cs50reader.models import User, Feed, Article
from cs50reader.db import get_db

bp = Blueprint('feed', __name__, url_prefix='/feed')


@bp.route("/fetch_feeds", methods=["POST"])
@login_required
async def fetch_feeds():
    """ Get the list of feeds """
    user_id = session["user_id"]
    # return the feeds for the current user.
    feeds = None

    async with get_db() as db_session:

        result = await db_session.execute(select(Feed).join(User, Feed.user_id == User.id).where(User.id == user_id))
        feeds = result.scalars().fetchall()
        await db_session.close()

    if feeds is not None:
        return jsonify([{'id': f.id, 'title': f.title} for f in feeds])
    else:
        return jsonify({})


@bp.route("/add_feed", methods=["POST"])
@login_required
async def add_feed():
    """ Add a feed """
    user_id = session["user_id"]
    request_data = request.get_json()
    feed_url = request_data.get('feed_url', None)
    feed_id = None

    async with get_db() as db_session:
        image_url = ''

        if feed_url:
            f = feedparser.parse(feed_url)

            if f.feed == {}:
                # the feed is bad.
                await db_session.close()
                return Response(json.dumps({'status': 'failure', 'message': 'bad feed'}), status=400, mimetype='application/json')

            # don't allow duplicate feeds
            result = await db_session.execute(select(Feed).where(and_(Feed.url == feed_url, Feed.user_id == User.id)))
            if result.scalars().one_or_none():
                await db_session.close()
                return Response(json.dumps({'status': 'failure', 'error': 'feed exists'}), status=400, mimetype='application/json')

            if 'icon' in f.feed:
                image_url = f.feed.get('icon', '')
            elif 'image' in f.feed:
                image_url = f.feed.image.get('url', '')
            else:
                image_url = ''

            # add the feed.
            user = await db_session.get(User, user_id)
            if not isinstance(user, User):
                await db_session.close()
                return redirect("/login")

            feed = Feed(title=f.feed.title, url=feed_url, description=f.feed.description,
                        icon_url=image_url, user_id=user_id)
            user.feeds.add(feed)

            await db_session.commit()
            feed_id = feed.id
            await db_session.close()

        if (feed_id):
            return Response(response=json.dumps({'status': 'success', 'feed_id': feed.id}), status=200, mimetype='application/json')

    return Response(response=json.dumps({'status': 'failure'}), status=400, mimetype='application/json')


@bp.route("/update_feed", methods=["POST"])
@login_required
async def update_feed():
    """ Refresh the articles in the feed(s) """
    user_id = session["user_id"]
    request_data = request.get_json()
    count = 0
    new_articles = list()
    update_articles = list()
    updated_articles = list()

    async with get_db() as db_session:

        # get the feeds for the current user.
        feed_id = int(request_data.get('feed_id'))
        result = await db_session.execute(select(Feed).join(User, Feed.user_id == User.id).where(
            and_(Feed.id == feed_id, User.id == user_id)))

        f = result.scalars().one_or_none()
        try:
            last_modified = f.last_modified.isoformat()
        except:
            last_modified = (datetime.fromtimestamp(0)).isoformat()

        # don't update feeds more frequently than every 15 minutes
        if (f.last_modified):
            if (f.last_modified > (datetime.now() - timedelta(minutes=15))):
                await db_session.close()
                return Response(response=json.dumps({'status': 'unchanged', 'count': 0, 'article_ids': []}), status=304, mimetype='application/json')

        # not all feeds use the 'modified' or 'etag' header, but it saves bandwidth if they do.
        current_feed = feedparser.parse(f.url, etag=f.etag, modified=last_modified)
        if current_feed.status == 304:
            # feed hasn't chenged since we last polled it.
            await db_session.close()
            return Response(response=json.dumps({'status': 'unchanged', 'count': 0, 'article_ids': []}), status=304, mimetype='application/json')

        if 'etag' in current_feed:
            etag = current_feed.etag
        else:
            etag = ''

        # handle the lack of agreement on the naming of the 'modified' attribute.
        if 'last_modified' in current_feed:
            feed_updated = dateutil.parser.parse(current_feed['last_modified'])
        elif 'modified' in current_feed:
            feed_updated = dateutil.parser.parse(current_feed['modified'])
        elif 'updated' in current_feed:
            feed_updated = dateutil.parser.parse(current_feed['updated'])
        elif 'generator' in current_feed:
            feed_updated = dateutil.parser.parse(current_feed['generator']['updated'])
        elif 'published' in current_feed:
            feed_updated = dateutil.parser.parse(current_feed['published'])
        else:
            feed_updated = datetime.now()

        if feed_updated == f.last_modified or (etag == f.etag and etag != ''):
            await db_session.close()
            return Response(response=json.dumps({'status': 'unchanged', 'count': 0, 'article_ids': []}), status=304, mimetype='application/json')

        f.last_updated = datetime.now()
        f.etag = etag

        for art in iter(current_feed.entries):
            content = ''
            if 'summary_detail' in art:
                content = art.summary_detail.value
            elif 'content' in art:
                content = art.content[0].value

            # if we've seen  this guid, title or content before move on to the next article.
            sub_query = (select(Feed.id).join(User, Feed.user_id == User.id).where(
                and_(Feed.id == feed_id, User.id == user_id)).scalar_subquery())
            result = await db_session.execute(select(Article).where(and_(or_(or_(Article.guid == html.escape(art.id), Article.title == html.escape(
                art.title)), or_(Article.summary == html.escape(content), Article.link == art.link)), Article.feed_id.in_(sub_query))))
            if len(result.scalars().fetchall()):
                # article needs updating?
                #    update_articles.append({'id': article_id, 'title': html.escape(art.title), 'summary': html.escape(content), 'link': art.link, 'thumb_url': thumb['url'], 'thumb_height': thumb[
                #       'height'], 'thumb_width': thumb['width'], 'published': published, 'guid': html.escape(art.id), 'feed_id': feed_id})

                continue

            # try to set a thumbnail image for the article. not all will have images.
            try:
                thumb = art.media_thumbnail[0]
            except AttributeError:
                thumb = None
            if not thumb:
                thumb = {'url': '', 'height': '', 'width': ''}
            published = ''
            try:
                if 'published' in art:
                    published = art.get('published')
                    published = dateutil.parser.parse(published)
                elif 'pubDate' in art:
                    published = art.get('pubDate')
                    published = dateutil.parser.parse(published)
                elif 'updated' in art:
                    published = art.get('updated')
                    published = dateutil.parser.parse(published)
                else:
                    published = datetime.now()
            except TypeError:
                published = datetime.now()

            # use beautiful soup to add 'target="_blank"' to links in article (forces them to open in a new tab)
            # also set embeded images to lazy loading
            try:
                soup = BeautifulSoup(content, 'html5lib')
                links = soup.find_all('a')
                for link in links:
                    link['target'] = '_blank'
                    link['rel'] = 'noopener noreferrer'

                images = soup.find_all('img')
                for image in images:
                    image['loading'] = 'lazy'

                soup = soup.html.unwrap()
                content = str(soup.body.unwrap())
            except:
                pass

            res = False
            for i in iter(new_articles):
                if i['link'] == art.link or i['title'] == html.escape(art.title):
                    res = True

            # the article doesn't exist so add it.
            if art.title and content and not res:
                new_articles.append({'title': html.escape(art.title), 'summary': html.escape(content), 'link': art.link, 'thumb_url': thumb['url'], 'thumb_height': thumb[
                    'height'], 'thumb_width': thumb['width'], 'is_read': 0, 'published': published, 'guid': html.escape(art.id), 'feed_id': feed_id})

        result = list()
        result_update = list()
        article_ids = list()
        if len(new_articles):
            result = await db_session.execute(insert(Article).returning(Article.id), new_articles)

        if len(update_articles):
            result_update = await db_session.execute(update(Article).returning(Article.id), update_articles)

        await db_session.commit()
        article_ids = [res for (res,) in result]
        updated_articles = [res for (res,) in result_update]
        article_ids.extend(updated_articles)
        await db_session.close()

    count = len(article_ids)

    if count > 0:
        return Response(response=json.dumps({'status': 'success', 'count': count, 'article_ids': article_ids, 'updated_articles': [i for (i, ) in updated_articles]}), status=200, mimetype='application/json')
    else:
        return Response(response=json.dumps({'status': 'unchanged', 'count': 0, 'article_ids': []}), status=304, mimetype='application/json')

@bp.route("/delete_feed", methods=["POST"])
@login_required
async def delete_feed():
    """ Delete the specified feed """
    user_id = session["user_id"]
    request_data = request.get_json()
    feed_id = request_data.get('feed_id', -1)

    async with get_db() as db_session:
        try:
            await db_session.execute(delete(Feed).where(
                and_(Feed.id == feed_id, Feed.user_id == user_id)))

            await db_session.commit()
            await db_session.close()
            return Response(response=json.dumps({'status': 'success'}), status=200, mimetype='application/json')
        except:
            pass

        await db_session.close()
    return Response(response=json.dumps({'status': 'failure'}), status=400, mimetype='application/json')


@bp.route("/mark_feed_read", methods=["POST"])
@login_required
async def mark_feed_read():
    """ Mark the specified article as read """
    user_id = session["user_id"]
    request_data = request.get_json()

    feed_id = request_data.get('feed_id', -1)
    async with get_db() as db_session:
        try:
            sub_query = (select(Article.id).join(Feed, Article.feed_id == Feed.id).join(
                User, Feed.user_id == User.id).where(and_(Feed.id == feed_id, User.id == user_id)).scalar_subquery())
            result = await db_session.execute(update(Article).where(
                and_(Article.is_read == 0, Article.id.in_(sub_query))).values(is_read=1))

            await db_session.commit()
            await db_session.close()
            return Response(response=json.dumps({'status': 'success'}), status=200, mimetype='application/json')
        except:
            await db_session.close()
            return Response(response=json.dumps({'status': 'failure'}), status=400, mimetype='application/json')

