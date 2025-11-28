#!/usr/bin/env python3
"""
Полный анализ базы данных - игры без описаний и жанров
"""

import json
import sqlite3
import os

def complete_analysis():
    """Полный анализ базы данных"""
    
    print("=== COMPLETE DATABASE ANALYSIS ===")
    
    # Проверяем базу данных
    try:
        conn = sqlite3.connect('games.db')
        cursor = conn.cursor()
        
        # Общая статистика
        cursor.execute("SELECT COUNT(*) FROM games")
        total_games = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM games WHERE description IS NOT NULL AND description != ''")
        with_descriptions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM games WHERE genres IS NOT NULL AND genres != '[]' AND genres != ''")
        with_genres = cursor.fetchone()[0]
        
        print(f"Total games: {total_games}")
        print(f"With descriptions: {with_descriptions} ({with_descriptions/total_games*100:.1f}%)")
        print(f"With genres: {with_genres} ({with_genres/total_games*100:.1f}%)")
        print()
        
        # Игры БЕЗ описаний
        cursor.execute("""
            SELECT title, url FROM games 
            WHERE description IS NULL OR description = '' 
            ORDER BY title
        """)
        games_without_desc = cursor.fetchall()
        
        print(f"=== GAMES WITHOUT DESCRIPTIONS ({len(games_without_desc)} games) ===")
        for i, (title, url) in enumerate(games_without_desc, 1):
            print(f"{i:3d}. {title}")
            print(f"     URL: {url}")
        print()
        
        # Игры БЕЗ жанров
        cursor.execute("""
            SELECT title, url FROM games 
            WHERE genres IS NULL OR genres = '[]' OR genres = ''
            ORDER BY title
        """)
        games_without_genres = cursor.fetchall()
        
        print(f"=== GAMES WITHOUT GENRES ({len(games_without_genres)} games) ===")
        for i, (title, url) in enumerate(games_without_genres, 1):
            print(f"{i:3d}. {title}")
            print(f"     URL: {url}")
        print()
        
        # Игры БЕЗ описаний И БЕЗ жанров
        cursor.execute("""
            SELECT title, url FROM games 
            WHERE (description IS NULL OR description = '') 
            AND (genres IS NULL OR genres = '[]' OR genres = '')
            ORDER BY title
        """)
        games_without_both = cursor.fetchall()
        
        print(f"=== GAMES WITHOUT DESCRIPTIONS AND GENRES ({len(games_without_both)} games) ===")
        for i, (title, url) in enumerate(games_without_both, 1):
            print(f"{i:3d}. {title}")
            print(f"     URL: {url}")
        print()
        
        # Проверяем исходные файлы
        print("=== SOURCE FILES ANALYSIS ===")
        
        # Проверяем all_switch_games_complete.json
        if os.path.exists('all_switch_games_complete.json'):
            with open('all_switch_games_complete.json', 'r', encoding='utf-8') as f:
                complete_games = json.load(f)
            
            unique_complete = {}
            for game in complete_games:
                title = game['title']
                if title not in unique_complete:
                    unique_complete[title] = game
            
            print(f"all_switch_games_complete.json: {len(unique_complete)} unique games")
            
            # Игры с жанрами в complete
            with_genres_complete = sum(1 for game in unique_complete.values() if game.get('genres'))
            print(f"Games with genres in complete: {with_genres_complete}")
        
        # Проверяем all_switch_games_with_descriptions.json
        if os.path.exists('all_switch_games_with_descriptions.json'):
            with open('all_switch_games_with_descriptions.json', 'r', encoding='utf-8') as f:
                desc_games = json.load(f)
            
            unique_desc = {}
            for game in desc_games:
                title = game['title']
                if title not in unique_desc:
                    unique_desc[title] = game
            
            print(f"all_switch_games_with_descriptions.json: {len(unique_desc)} unique games")
            
            # Игры с описаниями в descriptions
            with_desc_desc = sum(1 for game in unique_desc.values() if game.get('description'))
            print(f"Games with descriptions in descriptions: {with_desc_desc}")
            
            # Игры с жанрами в descriptions
            with_genres_desc = sum(1 for game in unique_desc.values() if game.get('genres'))
            print(f"Games with genres in descriptions: {with_genres_desc}")
        
        conn.close()
        
        # Итоги
        print("=== SUMMARY ===")
        print(f"Games needing descriptions: {len(games_without_desc)}")
        print(f"Games needing genres: {len(games_without_genres)}")
        print(f"Games needing both: {len(games_without_both)}")
        
        return {
            'total': total_games,
            'without_descriptions': len(games_without_desc),
            'without_genres': len(games_without_genres),
            'without_both': len(games_without_both)
        }
        
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    complete_analysis()
