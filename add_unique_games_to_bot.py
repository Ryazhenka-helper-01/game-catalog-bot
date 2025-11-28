#!/usr/bin/env python3
"""
Скрипт для добавления только УНИКАЛЬНЫХ игр в бота
"""

import json
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_unique_games_to_bot():
    """Добавить только уникальные игры в бота"""
    
    # Загружаем все игры
    with open('all_800_games_complete.json', 'r', encoding='utf-8') as f:
        all_games = json.load(f)
    
    logger.info(f"📊 Всего игр в файле: {len(all_games)}")
    
    # Создаем словарь уникальных игр (title -> лучшая запись)
    unique_games = {}
    
    for game in all_games:
        title = game['title']
        
        # Если игры еще нет в словаре или у текущей записи есть жанры
        if title not in unique_games or (game['found_genres'] and not unique_games[title]['found_genres']):
            unique_games[title] = game
    
    logger.info(f"🎯 Уникальных игр: {len(unique_games)}")
    
    # Подключаемся к базе
    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()
    
    # Очищаем базу
    cursor.execute("DELETE FROM games")
    conn.commit()
    logger.info("🗑️ База очищена")
    
    # Добавляем уникальные игры
    added_count = 0
    with_genres_count = 0
    
    for title, game in unique_games.items():
        try:
            # Подготавливаем данные
            url = game['url']
            genres = json.dumps(game['genres'], ensure_ascii=False) if game['genres'] else '[]'
            
            # Вставляем
            cursor.execute('''
                INSERT INTO games (title, url, genres)
                VALUES (?, ?, ?)
            ''', (title, url, genres))
            
            added_count += 1
            if game['found_genres']:
                with_genres_count += 1
            
            logger.info(f"✅ Добавлено: {title} -> {game['genres']}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления {title}: {e}")
            continue
    
    # Сохраняем
    conn.commit()
    conn.close()
    
    logger.info(f"🎉 Добавлено уникальных игр: {added_count}")
    logger.info(f"🏷️ С жанрами: {with_genres_count}")
    logger.info(f"📈 Процент с жанрами: {(with_genres_count/added_count*100):.1f}%")
    
    return added_count, with_genres_count

def show_final_stats():
    """Показать финальную статистику"""
    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM games")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM games WHERE genres != '[]' AND genres IS NOT NULL")
    with_genres = cursor.fetchone()[0]
    
    cursor.execute("SELECT title, genres FROM games ORDER BY title")
    all_games_db = cursor.fetchall()
    
    conn.close()
    
    logger.info("🎯 ФИНАЛЬНАЯ СТАТИСТИКА БОТА:")
    logger.info(f"📊 Всего игр в боте: {total}")
    logger.info(f"🏷️ Игр с жанрами: {with_genres}")
    logger.info(f"📈 Процент: {(with_genres/total*100):.1f}%")
    logger.info("")
    logger.info("📋 Все игры в боте:")
    
    for title, genres in all_games_db:
        genres_list = json.loads(genres) if genres else []
        genres_str = ", ".join(genres_list) if genres_list else "Нет жанров"
        status = "✅" if genres_list else "❌"
        logger.info(f"{status} {title} -> {genres_str}")

def main():
    logger.info("🚀 ДОБАВЛЯЕМ УНИКАЛЬНЫЕ ИГРЫ В БОТА!")
    
    # Добавляем уникальные игры
    added, with_genres = add_unique_games_to_bot()
    
    # Показываем статистику
    show_final_stats()
    
    logger.info("🎉 БОТ ГОТОВ! Теперь в базе уникальные игры с жанрами!")

if __name__ == "__main__":
    main()
