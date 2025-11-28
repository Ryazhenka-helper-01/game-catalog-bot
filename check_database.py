#!/usr/bin/env python3
"""
Проверка базы данных
"""

import sqlite3
import json

def check_database():
    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM games")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM games WHERE genres != '[]' AND genres IS NOT NULL")
    with_genres = cursor.fetchone()[0]
    
    print(f"Total games: {total}")
    print(f"With genres: {with_genres}")
    print(f"Percentage: {with_genres/total*100:.1f}%")
    
    # Получаем все уникальные жанры
    cursor.execute("SELECT genres FROM games WHERE genres != '[]' AND genres IS NOT NULL")
    all_genres_data = cursor.fetchall()
    
    all_unique_genres = set()
    for (genres_str,) in all_genres_data:
        try:
            genres = json.loads(genres_str)
            all_unique_genres.update(genres)
        except:
            continue
    
    print(f"Unique genres: {len(all_unique_genres)}")
    
    # Топ жанров
    genre_counts = {}
    for genre in all_unique_genres:
        count = conn.execute("SELECT COUNT(*) FROM games WHERE genres LIKE ?", (f'%{genre}%',)).fetchone()[0]
        genre_counts[genre] = count
    
    sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)
    print("Top-10 genres:")
    for i, (genre, count) in enumerate(sorted_genres[:10], 1):
        print(f"   {i:2d}. {genre}: {count} games")
    
    conn.close()

if __name__ == "__main__":
    check_database()
