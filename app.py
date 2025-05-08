from helpers import apology, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from flask_session import Session
from flask import Flask, Response, flash, redirect, render_template, request, session, jsonify
import logging
from datetime import datetime, timedelta
import dateutil
import feedparser
import json
import html
from bs4 import BeautifulSoup
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, select, update, and_, text

from models import User, Feed, Article

engine = create_engine("sqlite:///cs50reader.db")
session_factory = sessionmaker(bind=engine)

logger = logging.getLogger(__name__)

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()



    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        db_session = scoped_session(session_factory)
        user = db_session.scalars(select(User).where(
            User.username == request.form.get("username"))).one()
        db_session.remove()

        # Ensure username exists and password is correct
        if not isinstance(user, User) or not check_password_hash(user.hash, request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = user.id

        # Redirect user to home page
        return redirect("/")
    else:
        # User reached route via GET (as by clicking a link or via redirect)
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirmation")

        # Ensure username was submitted
        if not username:
            return apology("must provide username", 400)
        # Ensure password was submitted
        elif not password or not confirm_password:
            return apology("must provide password", 400)
        elif password != confirm_password:
            return apology("passwords must match", 400)

        hash = generate_password_hash(password, method='scrypt', salt_length=16)

        db_session = scoped_session(session_factory)
        try:
            user = User(username=username, hash=hash)
            db_session.add(user)
            db_session.commit()
            db_session.remove()
        except ValueError:
            return apology("Username already exists", 400)

        flash('You have successfully registerd!')
        return redirect("/login")

    return render_template("register.html")


@app.route("/change_password", methods=["POST"])
@login_required
def change_password():
    """Change user password"""
    user_id = session["user_id"]
    request_data = request.get_json()
    current_password = request_data['current_password']
    new_password = request_data['new_password']
    confirm_password = request_data['confirm_password']

    # get the user's current password hash
    # result = db.execute("SELECT hash FROM users WHERE id=? LIMIT 1", userid)
    db_session = scoped_session(session_factory)
    user = db_session.get(User, user_id)
    hash = user.hash

    # check that the current password matches
    if not check_password_hash(hash, current_password):
        db_session.remove()
        return Response(json.dumps({'status': 'failure', 'error': 'bad password'}), status=400, mimetype='application/json')

    if new_password == '' or confirm_password == '':
        db_session.remove()
        return Response(json.dumps({'status': 'failure', 'error': 'password blank'}), status=400, mimetype='application/json')

    # check that the new password and confirmation match each other
    if not new_password == confirm_password:
        db_session.remove()
        return Response(json.dumps({'status': 'failure', 'error': 'password mismatch'}), status=400, mimetype='application/json')

    # create a new hash, and update the users table
    new_hash = generate_password_hash(new_password, method='scrypt', salt_length=16)
    db_session = scoped_session(session_factory)
    # db.execute("UPDATE users SET hash = ? WHERE id = ? LIMIT 1", new_hash, user_id)

    user.hash = new_hash
    db_session.merge(user)
    db_session.commit()
    db_session.remove()

    return Response(response=json.dumps({'status': 'success'}), status=200, mimetype='application/json')


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """ Show the index page """
    # the GUI is implemented in Javascript/jQuery/Bootstrap in the template.
    return render_template("index.html")


@app.route("/fetch_feeds", methods=["POST"])
@login_required
def fetch_feeds():
    """ Get the list of feeds """
    user_id = session["user_id"]
    # return the feeds for the current user.
    feeds = None

    db_session = scoped_session(session_factory)

    feeds = db_session.query(Feed.id, Feed.title).where(Feed.user_id == user_id).all()

    db_session.remove()

    if feeds is not None:
        return jsonify([row._asdict() for row in feeds])
    else:
        return jsonify({})


@app.route("/fetch_articles", methods=["POST"])
@login_required
def fetch_articles():
    """ Get the list of articles for the feed """
    user_id = session["user_id"]
    request_data = request.get_json()
    feed_id = request_data.get('feed_id', None)
    offset = request_data.get('offset', 0)
    limit = request_data.get('limit', 20)
    article_ids = request_data.get('article_ids', None)
    try:
        show_type = int(request_data.get('show_type'))
    except:
        show_type = 0

    db_session = scoped_session(session_factory)

    # get the articles for the given feed.

    if article_ids:
        entries = db_session.query(Article).join(Feed, Article.feed_id == Feed.id).join(User, Feed.user_id == User.id).where(and_(
            Feed.id == feed_id, Article.id.in_(article_ids))).order_by(Article.published.desc(), Article.guid.desc()).all()
    else:
        if show_type < 2:
            entries = db_session.query(Article).join(Feed, Article.feed_id == Feed.id).join(User, Feed.user_id == User.id).where(and_(Feed.id == feed_id,
                Article.is_read == show_type)).order_by(Article.published.desc(), Article.guid.desc()).offset(offset).limit(limit).all()
        else:
            entries = db_session.query(Article).join(Feed, Article.feed_id == Feed.id).join(User, Feed.user_id == User.id).where(
                Feed.id == feed_id).order_by(Article.published.desc(), Article.guid.desc()).offset(offset).limit(limit).all()

    # unescape the article for display (it was escaped for storage)
    for e in entries:
        e.title = html.unescape(e.title)
        e.summary = html.unescape(e.summary)

    db_session.remove()
    return jsonify([row.to_dict() for row in entries])


@app.route("/add_feed", methods=["POST"])
@login_required
def add_feed():
    """ Add a feed """
    user_id = session["user_id"]
    request_data = request.get_json()
    feed_url = request_data.get('feed_url', None)

    db_session = scoped_session(session_factory)
    image_url = ''

    if feed_url:
        f = feedparser.parse(feed_url)

        if f.feed == {}:
            # the feed is bad.
            db_session.remove()
            return Response(json.dumps({'status': 'failure', 'message': 'bad feed'}), status=400, mimetype='application/json')

        # don't allow duplicate feeds
        result = db_session.scalars(select(Feed).join(
            User, Feed.user_id == User.id).where(Feed.url == feed_url)).one()
        if isinstance(Feed, result):
            db_session.remove()
            return Response(json.dumps({'status': 'failure', 'error': 'feed exists'}), status=400, mimetype='application/json')

        if 'icon' in f.feed:
            image_url = f.feed.get('icon', '')
        elif 'image' in f.feed:
            image_url = f.feed.image.get('url', '')
        else:
            image_url = ''

        # add the feed.
        user = db_session.get(User, user_id)
        feed = Feed(title=f.feed.title, url=feed_url, description=f.feed.description,
                    icon_url=image_url, user_id=user_id)
        user.feeds.append(feed)

        db_session.commit()
        db_session.remove()

        if (feed.id):
            return Response(response=json.dumps({'status': 'success', 'feed_id': feed_id}), status=200, mimetype='application/json')

    return Response(response=json.dumps({'status': 'failure'}), status=400, mimetype='application/json')


@app.route("/update_feed", methods=["POST"])
@login_required
def update_feed():
    """ Refresh the articles in the feed(s) """
    user_id = session["user_id"]
    request_data = request.get_json()
    count = 0
    new_articles = list()

    db_session = scoped_session(session_factory)

    # get the feeds for the current user.
    feed_id = request_data.get('feed_id')
    f = db_session.scalars(select(Feed).where(
        and_(Feed.id == feed_id, Feed.user_id == user_id))).one()


    # don't update feeds more frequently than every 15 minutes
    if (f.last_modified):
        if (dateutil.parser.parse(f.last_modified).isoformat() > ((datetime.now() - timedelta(minutes=15)).isoformat())):
            return Response(response=json.dumps({'status': 'unchanged', 'count': 0, 'article_ids': []}), status=304, mimetype='application/json')

    # not all feeds use the 'modified' or 'etag' header, but it saves bandwidth if they do.
    current_feed = feedparser.parse(f.url, etag=f.etag, modified=f.last_modified)
    if current_feed['status'] == 304:
        # feed hasn't chenged since we last polled it.
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

    feed_updated = feed_updated.isoformat()

    if feed_updated == f.last_modified or (etag == f.etag and etag != ''):
        return Response(response=json.dumps({'status': 'unchanged', 'count': 0, 'article_ids': []}), status=304, mimetype='application/json')

    f.last_modified = feed_updated
    f.last_modified = datetime.now().isoformat()
    f.etag = etag
    db_session.merge(f)
    db_session.commit()

    # try to filter out duplicated articles. BBC News, I'm looking at you!
    # doing this in memory means we're not hitting the database to check every article (which is the other option: think http timeout before we can reply to the request).
    seen_articles = list()
    seen_titles = list()
    seen_content = list()
    for e in f.articles:
        seen_articles.append(e.guid)
        seen_titles.append((e.title)[:20])
        seen_content.append((e.summary)[:20])

    seen_articles.sort()
    seen_titles.sort()
    seen_content.sort()

    for art in current_feed.entries:
        content = ''
        if 'summary_detail' in art:
            content = art.summary_detail.value
        elif 'content' in art:
            content = art.content[0].value

        # if we've seen  this guid, title or content before move on to the next article.
        # we're only looking at the first 20 characters of each to reduce memory requirements.
        if html.escape(art.id) in seen_articles or (html.escape(art.title))[:20] in seen_titles or (html.escape(content))[:20] in seen_content:
            continue

        count = count + 1
        # we haven't seen this article before so add it to the seen articles.
        seen_articles.append(html.escape(art.id))
        seen_titles.append((html.escape(art.title))[:20])
        seen_content.append((html.escape(content))[:20])
        seen_articles.sort()
        seen_titles.sort()
        seen_content.sort()

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
                published = dateutil.parser.parse(published).isoformat()
            elif 'pubDate' in art:
                published = art.get('pubDate')
                published = dateutil.parser.parse(published).isoformat()
            elif 'updated' in art:
                published = art.get('updated')
                published = dateutil.parser.parse(published).isoformat()
            else:
                published = datetime.now().isoformat()
        except TypeError:
            published = datetime.now().isoformat()

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

        # the article doesn't exist so add it.
        new_article = Article(title=html.escape(art.title), summary=html.escape(content), link=art.link,
                                thumb_url=thumb['url'], thumb_height=thumb['height'], thumb_width=thumb['width'], is_read=0, published=published, guid=html.escape(art.id))
        f.articles.append(new_article)
        new_articles.append(new_article)

    del seen_articles, seen_titles, seen_content
    db_session.commit()
    article_ids = [article.id for article in new_articles]
    db_session.remove()

    if len(article_ids) > 0:
        return Response(response=json.dumps({'status': 'success', 'count': count, 'article_ids': article_ids}), status=200, mimetype='application/json')
    else:
        return Response(response=json.dumps({'status': 'unchanged', 'count': 0, 'article_ids': []}), status=304, mimetype='application/json')


@app.route("/delete_feed", methods=["POST"])
@login_required
def delete_feed():
    """ Delete the specified feed """
    user_id = session["user_id"]
    request_data = request.get_json()
    feed_id = request_data.get('feed_id', -1)

    db_session = scoped_session(session_factory)

    feed = db_session.scalars(select(Feed).where(
        and_(Feed.id == feed_id, Feed.user_id == user_id))).one()

    db_session.delete(feed)
    db_session.commit()

    db_session.remove()
    return Response(response=json.dumps({'status': 'success'}), status=200, mimetype='application/json')


@app.route("/mark_article_read", methods=["POST"])
@login_required
def mark_article_read():
    """ Mark the specified article as read """
    user_id = session["user_id"]
    request_data = request.get_json()

    feed_id = request_data.get('feed_id', -1)
    article_id = request_data.get('article_id', -1)

    db_session = scoped_session(session_factory)

    sub_query = (select(Feed.id).where(
        and_(Feed.id == feed_id, Feed.user_id == user_id)).scalar_subquery())
    result = db_session.execute(update(Article).where(
        and_(Article.id == article_id, Feed.id.in_(sub_query))).values(is_read=1))

    db_session.commit()
    db_session.remove()

    if result:
        return Response(response=json.dumps({'status': 'success'}), status=200, mimetype='application/json')
    else:
        return Response(response=json.dumps({'status': 'failure'}), status=400, mimetype='application/json')


@app.route("/mark_feed_read", methods=["POST"])
@login_required
def mark_feed_read():
    """ Mark the specified article as read """
    user_id = session["user_id"]
    request_data = request.get_json()

    feed_id = request_data.get('feed_id', -1)
    db_session = scoped_session(session_factory)

    sub_query = (select(Article.id).join(Feed, Article.feed_id == Feed.id).join(
        User, Feed.user_id == User.id).where(and_(Feed.id == feed_id, User.id == user_id)).scalar_subquery())
    result = db_session.execute(update(Article).where(
        and_(Article.is_read == 0, Article.id.in_(sub_query))).values(is_read=1))

    db_session.commit()
    db_session.remove()

    if result:
        return Response(response=json.dumps({'status': 'success'}), status=200, mimetype='application/json')
    else:
        return Response(response=json.dumps({'status': 'failure'}), status=400, mimetype='application/json')


@app.route("/compact_db", methods=["POST"])
@login_required
def compact_db():
    """ Compact the database """
    try:
        db_session = scoped_session(session_factory)
        db_session.execute(text("COMMIT"))
        result = db_session.execute(text("VACUUM"))
        db_session.commit()
        db_session.remove()
        if result:
            return Response(response=json.dumps({'status': 'success'}), status=200, mimetype='application/json')
    except:
        pass

    return Response(response=json.dumps({'status': 'failure'}), status=400, mimetype='application/json')
