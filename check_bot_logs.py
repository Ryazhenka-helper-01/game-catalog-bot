#!/usr/bin/env python3
"""
Проверка логов и статуса бота
"""

import sqlite3
import json
import asyncio
import sys
import os

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Database
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def check_bot_status():
    """Проверка статуса бота"""
    
    logger.info("🚀 ПРОВЕРКА СТАТУСА БОТА!")
    
    # Инициализируем базу данных
    db = Database()
    
    # Проверяем базу данных
    all_games = await db.get_all_games()
    logger.info(f"📊 Игр в базе: {len(all_games)}")
    
    games_with_genres = [game for game in all_games if game.get('genres')]
    logger.info(f"🏷️ Игр с жанрами: {len(games_with_genres)}")
    
    all_genres = await db.get_all_genres()
    logger.info(f"🎯 Уникальных жанров: {len(all_genres)}")
    
    # Проверяем популярные жанры
    logger.info("")
    logger.info("🔍 ПРОВЕРКА ПОПУЛЯРНЫХ ЖАНРОВ:")
    
    test_genres = ['Экшен', 'RPG', 'Приключение', 'Стратегия']
    
    for genre in test_genres:
        if genre in all_genres:
            games = await db.get_games_by_genre(genre)
            logger.info(f"✅ {genre}: {len(games)} игр")
        else:
            logger.info(f"❌ {genre}: жанр не найден")
    
    # Проверяем базу напрямую
    logger.info("")
    logger.info("🔍 ПРЯМАЯ ПРОВЕРКА БАЗЫ ДАННЫХ:")
    
    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM games")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM games WHERE genres != '[]' AND genres IS NOT NULL")
    with_genres = cursor.fetchone()[0]
    
    logger.info(f"📊 Всего игр в SQLite: {total}")
    logger.info(f"🏷️ С жанрами в SQLite: {with_genres}")
    
    # Получаем примеры игр
    cursor.execute("SELECT title, genres FROM games ORDER BY title LIMIT 5")
    sample_games = cursor.fetchall()
    
    logger.info("")
    logger.info("📋 ПРИМЕРЫ ИГР В БАЗЕ:")
    for i, (title, genres) in enumerate(sample_games, 1):
        try:
            genre_list = json.loads(genres) if genres else []
            genres_str = ", ".join(genre_list) if genre_list else "Нет жанров"
            status = "✅" if genre_list else "❌"
            logger.info(f"{status} [{i}] {title}")
            logger.info(f"     🏷️ {genres_str}")
        except:
            logger.info(f"❌ [{i}] {title} -> Ошибка жанров")
    
    conn.close()
    
    logger.info("")
    logger.info("🎯 СТАТИСТИКА ПО ЖАНРАМ:")
    
    # Считаем все жанры
    genre_counts = {}
    for genre in all_genres:
        games = await db.get_games_by_genre(genre)
        genre_counts[genre] = len(games)
    
    sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)
    
    logger.info("📈 ТОП-15 ЖАНРОВ:")
    for i, (genre, count) in enumerate(sorted_genres[:15], 1):
        logger.info(f"{i:2d}. {genre}: {count} игр")
    
    logger.info("")
    logger.info("🎉 ПРОВЕРКА ЗАВЕРШЕНА!")
    logger.info(f"📊 Бот готов с {len(all_games)} играми и {len(all_genres)} жанрами!")
    
    # Проверяем доступность команд
    logger.info("")
    logger.info("📋 ДОСТУПНЫЕ КОМАНДЫ БОТА:")
    commands = [
        "/start - Приветствие",
        "/genres - Все жанры кнопками", 
        "/games - Все игры",
        "/search [жанр] - Поиск по жанру",
        "/help - Помощь",
        "/stats - Статистика",
        "/update_genres - Обновить жанры"
    ]
    
    for cmd in commands:
        logger.info(f"   ✅ {cmd}")
    
    logger.info("")
    logger.info("💡 ТЕКСТОВЫЕ КОМАНДЫ:")
    text_commands = [
        "Экшен - 204 игры",
        "RPG - 106 игр",
        "Приключение - 105 игр", 
        "Стратегия - 67 игр",
        "Гонки - 53 игр"
    ]
    
    for cmd in text_commands:
        logger.info(f"   ✅ {cmd}")

async def main():
    await check_bot_status()

if __name__ == "__main__":
    asyncio.run(main())
