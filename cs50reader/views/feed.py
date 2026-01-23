from util.helpers import login_required
from sqlalchemy import select, insert, update, delete, distinct, and_, or_, func
import json, subprocess, time, logging
import asyncio, html, dateutil
from datetime import datetime, timedelta, timezone

from zoneinfo import ZoneInfo

import feedparser
from bs4 import BeautifulSoup, Comment
import os, time, argparse
from db.models import Feed, Article

import asyncio
import click
from flask import (
    Blueprint, redirect, Response, request, session, jsonify
)

import feedparser
from bs4 import BeautifulSoup
from db.models import User, Feed, Article, JT_User_Feed, JT_Feed_Article
from db.db import get_db

if os.environ.get('FLASK_DEBUG') == '1':
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)
#logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
logger = logging.getLogger(__name__)

feed_bp = Blueprint('feed', __name__, url_prefix='/feed')

@feed_bp.route("/fetch_feeds", methods=["POST"])
@login_required
async def fetch_feeds():
    """ Get the list of feeds """
    user_id = session["user_id"]
    # return the feeds for the current user.
    feeds = None

    async with get_db() as db_session:

        result = await db_session.execute(select(Feed).join(JT_User_Feed, Feed.id == JT_User_Feed.feed_id).join(User, JT_User_Feed.user_id == User.id).where(User.id == user_id).order_by(Feed.title))
        feeds = result.scalars().fetchall()
        await db_session.close()

    if feeds is not None:
        return jsonify([{'id': f.id, 'title': f.title} for f in feeds])
    else:
        return jsonify({})


@feed_bp.route("/add_feed", methods=["POST"])
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
            result = await db_session.execute(select(Feed).join(JT_User_Feed, JT_User_Feed.feed_id == Feed.id).join(User, JT_User_Feed.user_id == User.id).where(and_(Feed.url == feed_url, User.id == user_id)))
            if result.scalars().one_or_none() is not None:
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

            result = await db_session.execute(select(Feed).where(Feed.url == feed_url))
            result = result.scalars().one_or_none()
            if not isinstance(result, Feed):
                result = await db_session.execute(insert(Feed).values(title=f.feed.title, url=feed_url, description=f.feed.description,
                            icon_url=image_url, last_modified=datetime.min).returning(Feed.id))
                feed = result.scalars().one_or_none()
                feed_user = await db_session.execute(insert(JT_User_Feed).values(feed_id=feed, user_id=user_id).returning(JT_User_Feed.id))
            else:
                feed_user = await db_session.execute(insert(JT_User_Feed).values(feed_id=result.id, user_id=user_id).returning(JT_User_Feed.id))

            await db_session.commit()
            try:
                feed_id = feed
            except:
                pass
            await db_session.close()

        if (feed):
            subprocess.run(["python", "-m", "flask", "feed", "update", "--id", str(feed_id)])
            time.sleep(2)
            return Response(response=json.dumps({'status': 'success', 'feed_id': feed_id}), status=200, mimetype='application/json')

    return Response(response=json.dumps({'status': 'failure'}), status=400, mimetype='application/json')


