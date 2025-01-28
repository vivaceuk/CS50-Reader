from cs50 import SQL
from bs4 import BeautifulSoup
import html

db = SQL("sqlite:///cs50reader.db")

articles = db.execute('SELECT id, summary FROM articles')

for a in articles:
    soup = BeautifulSoup(html.unescape(a['summary']), 'html.parser')
    #links = soup.find_all('a')
    #for link in links:
    #    link['target'] = '_blank'
    #    link['rel'] = 'noopener noreferrer'

    images = soup.find_all('img')
    for image in images:
        image['loading'] = 'lazy'

    db.execute('UPDATE articles SET summary=? WHERE id=?', html.escape(soup.prettify()), a['id'])
