#!/usr/bin/env python3
"""
Исправление лимита базы данных - добавляем все 510 игр
"""

import json
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_database_limit():
    """Исправить проблему с лимитом базы данных"""
    
    # Загружаем все игры
    with open('all_switch_games_complete.json', 'r', encoding='utf-8') as f:
        all_games = json.load(f)
    
    logger.info(f"📊 Всего игр в файле: {len(all_games)}")
    
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
    
    # Проверяем текущее состояние
    cursor.execute("SELECT COUNT(*) FROM games")
    current_count = cursor.fetchone()[0]
    logger.info(f"📊 Текущее количество игр в базе: {current_count}")
    
    # Удаляем все данные
    cursor.execute("DELETE FROM games")
    conn.commit()
    logger.info("🗑️ База очищена")
    
    # Добавляем все игры без лимита
    added_count = 0
    errors = 0
    
    for title, game in unique_games.items():
        try:
            url = game['url']
            genres = json.dumps(game['genres'], ensure_ascii=False) if game['genres'] else '[]'
            
            cursor.execute('''
                INSERT INTO games (title, url, genres)
                VALUES (?, ?, ?)
            ''', (title, url, genres))
            
            added_count += 1
            
            if added_count % 100 == 0:
                logger.info(f"📊 Добавлено {added_count}/{len(unique_games)} игр...")
                
        except Exception as e:
            errors += 1
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
    logger.info(f"❌ Ошибок: {errors}")
    logger.info(f"📈 Процент с жанрами: {(with_genres/final_count*100):.1f}%")
    
    return final_count, with_genres

def verify_all_games_added():
    """Проверить что все игры добавлены"""
    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM games")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT title, genres FROM games ORDER BY title LIMIT 20")
    sample = cursor.fetchall()
    
    conn.close()
    
    logger.info("🔍 ПРОВЕРКА:")
    logger.info(f"📊 Всего игр в базе: {total}")
    logger.info("📋 Первые 20 игр:")
    
    for i, (title, genres) in enumerate(sample, 1):
        try:
            genre_list = json.loads(genres) if genres else []
            genres_str = ", ".join(genre_list) if genre_list else "Нет жанров"
            status = "✅" if genre_list else "❌"
            logger.info(f"{status} [{i:2d}] {title}")
            logger.info(f"     🏷️ {genres_str}")
        except:
            logger.info(f"❌ [{i:2d}] {title} -> Ошибка жанров")
        logger.info("")
    
    if total >= 500:
        logger.info("🎉 База данных успешно заполнена!")
    else:
        logger.warning(f"⚠️ В базе только {total} игр, ожидалось ~510")

def main():
    logger.info("🚀 ИСПРАВЛЕНИЕ БАЗЫ ДАННЫХ!")
    
    # Исправляем лимит
    total, with_genres = fix_database_limit()
    
    # Проверяем
    verify_all_games_added()
    
    logger.info("🎉 БАЗА ДАННЫХ ИСПРАВЛЕНА!")

if __name__ == "__main__":
    main()
