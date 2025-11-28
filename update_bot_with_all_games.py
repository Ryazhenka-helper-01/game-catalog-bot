#!/usr/bin/env python3
"""
Скрипт для добавления ВСЕХ 360 игр с жанрами в бота
"""

import json
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_bot_database():
    """Обновить базу данных бота всеми играми"""
    
    # Загружаем все игры
    with open('all_800_games_complete.json', 'r', encoding='utf-8') as f:
        all_games = json.load(f)
    
    logger.info(f"📊 Загружено игр из файла: {len(all_games)}")
    
    # Подключаемся к базе
    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()
    
    # Создаем таблицу если нет
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL UNIQUE,
            description TEXT,
            rating TEXT,
            genres TEXT,
            image_url TEXT,
            screenshots TEXT,
            release_date TEXT,
            url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Очищаем старые данные
    cursor.execute("DELETE FROM games")
    conn.commit()
    logger.info("🗑️ Старая база очищена")
    
    # Добавляем все игры
    added_count = 0
    with_genres_count = 0
    
    for i, game in enumerate(all_games, 1):
        try:
            # Подготавливаем данные
            title = game['title']
            url = game['url']
            genres = json.dumps(game['genres'], ensure_ascii=False) if game['genres'] else '[]'
            
            # Вставляем в базу
            cursor.execute('''
                INSERT INTO games (title, url, genres)
                VALUES (?, ?, ?)
            ''', (title, url, genres))
            
            added_count += 1
            if game['found_genres']:
                with_genres_count += 1
            
            # Показываем прогресс
            if i % 50 == 0:
                logger.info(f"📊 Добавлено {i}/{len(all_games)} игр...")
                
        except Exception as e:
            logger.error(f"❌ Ошибка добавления игры {game['title']}: {e}")
            continue
    
    # Сохраняем изменения
    conn.commit()
    conn.close()
    
    logger.info(f"✅ Добавлено игр в базу: {added_count}")
    logger.info(f"🏷️ Игр с жанрами: {with_genres_count}")
    logger.info(f"📈 Процент с жанрами: {(with_genres_count/added_count*100):.1f}%")
    
    return added_count, with_genres_count

def verify_database():
    """Проверяем что все добавилось корректно"""
    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()
    
    # Общее количество
    cursor.execute("SELECT COUNT(*) FROM games")
    total = cursor.fetchone()[0]
    
    # С жанрами
    cursor.execute("SELECT COUNT(*) FROM games WHERE genres != '[]' AND genres IS NOT NULL")
    with_genres = cursor.fetchone()[0]
    
    # Показываем несколько примеров
    cursor.execute("SELECT title, genres FROM games LIMIT 5")
    examples = cursor.fetchall()
    
    conn.close()
    
    logger.info("🔍 ПРОВЕРКА БАЗЫ ДАННЫХ:")
    logger.info(f"📊 Всего игр: {total}")
    logger.info(f"🏷️ С жанрами: {with_genres}")
    logger.info("📋 Примеры:")
    
    for title, genres in examples:
        genres_list = json.loads(genres) if genres else []
        genres_str = ", ".join(genres_list) if genres_list else "Нет жанров"
        logger.info(f"🎮 {title} -> {genres_str}")

def main():
    logger.info("🚀 НАЧИНАЮ ОБНОВЛЕНИЕ БОТА ВСЕМИ 360 ИГРАМИ!")
    
    # Обновляем базу
    added, with_genres = update_bot_database()
    
    # Проверяем
    verify_database()
    
    logger.info("🎉 БОТ ОБНОВЛЕН! Теперь в базе 360 игр с жанрами!")

if __name__ == "__main__":
    main()
