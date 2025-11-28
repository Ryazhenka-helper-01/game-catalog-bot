#!/usr/bin/env python3
"""
ГАРАНТИРОВАННОЕ исправление базы данных для Railway
"""

import json
import sqlite3
import os

def guaranteed_railway_fix():
    """Гарантированное исправление базы для Railway"""
    
    print("=== GUARANTEED RAILWAY DATABASE FIX ===")
    
    # 1. Проверяем текущее состояние
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
        else:
            print(f"Database needs fixing: only {current_count} games")
        conn.close()
    except Exception as e:
        print(f"Error checking database: {e}")
    
    # 2. Ищем исходные данные
    sources = [
        'all_switch_games_with_descriptions.json',
        'all_switch_games_complete.json'
    ]
    
    games_data = None
    source_file = None
    
    for file in sources:
        if os.path.exists(file):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    games_data = json.load(f)
                source_file = file
                print(f"Found source: {file} ({len(games_data)} games)")
                break
            except Exception as e:
                print(f"Error reading {file}: {e}")
                continue
    
    if not games_data:
        print("ERROR: No source data found!")
        return False
    
    # 3. Создаем уникальные игры
    unique_games = {}
    for game in games_data:
        title = game['title']
        if title not in unique_games:
            unique_games[title] = game
    
    print(f"Unique games: {len(unique_games)}")
    
    # 4. ПОЛНОСТЬЮ пересоздаем базу
    try:
        # Удаляем старый файл
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
                genres = json.dumps(game.get('genres', []), ensure_ascii=False)
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
        
        cursor.execute("SELECT COUNT(*) FROM games WHERE genres IS NOT NULL AND genres != '[]' AND genres != ''")
        with_genres = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"=== GUARANTEED FIX RESULTS ===")
        print(f"Total games: {total}")
        print(f"With descriptions: {with_desc} ({with_desc/total*100:.1f}%)")
        print(f"With genres: {with_genres} ({with_genres/total*100:.1f}%)")
        print(f"Source file: {source_file}")
        
        return total >= 500
        
    except Exception as e:
        print(f"Database recreation error: {e}")
        return False

if __name__ == "__main__":
    success = guaranteed_railway_fix()
    if success:
        print("Railway database fix completed successfully!")
    else:
        print("Railway database fix failed!")