@feed_bp.route("/update_feed", methods=["POST"])
@login_required
async def update_feed():
    user_id = session["user_id"]
    request_data = request.get_json()
    feed_id = int(request_data.get('feed_id'))
    new_articles = list()


    async with get_db() as db_session:

        result = await db_session.execute(select(JT_User_Feed.id).join(User, JT_User_Feed.user_id == User.id).where(
            and_(JT_User_Feed.feed_id == feed_id, User.id == user_id)))

        user_feed = result.scalars().one_or_none()

        # this looks complicated, but we are using a single query to update the user's junction table

        # 1. get all the article ids currently in the user's junction table for this feed...
        ids_in_jt_query = (select(JT_Feed_Article.article_id).join(JT_User_Feed, JT_Feed_Article.feed_id == JT_User_Feed.id).join(User, JT_User_Feed.user_id == User.id).where(and_(JT_User_Feed.feed_id == feed_id, User.id == user_id)).scalar_subquery())

        # 2. get all the article ids that belong to this feed but aren't in the user's junction table...
        ids_not_in_jt_query = select(distinct(Article.id), user_feed, 0).join(Feed, Article.feed_id == Feed.id).where(and_(Feed.id == feed_id, Article.id.notin_(ids_in_jt_query)))

        # 3. insert all the ids into the user's junction table and return their article ids
        result = await db_session.execute(insert(JT_Feed_Article).from_select(["article_id", "feed_id", "is_read"], ids_not_in_jt_query).returning(JT_Feed_Article.article_id))

        await db_session.commit()
        new_articles = [x for x in result.scalars().all()]

        result = await db_session.execute(select(func.count(JT_Feed_Article.id)).join(JT_User_Feed, JT_Feed_Article.feed_id == JT_User_Feed.id).join(User, JT_User_Feed.user_id == User.id).where(and_(and_(JT_User_Feed.feed_id == feed_id, User.id == user_id), JT_Feed_Article.is_read == 0)))
        unread_articles = result.scalars().one()

        await db_session.close()

    len_new_articles = len(new_articles)

    if len_new_articles != 0:
        return Response(response=json.dumps({'status': 'success', 'count': len_new_articles, 'article_ids': new_articles, 'unread_articles': unread_articles}), status=200, mimetype='application/json')
    elif len_new_articles == 0:
        return Response(response=json.dumps({'status': 'unchanged', 'count': len_new_articles, 'article_ids': new_articles, 'unread_articles': unread_articles}), status=200, mimetype='application/json')

    return Response(response=json.dumps({'status': 'unchanged', 'count': 0, 'article_ids': []}), status=304, mimetype='application/json')


@feed_bp.route("/delete_feed", methods=["POST"])
@login_required
async def delete_feed():
    """ Delete the specified feed """
    user_id = session["user_id"]
    request_data = request.get_json()
    feed_id = request_data.get('feed_id', -1)

    async with get_db() as db_session:
        try:
            await db_session.execute(delete(JT_User_Feed).where(
                and_(JT_User_Feed.feed_id == feed_id, JT_User_Feed.user_id == user_id)))

            await db_session.commit()
            await db_session.close()
            return Response(response=json.dumps({'status': 'success'}), status=200, mimetype='application/json')
        except Exception as e:
            logger.info(e)

        await db_session.close()
    return Response(response=json.dumps({'status': 'failure'}), status=400, mimetype='application/json')


@feed_bp.route("/mark_feed_read", methods=["POST"])
@login_required
async def mark_feed_read():
    """ Mark the specified article as read """
    user_id = session["user_id"]
    request_data = request.get_json()

    feed_id = request_data.get('feed_id', -1)
    async with get_db() as db_session:
        try:
            sub_query = (select(JT_Feed_Article.id).join(Feed, JT_Feed_Article.feed_id == Feed.id).join(JT_User_Feed, JT_Feed_Article.feed_id == JT_User_Feed.id).join(
                User, JT_User_Feed.user_id == User.id).where(and_(JT_Feed_Article.feed_id == feed_id, User.id == user_id)).scalar_subquery())
            result = await db_session.execute(update(JT_Feed_Article).where(
                and_(JT_Feed_Article.is_read == 0, JT_Feed_Article.id.in_(sub_query))).values(is_read=1))

            await db_session.commit()
            await db_session.close()
            return Response(response=json.dumps({'status': 'success'}), status=200, mimetype='application/json')
        except Exception as e:
            await db_session.close()
            logger.info(e)
            return Response(response=json.dumps({'status': 'failure'}), status=400, mimetype='application/json')


