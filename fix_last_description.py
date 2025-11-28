#!/usr/bin/env python3
import json
import sqlite3

def fix_last_description():
    print("=== FIXING LAST DESCRIPTION ===")
    
    # Загружаем результаты
    with open('missing_descriptions_results.json', 'r', encoding='utf-8') as f:
        missing_descriptions = json.load(f)
    
    # Находим описание для Ni no Kuni
    target_description = ""
    for game in missing_descriptions:
        if "Ni no Kuni II" in game['title']:
            target_description = game['description']
            print(f"Found description: {target_description[:50]}...")
            break
    
    if not target_description:
        print("Description not found!")
        return False
    
    # Подключаемся к базе
    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()
    
    # Ищем точное название в базе
    cursor.execute('SELECT title FROM games WHERE description IS NULL OR description = ""')
    games = cursor.fetchall()
    
    if games:
        exact_title = games[0][0]
        print(f"Exact title in database: {exact_title}")
        
        # Обновляем описание
        cursor.execute("UPDATE games SET description = ? WHERE title = ?", (target_description, exact_title))
        
        if cursor.rowcount > 0:
            conn.commit()
            print("Description updated successfully!")
            
            # Проверяем результат
            cursor.execute("SELECT COUNT(*) FROM games")
            total = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM games WHERE description IS NOT NULL AND description != ''")
            with_descriptions = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM games WHERE genres IS NOT NULL AND genres != '[]' AND genres != ''")
            with_genres = cursor.fetchone()[0]
            
            print(f"\n=== PERFECT RESULTS ===")
            print(f"Total games: {total}")
            print(f"Games with descriptions: {with_descriptions} ({with_descriptions/total*100:.1f}%)")
            print(f"Games with genres: {with_genres} ({with_genres/total*100:.1f}%)")
            
            if with_descriptions == total and with_genres == total:
                print("\nPERFECT! All 510 games now have descriptions AND genres!")
                return True
        else:
            print("Update failed!")
    else:
        print("No games without descriptions found!")
    
    conn.close()
    return False

if __name__ == "__main__":
    success = fix_last_description()
    if success:
        print("\nPERFECT COMPLETION!")
    else:
        print("\nSomething went wrong!")
