__all__ = ['db', 'views', 'util']

from util.helpers import login_required
from flask_session import Session
from cachelib.file import FileSystemCache
from flask import Flask, render_template, redirect, url_for
from flask.cli import FlaskGroup
import click
import os, logging, asyncio

from views import auth, feed, article, util
from db import db


def create_app(test_config=None):
    logging.basicConfig(level=logging.INFO)
    #logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    logger = logging.getLogger(__name__)

    # create and configure the app
    app = Flask(__name__) #, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE= "sqlite+aiosqlite:///" + os.path.join(app.instance_path, "cs50reader.db"),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    db.init_app(app)

    # Configure session to use cachelib (instead of signed cookies)
    app.config["SESSION_TYPE"] = 'cachelib'
    app.config["SESSION_SERIALIZATION_FORMAT"] = 'json'
    app.config["SESSION_CACHELIB"] = FileSystemCache(cache_dir=os.path.join(app.instance_path, "flask_session"), threshold=500, default_timeout=0)

    Session(app)


    @app.after_request
    def after_request(response):
        """Ensure responses aren't cached"""
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response


    app.register_blueprint(auth.auth_bp)
    app.register_blueprint(feed.feed_bp)
    app.register_blueprint(article.article_bp)
    app.register_blueprint(util.util_bp)


    @app.route("/", methods=["GET", "POST"])
    @login_required
    def index():
        """ Show the index page """
        # the GUI is implemented in Javascript/jQuery/Bootstrap in the template.
        return render_template("index.html")


    @app.route("/.well-known/appspecific/com.chrome.devtools.json")
    def google_is_annoying():
        return render_template("com.chrome.devtools.json")


    @app.route("/favicon.ico", methods=["GET", "POST"])
    def favicon():
        return redirect(url_for('static', filename='favicon.ico'))


    return app


app = create_app()
