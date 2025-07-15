from cs50reader.helpers import login_required
from flask_session import Session
from flask import Flask, render_template
import os, logging, asyncio, atexit, signal

from cs50reader import auth, feed, article, util
from cs50reader.db import engine


def create_app(test_config=None):
    logging.basicConfig(level=logging.INFO)
    # logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    logger = logging.getLogger(__name__)

    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE= "sqlite+aiosqlite:///" + os.path.join(os.path.dirname(__file__), "cs50reader.db"),
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


    # Configure session to use filesystem (instead of signed cookies)
    app.config["SESSION_FILE_DIR"] = os.path.join(os.path.dirname(__file__), "flask_session")
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


    app.register_blueprint(auth.bp)
    app.register_blueprint(feed.bp)
    app.register_blueprint(article.bp)
    app.register_blueprint(util.bp)


    @app.route("/", methods=["GET", "POST"])
    @login_required
    def index():
        """ Show the index page """
        # the GUI is implemented in Javascript/jQuery/Bootstrap in the template.
        return render_template("index.html")


    @app.route("/.well-known/appspecific/com.chrome.devtools.json")
    def google_is_annoying():
        return render_template("com.chrome.devtools.json")


    def close_db():
        logging.info("close_db() called.")

        async def wrapped():
            global engine
            if engine is not None:
                db.engine.dispose()
        asyncio.run(wrapped())

    atexit.register(close_db)
    signal.signal(signal.SIGINT, close_db)

    return app
