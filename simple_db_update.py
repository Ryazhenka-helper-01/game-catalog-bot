#!/usr/bin/env python3
import json
import sqlite3

def update_database():
    print("=== UPDATING DATABASE WITH DESCRIPTIONS ===")
    
    # Load games with descriptions
    with open('all_switch_games_with_descriptions.json', 'r', encoding='utf-8') as f:
        games = json.load(f)
    
    print(f"Loaded {len(games)} games")
    
    # Connect to database
    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()
    
    updated = 0
    with_desc = 0
    
    for game in games:
        title = game['title']
        description = game.get('description', '')
        found_desc = game.get('found_description', False)
        
        # Check if game exists
        cursor.execute("SELECT id FROM games WHERE title = ?", (title,))
        result = cursor.fetchone()
        
        if result:
            game_id = result[0]
            cursor.execute("UPDATE games SET description = ? WHERE id = ?", (description, game_id))
            updated += 1
            
            if found_desc and description:
                with_desc += 1
                print(f"OK: {title[:30]}...")
            else:
                print(f"NO DESC: {title[:30]}...")
        else:
            print(f"NOT FOUND: {title[:30]}...")
    
    conn.commit()
    
    # Check results
    cursor.execute("SELECT COUNT(*) FROM games")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM games WHERE description IS NOT NULL AND description != ''")
    with_descriptions = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM games WHERE genres != '[]' AND genres IS NOT NULL")
    with_genres = cursor.fetchone()[0]
    
    conn.close()
    
    print("\n=== RESULTS ===")
    print(f"Total games: {total}")
    print(f"Updated: {updated}")
    print(f"With descriptions: {with_descriptions}")
    print(f"With genres: {with_genres}")
    print(f"Description coverage: {(with_descriptions/total*100):.1f}%")
    print(f"Genre coverage: {(with_genres/total*100):.1f}%")

if __name__ == "__main__":
    update_database()
