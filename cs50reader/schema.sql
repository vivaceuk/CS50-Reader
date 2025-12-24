CREATE TABLE users (
        id INTEGER NOT NULL, 
        username VARCHAR NOT NULL, 
        hash VARCHAR NOT NULL, 
        PRIMARY KEY (id), 
        UNIQUE (username)
);
CREATE UNIQUE INDEX ix_users_username ON users (username);
CREATE TABLE feeds (
        id INTEGER NOT NULL, 
        title VARCHAR NOT NULL, 
        url VARCHAR(255) NOT NULL, 
        description VARCHAR, 
        icon_url VARCHAR, 
        etag VARCHAR, 
        last_modified DATETIME, 
        last_updated DATETIME, 
        purge_date DATETIME, 
        PRIMARY KEY (id)
);
CREATE TABLE articles (
        id INTEGER NOT NULL, 
        title VARCHAR NOT NULL, 
        summary TEXT NOT NULL, 
        link VARCHAR(255) NOT NULL, 
        thumb_url VARCHAR, 
        thumb_height INTEGER, 
        thumb_width INTEGER, 
        published DATETIME NOT NULL, 
        guid VARCHAR NOT NULL, 
        feed_id INTEGER NOT NULL, 
        PRIMARY KEY (id), 
        FOREIGN KEY(feed_id) REFERENCES feeds (id)
);
CREATE INDEX ix_articles_feed_id ON articles (feed_id);
CREATE TABLE jt_user_feed (
        id INTEGER NOT NULL, 
        feed_id INTEGER NOT NULL, 
        user_id INTEGER NOT NULL, 
        PRIMARY KEY (id), 
        FOREIGN KEY(feed_id) REFERENCES feeds (id), 
        FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX ix_jt_user_feed_user_id ON jt_user_feed (user_id);
CREATE INDEX ix_jt_user_feed_feed_id ON jt_user_feed (feed_id);
CREATE TABLE jt_feed_article (
        id INTEGER NOT NULL, 
        feed_id INTEGER NOT NULL, 
        article_id INTEGER NOT NULL, 
        is_read INTEGER NOT NULL, 
        favourite INTEGER NOT NULL, 
        PRIMARY KEY (id), 
        FOREIGN KEY(feed_id) REFERENCES jt_user_feed (id), 
        FOREIGN KEY(article_id) REFERENCES articles (id)
);
