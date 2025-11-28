#!/usr/bin/env python3
"""
Исправление бота - добавляем все 510 игр с правильными жанрами
"""

import json
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_bot_database():
    """Исправить базу данных бота нашими 510 играми"""
    
    # Загружаем наши 510 игр
    with open('all_switch_games_complete.json', 'r', encoding='utf-8') as f:
        all_games = json.load(f)
    
    logger.info(f"📊 Загружено игр из файла: {len(all_games)}")
    
    # Создаем уникальные игры
    unique_games = {}
    for game in all_games:
        title = game['title']
        if title not in unique_games:
            unique_games[title] = game
    
    logger.info(f"🎯 Уникальных игр: {len(unique_games)}")
    
    # Подключаемся к базе
    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()
    
    # Удаляем старые данные
    cursor.execute("DELETE FROM games")
    conn.commit()
    logger.info("🗑️ Старые данные удалены")
    
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
                logger.info(f"📊 Добавлено {added_count}/{len(unique_games)} игр...")
                
        except Exception as e:
            logger.error(f"❌ Ошибка добавления {title}: {e}")
            continue
    
    conn.commit()
    
    # Проверяем результат
    cursor.execute("SELECT COUNT(*) FROM games")
    final_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM games WHERE genres != '[]' AND genres IS NOT NULL")
    with_genres = cursor.fetchone()[0]
    
    conn.close()
    
    logger.info("✅ РЕЗУЛЬТАТЫ:")
    logger.info(f"📊 Добавлено игр: {added_count}")
    logger.info(f"📊 Финальное количество в базе: {final_count}")
    logger.info(f"🏷️ Игр с жанрами: {with_genres}")
    logger.info(f"📈 Процент с жанрами: {(with_genres/final_count*100):.1f}%")
    
    return final_count, with_genres

def show_final_stats():
    """Показать финальную статистику"""
    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM games")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM games WHERE genres != '[]' AND genres IS NOT NULL")
    with_genres = cursor.fetchone()[0]
    
    # Получаем все уникальные жанры
    cursor.execute("SELECT genres FROM games WHERE genres != '[]' AND genres IS NOT NULL")
    all_genres_data = cursor.fetchall()
    
    all_unique_genres = set()
    for (genres_str,) in all_genres_data:
        try:
            genres = json.loads(genres_str)
            all_unique_genres.update(genres)
        except:
            continue
    
    conn.close()
    
    logger.info("=" * 80)
    logger.info("🎯 ФИНАЛЬНАЯ СТАТИСТИКА БОТА:")
    logger.info(f"📊 Всего игр в боте: {total}")
    logger.info(f"🏷️ Игр с жанрами: {with_genres}")
    logger.info(f"📈 Процент с жанрами: {(with_genres/total*100):.1f}%")
    logger.info(f"🎯 Уникальных жанров: {len(all_unique_genres)}")
    
    logger.info("")
    logger.info("🏷️ Топ-10 жанров:")
    genre_counts = {}
    for genre in all_unique_genres:
        conn = sqlite3.connect('games.db')
        count = conn.execute("SELECT COUNT(*) FROM games WHERE genres LIKE ?", (f'%{genre}%',)).fetchone()[0]
        conn.close()
        genre_counts[genre] = count
    
    sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)
    for genre, count in sorted_genres[:10]:
        logger.info(f"   📊 {genre}: {count} игр")

def main():
    logger.info("🚀 ИСПРАВЛЕНИЕ БОТА - ДОБАВЛЕНИЕ ВСЕХ 510 ИГР!")
    
    # Исправляем базу
    total, with_genres = fix_bot_database()
    
    # Показываем статистику
    show_final_stats()
    
    logger.info("🎉 БОТ ИСПРАВЛЕН И ГОТОВ К РАБОТЕ!")

if __name__ == "__main__":
    main()
