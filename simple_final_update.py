#!/usr/bin/env python3
import json
import sqlite3

def final_update():
    print("=== FINAL DATABASE UPDATE ===")
    
    # Загружаем результаты
    with open('missing_descriptions_results.json', 'r', encoding='utf-8') as f:
        missing_descriptions = json.load(f)
    
    with open('missing_genre_result.json', 'r', encoding='utf-8') as f:
        missing_genre = json.load(f)
    
    print(f"Loaded {len(missing_descriptions)} missing descriptions")
    print(f"Loaded missing genre for: {missing_genre['title']}")
    
    # Подключаемся к базе
    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()
    
    updated_desc = 0
    updated_genres = 0
    
    # Обновляем описания
    print("\n=== UPDATING DESCRIPTIONS ===")
    for game in missing_descriptions:
        title = game['title']
        description = game['description']
        
        cursor.execute("UPDATE games SET description = ? WHERE title = ?", (description, title))
        
        if cursor.rowcount > 0:
            updated_desc += 1
            print(f"OK: {title[:40]}...")
        else:
            print(f"NOT FOUND: {title[:40]}...")
    
    # Обновляем жанры
    print("\n=== UPDATING GENRES ===")
    title = missing_genre['title']
    genres = json.dumps(missing_genre['genres'], ensure_ascii=False)
    
    cursor.execute("UPDATE games SET genres = ? WHERE title = ?", (genres, title))
    
    if cursor.rowcount > 0:
        updated_genres += 1
        print(f"OK: {title}")
    else:
        print(f"NOT FOUND: {title}")
    
    conn.commit()
    
    # Проверяем результат
    cursor.execute("SELECT COUNT(*) FROM games")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM games WHERE description IS NOT NULL AND description != ''")
    with_descriptions = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM games WHERE genres IS NOT NULL AND genres != '[]' AND genres != ''")
    with_genres = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\n=== FINAL RESULTS ===")
    print(f"Total games: {total}")
    print(f"Descriptions updated: {updated_desc}")
    print(f"Genres updated: {updated_genres}")
    print(f"Games with descriptions: {with_descriptions} ({with_descriptions/total*100:.1f}%)")
    print(f"Games with genres: {with_genres} ({with_genres/total*100:.1f}%)")
    
    # Проверяем идеальность
    if with_descriptions == total and with_genres == total:
        print("\nPERFECT! All games now have descriptions AND genres!")
        return True
    else:
        missing_desc_count = total - with_descriptions
        missing_genres_count = total - with_genres
        print(f"\nStill missing:")
        print(f"   - {missing_desc_count} descriptions")
        print(f"   - {missing_genres_count} genres")
        return False

if __name__ == "__main__":
    success = final_update()
    if success:
        print("\nDatabase update completed successfully!")
    else:
        print("\nDatabase update had issues!")
