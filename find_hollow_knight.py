#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('games.db')
cursor = conn.cursor()

cursor.execute('SELECT title, url, genres FROM games WHERE title LIKE "%Hollow Knight%"')
games = cursor.fetchall()

print('Hollow Knight search results:')
if games:
    for i, game in enumerate(games):
        print(f'{i+1}. {game[0]}')
        print(f'   URL: {game[1]}')
        print(f'   Genres: {game[2]}')
else:
    print('Hollow Knight not found in database!')

conn.close()
