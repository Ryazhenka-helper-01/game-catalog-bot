#!/usr/bin/env python3
"""
Исправление базы данных на Railway
"""

import sqlite3
import json
import asyncio
import sys
import os

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Database

async def fix_railway_database():
    """Исправление базы данных Railway"""
    
    print("=== FIXING RAILWAY DATABASE ===")
    
    # Загружаем наши 510 игр
    try:
        with open('all_switch_games_complete.json', 'r', encoding='utf-8') as f:
            all_games = json.load(f)
        print(f"Loaded {len(all_games)} games from JSON")
    except FileNotFoundError:
        print("ERROR: all_switch_games_complete.json not found!")
        return
    
    # Создаем уникальные игры
    unique_games = {}
    for game in all_games:
        title = game['title']
        if title not in unique_games:
            unique_games[title] = game
    
    print(f"Unique games: {len(unique_games)}")
    
    # Подключаемся к базе
    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()
    
    # Удаляем старые данные
    cursor.execute("DELETE FROM games")
    conn.commit()
    print("Old data deleted")
    
    # Добавляем все 510 игр
    added_count = 0
    with_genres_count = 0
    
    for title, game in unique_games.items():
        try:
            url = game['url']
            genres = json.dumps(game['genres'], ensure_ascii=False) if game['genres'] else '[]'
            
            cursor.execute('''
                INSERT INTO games (title, url, genres, description, rating, image_url, screenshots, release_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (title, url, genres, None, None, None, None, None))
            
            added_count += 1
            if game['found_genres']:
                with_genres_count += 1
            
            if added_count % 100 == 0:
                print(f"Added {added_count}/{len(unique_games)} games...")
                
        except Exception as e:
            print(f"Error adding {title}: {e}")
            continue
    
    conn.commit()
    
    # Проверяем результат
    cursor.execute("SELECT COUNT(*) FROM games")
    final_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM games WHERE genres != '[]' AND genres IS NOT NULL")
    with_genres = cursor.fetchone()[0]
    
    conn.close()
    
    print("=== RESULTS ===")
    print(f"Added games: {added_count}")
    print(f"Final count: {final_count}")
    print(f"With genres: {with_genres}")
    print(f"Percentage: {(with_genres/final_count*100):.1f}%")
    
    return final_count, with_genres

async def main():
    await fix_railway_database()

if __name__ == "__main__":
    asyncio.run(main())
