CREATE TABLE users (
	id INTEGER NOT NULL, 
	username VARCHAR NOT NULL, 
	hash VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (username)
);
CREATE TABLE feeds (
	id INTEGER NOT NULL, 
	title VARCHAR NOT NULL, 
	url VARCHAR(255) NOT NULL, 
	description VARCHAR, 
	icon_url VARCHAR, 
	etag VARCHAR, 
	last_modified DATETIME, 
	last_updated DATETIME, 
	user_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
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
	is_read INTEGER NOT NULL, 
	guid VARCHAR NOT NULL, 
	feed_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(feed_id) REFERENCES feeds (id)
);
CREATE UNIQUE INDEX ix_users_username ON users (username);
CREATE INDEX ix_feeds_user_id ON feeds (user_id);
CREATE INDEX ix_feeds_url ON feeds (url);
CREATE INDEX ix_articles_feed_id ON articles (feed_id);
CREATE INDEX ix_articles_link ON articles (link);