async def update_feeds(feed_id):
    """ Refresh the articles in the feed(s) """
    async with get_db() as db_session:
        if feed_id is not None:
            result = await db_session.execute(select(Feed).where(Feed.id == feed_id))
        else:
            result = await db_session.execute(select(Feed))

        if feed_id:
            feeds = [result.scalars().one()]
        else:
            feeds = result.scalars().all()


        for f in iter(feeds):
            new_articles = [] # or were going to end up with duplicate articles!

            try:
                last_modified = f.last_modified.astimezone(timezone.utc)
            except:
                last_modified = datetime.fromtimestamp(0, timezone.utc)


            # don't update feeds more frequently than every 15 minutes
            try:
                if (last_modified > (datetime.now(tz=ZoneInfo("UTC"))) - timedelta(minutes=15)) or last_modified > (datetime.now(tz=ZoneInfo("UTC")) - timedelta(minutes=15)):
                    logger.info(f"[{time.strftime("%d/%b/%Y %H:%M:%S", time.localtime())}] Feed id: {f.id}, 0 articles added.")
                    continue
            except:
                pass


            # not all feeds use the 'modified' or 'etag' header, but it saves bandwidth if they do.
            current_feed = feedparser.parse(f.url, etag=f.etag, modified=last_modified, agent='cs50reader/0.0.1 +https://github.com/vivaceuk/CS50-Reader/tree/main')
            try:
                if current_feed.status == 304:
                    # feed hasn't chenged since we last polled it.
                    logger.info(f"[{time.strftime("%d/%b/%Y %H:%M:%S", time.localtime())}] Feed id: {f.id}, 0 articles added.")
                    continue
            except:
                pass

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
                feed_updated = datetime.now(tz=ZoneInfo("UTC"))

            try:
                feed_updated = feed_updated.replace(tzinfo=ZoneInfo("UTC"))
            except:
                feed_updated = datetime.now(tz=ZoneInfo("UTC"))

            try:
                if feed_updated <= last_modified or (etag == f.etag and f.etag != ''):
                    logger.info(f"[{time.strftime("%d/%b/%Y %H:%M:%S", time.localtime())}] Feed id: {f.id}, 0 articles added.")
                    continue
            except Exception as e:
                logger.info(e)

            f.last_updated = datetime.now(tz=ZoneInfo("UTC"))
            f.last_modified = feed_updated.astimezone(timezone.utc)
            f.etag = etag

            purge_date = f.purge_date.astimezone(timezone.utc) if f.purge_date is not None else datetime.fromtimestamp(0, timezone.utc)

            for art in iter(current_feed.entries):
                content = ''
                if 'summary_detail' in art:
                    content = art.summary_detail.value
                elif 'content' in art:
                    content = art.content[0].value

                # if we've seen  this guid, title or content before move on to the next article.
                result = await db_session.execute(select(Article.id).join(Feed, Article.feed_id == Feed.id).where(and_(or_(or_(Article.guid == html.escape(art.id), Article.title == html.escape(
                    art.title)), or_(Article.summary == content, Article.link == art.link)), Feed.id == f.id)).limit(1))
                result = result.scalars().all()

                if len(result) > 0:
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
                        published = datetime.now(timezone.utc)
                except TypeError:
                    published = datetime.now(timezone.utc)

                published = published.astimezone(timezone.utc)

                today = datetime.now(timezone.utc)
                if published > today: # Prevent articles in the future. BBC News I'm looking at you. :-s
                    published.replace(day=today.day, month=today.month, year=today.year)

                # Ignore articles dated before the last purge
                if published < purge_date:
                    continue

                # use beautiful soup to add 'target="_blank"' to links in article (forces them to open in a new tab)
                # also set embeded images to lazy loading

                soup = BeautifulSoup(content, 'html5lib')
                links = soup.find_all('a')
                for link in links:
                    link['class'] = 'link-secondary'
                    link['target'] = '_blank'
                    link['rel'] = 'noopener noreferrer'

                images = soup.find_all('img')
                for image in images:
                    image['loading'] = 'lazy'

                for tag in soup.find_all('script'):
                    tag.extract()

                for tag in soup(text=lambda text: isinstance(text, Comment)):
                    tag.extract()

                try:
                    soup.html.unwrap()
                    soup.head.decompose()
                    soup.body.unwrap()
                    content = str(soup)
                except Exception as e:
                    content = str(soup)

                res = False
                for i in iter(new_articles):
                    if i['link'] == art.link or i['title'] == html.escape(art.title) or i['summary'] == html.escape(content):
                        res = True

                if res:
                    continue

                # the article doesn't exist so add it.
                if art.title and content:
                    new_articles.append({'title': html.escape(art.title), 'summary': html.escape(content), 'link': art.link, 'thumb_url': thumb['url'], 'thumb_height': thumb[
                        'height'], 'thumb_width': thumb['width'], 'is_read': 0, 'published': published, 'guid': html.escape(art.id), 'feed_id': f.id})

            result = list()
            if len(new_articles):
                result = await db_session.execute(insert(Article).returning(Article.id), new_articles)
                await db_session.commit()
            logger.info(f"[{time.strftime("%d/%b/%Y %H:%M:%S", time.localtime())}] Feed id: {f.id}, {len(new_articles)} articles added.")


        await db_session.commit()
        await db_session.close()

