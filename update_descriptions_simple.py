#!/usr/bin/env python3
"""
Простое обновление описаний в базе данных
"""

import json
import sqlite3

def update_descriptions():
    """Обновление описаний из файла all_switch_games_with_descriptions.json"""
    
    print("=== UPDATING DESCRIPTIONS ===")
    
    # Load descriptions
    try:
        with open('all_switch_games_with_descriptions.json', 'r', encoding='utf-8') as f:
            games_with_descriptions = json.load(f)
        print(f"Loaded {len(games_with_descriptions)} games with descriptions")
    except FileNotFoundError:
        print("ERROR: File all_switch_games_with_descriptions.json not found")
        return False
    
    # Подключаемся к базе
    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()
    
    updated_count = 0
    
    for game in games_with_descriptions:
        title = game.get('title', '')
        description = game.get('description', '')
        
        if title and description:
            cursor.execute("UPDATE games SET description = ? WHERE title = ?", (description, title))
            if cursor.rowcount > 0:
                updated_count += 1
                if updated_count % 50 == 0:
                    print(f"Updated {updated_count} games...")
    
    conn.commit()
    
    # Проверяем результат
    cursor.execute("SELECT COUNT(*) FROM games")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM games WHERE description IS NOT NULL AND description != ''")
    with_descriptions = cursor.fetchone()[0]
    
    print(f"\n=== RESULT ===")
    print(f"Total games: {total}")
    print(f"Descriptions updated: {updated_count}")
    print(f"Games with descriptions: {with_descriptions} ({with_descriptions/total*100:.1f}%)")
    
    conn.close()
    return True

if __name__ == "__main__":
    update_descriptions()
