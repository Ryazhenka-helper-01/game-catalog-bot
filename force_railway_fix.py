#!/usr/bin/env python3
"""
Принудительное исправление базы данных Railway
"""

import json
import sqlite3
import os

def force_fix_database():
    """Принудительное исправление базы данных"""
    
    print("=== FORCE FIXING RAILWAY DATABASE ===")
    
    # Проверяем доступные файлы
    files_to_check = [
        'all_switch_games_with_descriptions.json',
        'all_switch_games_complete.json'
    ]
    
    games_file = None
    for file in files_to_check:
        if os.path.exists(file):
            games_file = file
            print(f"Found file: {file}")
            break
    
    if not games_file:
        print("ERROR: No games file found!")
        return False
    
    # Загружаем игры
    try:
        with open(games_file, 'r', encoding='utf-8') as f:
            all_games = json.load(f)
        print(f"Loaded {len(all_games)} games from {games_file}")
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
    
    # Подключаемся к базе
    try:
        conn = sqlite3.connect('games.db')
        cursor = conn.cursor()
        
        # Полностью очищаем базу
        cursor.execute("DELETE FROM games")
        conn.commit()
        print("Database cleared")
        
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
        print(f"Database error: {e}")
        return False

if __name__ == "__main__":
    success = force_fix_database()
    if success:
        print("Database fixed successfully!")
    else:
        print("Failed to fix database!")
