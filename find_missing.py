#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('games.db')
cursor = conn.cursor()

cursor.execute('SELECT title FROM games WHERE description IS NULL OR description = ""')
games = cursor.fetchall()

print('Games without descriptions:')
for i, game in enumerate(games):
    print(f'{i+1}. {game[0]}')

conn.close()
