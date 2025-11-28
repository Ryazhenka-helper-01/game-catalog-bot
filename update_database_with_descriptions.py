#!/usr/bin/env python3
"""
Обновление базы данных бота с описаниями игр
"""

import json
import sqlite3
import asyncio
import sys
import os

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Database

async def update_database_with_descriptions():
    """Обновление базы данных с описаниями"""
    
    print("=== UPDATING DATABASE WITH DESCRIPTIONS ===")
    
    # Загружаем игры с описаниями
    try:
        with open('all_switch_games_with_descriptions.json', 'r', encoding='utf-8') as f:
            games_with_descriptions = json.load(f)
        print(f"Loaded {len(games_with_descriptions)} games with descriptions")
    except FileNotFoundError:
        print("ERROR: all_switch_games_with_descriptions.json not found!")
        print("Please run extract_all_descriptions.py first")
        return
    
    # Подключаемся к базе
    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()
    
    # Обновляем описания для существующих игр
    updated_count = 0
    with_descriptions_count = 0
    
    for game in games_with_descriptions:
        try:
            title = game['title']
            description = game.get('description', '')
            found_description = game.get('found_description', False)
            
            # Проверяем, есть ли игра в базе
            cursor.execute("SELECT id FROM games WHERE title = ?", (title,))
            result = cursor.fetchone()
            
            if result:
                game_id = result[0]
                
                # Обновляем описание
                cursor.execute("UPDATE games SET description = ? WHERE id = ?", (description, game_id))
                updated_count += 1
                
                if found_description and description:
                    with_descriptions_count += 1
                    print(f"OK Updated description: {title[:50]}...")
                else:
                    print(f"NO No description: {title[:50]}...")
            else:
                print(f"NOT Game not found in database: {title}")
                
        except Exception as e:
            print(f"ERR Error updating {game.get('title', 'Unknown')}: {e}")
            continue
    
    conn.commit()
    
    # Проверяем результат
    cursor.execute("SELECT COUNT(*) FROM games")
    total_games = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM games WHERE description IS NOT NULL AND description != ''")
    games_with_descriptions = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM games WHERE genres != '[]' AND genres IS NOT NULL")
    games_with_genres = cursor.fetchone()[0]
    
    conn.close()
    
    print("\n=== RESULTS ===")
    print(f"Total games in database: {total_games}")
    print(f"Games updated: {updated_count}")
    print(f"Games with descriptions: {games_with_descriptions}")
    print(f"Games with genres: {games_with_genres}")
    print(f"Description coverage: {(games_with_descriptions/total_games*100):.1f}%")
    print(f"Genre coverage: {(games_with_genres/total_games*100):.1f}%")
    
    return total_games, games_with_descriptions, games_with_genres

async def main():
    await update_database_with_descriptions()

if __name__ == "__main__":
    asyncio.run(main())
