#!/usr/bin/env python3
"""
Агрессивное исправление базы данных для Railway
"""

import json
import sqlite3
import os

def aggressive_fix():
    """Агрессивное исправление базы данных"""
    
    print("=== AGGRESSIVE DATABASE FIX ===")
    
    # Проверяем текущее состояние
    try:
        conn = sqlite3.connect('games.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM games")
        current_count = cursor.fetchone()[0]
        print(f"Current games in database: {current_count}")
        
        if current_count >= 500:
            print("Database already has enough games!")
            conn.close()
            return True
    except Exception as e:
        print(f"Error checking database: {e}")
        return False
    
    # Ищем файл с играми
    games_file = None
    for file in ['all_switch_games_with_descriptions.json', 'all_switch_games_complete.json']:
        if os.path.exists(file):
            games_file = file
            print(f"Found games file: {file}")
            break
    
    if not games_file:
        print("ERROR: No games file found!")
        return False
    
    # Загружаем игры
    try:
        with open(games_file, 'r', encoding='utf-8') as f:
            all_games = json.load(f)
        print(f"Loaded {len(all_games)} games")
    except Exception as e:
        print(f"Error loading games: {e}")
        return False
    
    # Создаем уникальные игры
    unique_games = {}
    for game in all_games:
        title = game['title']
        if title not in unique_games:
            unique_games[title] = game
    
    print(f"Unique games: {len(unique_games)}")
    
    # Полностью пересоздаем базу
    try:
        # Удаляем старый файл базы
        if os.path.exists('games.db'):
            os.remove('games.db')
            print("Removed old database file")
        
        # Создаем новую базу
        conn = sqlite3.connect('games.db')
        cursor = conn.cursor()
        
        # Создаем таблицу
        cursor.execute('''
            CREATE TABLE games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT UNIQUE NOT NULL,
                url TEXT NOT NULL,
                genres TEXT DEFAULT '[]',
                description TEXT DEFAULT '',
                rating TEXT DEFAULT '',
                image_url TEXT DEFAULT '',
                screenshots TEXT DEFAULT '[]',
                release_date TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Добавляем все игры
        added_count = 0
        for title, game in unique_games.items():
            try:
                url = game['url']
                genres = json.dumps(game['genres'], ensure_ascii=False) if game.get('genres') else '[]'
                description = game.get('description', '')
                
                cursor.execute('''
                    INSERT INTO games (title, url, genres, description, rating, image_url, screenshots, release_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (title, url, genres, description, None, None, None, None))
                
                added_count += 1
                
            except Exception as e:
                print(f"Error adding {title}: {e}")
                continue
        
        conn.commit()
        
        # Проверяем результат
        cursor.execute("SELECT COUNT(*) FROM games")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM games WHERE description IS NOT NULL AND description != ''")
        with_desc = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM games WHERE genres != '[]' AND genres IS NOT NULL")
        with_genres = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"=== RESULTS ===")
        print(f"Total games: {total}")
        print(f"With descriptions: {with_desc}")
        print(f"With genres: {with_genres}")
        print(f"Description coverage: {(with_desc/total*100):.1f}%")
        print(f"Genre coverage: {(with_genres/total*100):.1f}%")
        
        return total >= 500
        
    except Exception as e:
        print(f"Database recreation error: {e}")
        return False

if __name__ == "__main__":
    success = aggressive_fix()
    if success:
        print("Database fixed aggressively!")
    else:
        print("Failed to fix database!")