@feed_bp.cli.command('update')
@click.option('--id', 'feed_id', type=int, help='Feed id to update. All if not given.')
def update_feeds_cli(feed_id: int):
    """ Update feeds. """
    asyncio.run(update_feeds(feed_id))


async def purge_feeds(feed_id, article_id, days_to_keep, count_articles):
    async with get_db() as db_session:

        if article_id is not None:
            db_session.execute(delete(Article).where(Article.id == article_id))
        else:
            if feed_id is not None:
                result = await db_session.execute(select(Feed).where(Feed.id == feed_id))
            else:
                result = await db_session.execute(select(Feed))

            query = ''

            if feed_id:
                feeds = [result.scalars().one()]
            else:
                feeds = result.scalars().all()

            for f in iter(feeds):
                if count_articles is not None:
                    sub_query = (select(Article.id).join(Feed, Feed.id == Article.feed_id).where(
                            Feed.id == f.id).order_by(Article.published.desc(), Article.guid.desc()).limit(count_articles)).scalar_subquery()
                    query = (delete(Article).where(and_(Article.feed_id == f.id, Article.id.not_in(sub_query))))
                elif days_to_keep is not None:
                    purge_date = datetime.now(tz=ZoneInfo("UTC")) - timedelta(days = days_to_keep)
                    query = (delete(Article).where(and_(Article.feed_id == f.id, Article.published < purge_date)))
                else:
                    days_to_keep = 100
                    purge_date = datetime.now(tz=ZoneInfo("UTC")) - timedelta(days = days_to_keep)
                    query = (delete(Article).where(and_(Article.feed_id == f.id, Article.published < purge_date)))

                await db_session.execute(query)

                if count_articles is not None:
                    # get the published date of the oldest remaining article
                    query = (select(Article.published).join(Feed, Feed.id == Article.feed_id).where(
                            Feed.id == f.id).order_by(Article.published.asc(), Article.guid.asc()).limit(1))

                    # if there aren't any articles set the purge_date to now instead
                    try:
                        result = await db_session.execute(query)
                        f.purge_date = result.scalars().one()
                    except:
                        f.purge_date = datetime.now(timezone.utc)
                else:
                    f.purge_date = purge_date

                logger.info(f"Purged feed id: {f.id}")


        await db_session.commit()
        await db_session.close()

@feed_bp.cli.command('purge-articles')
@click.option('--id', 'feed_id', type=int, help='Feed id to purge. All feeds if not given.')
@click.option('--article-id', 'article_id', type=int, help='Article id to purge.')
@click.option('--days', 'days_to_keep', type=int, help='Number of days worth of articles to keep')
@click.option('--count', 'count_articles', type=int, help='Number of articles to keep')
def purge_feeds_cli(feed_id: int, article_id: int, days_to_keep: int, count_articles: int):
    """ Purge articles from feeds. """
    asyncio.run(purge_feeds(feed_id, article_id, days_to_keep, count_articles))


async def delete_feeds_(feed_id):
    async with get_db() as db_session:
        if feed_id is not None:
            result = await db_session.execute(delete(Feed).where(Feed.id == feed_id))
        else:
            result = await db_session.execute(delete(Feed))

        await db_session.commit()
        await db_session.close()


@feed_bp.cli.command('delete')
@click.option('--id', 'feed_id', type=int, help='Feed id to delete. All feeds if not given.')
def delete_feed_cli(feed_id: int):
    """ Delete selected feed """
    asyncio.run(delete_feeds_(feed_id))
