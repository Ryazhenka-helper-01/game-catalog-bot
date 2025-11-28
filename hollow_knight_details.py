#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('games.db')
cursor = conn.cursor()

cursor.execute('SELECT title, url, genres, description FROM games WHERE title LIKE "%Hollow Knight%" ORDER BY title')
games = cursor.fetchall()

print('Hollow Knight games in database:')
print('=' * 60)

for game in games:
    title, url, genres, description = game
    print(f'Title: {title}')
    print(f'URL: {url}')
    print(f'Genres: {genres}')
    if description:
        print(f'Description: {description[:200]}...')
    else:
        print('Description: No description')
    print('-' * 60)

conn.close()
