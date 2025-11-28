#!/usr/bin/env python3
"""
Тестирование бота с новой базой данных
"""

import asyncio
import sys
import os

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Database
from parser import GameParser
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_bot_database():
    """Тестирование базы данных бота"""
    
    logger.info("🚀 ТЕСТИРУЕМ БОТА С НОВОЙ БАЗОЙ!")
    
    # Инициализируем компоненты
    db = Database()
    parser = GameParser()
    
    # Получаем все игры из базы
    all_games = await db.get_all_games()
    logger.info(f"📊 Игр в базе бота: {len(all_games)}")
    
    # Показываем игры с жанрами
    games_with_genres = [game for game in all_games if game.get('genres')]
    logger.info(f"🏷️ Игр с жанрами: {len(games_with_genres)}")
    
    logger.info("📋 Игры в боте:")
    for i, game in enumerate(all_games, 1):
        title = game.get('title', 'Unknown')
        genres = game.get('genres', [])
        
        if isinstance(genres, str):
            genres = json.loads(genres) if genres else []
        
        genres_str = ", ".join(genres) if genres else "Нет жанров"
        status = "✅" if genres else "❌"
        
        logger.info(f"{status} [{i:2d}] {title}")
        logger.info(f"     🏷️ {genres_str}")
        logger.info("")
    
    # Тестируем поиск по жанрам
    logger.info("🔍 ТЕСТ ПОИСКА ПО ЖАНРАМ:")
    
    # Получаем все жанры
    all_genres = await db.get_all_genres()
    logger.info(f"🏷️ Всего жанров в боте: {len(all_genres)}")
    
    # Показываем жанры и количество игр
    for genre in all_genres:
        games_by_genre = await db.get_games_by_genre(genre)
        logger.info(f"📊 {genre}: {len(games_by_genre)} игр")
        
        # Показываем несколько игр для каждого жанра
        for game in games_by_genre[:3]:
            logger.info(f"   • {game['title']}")
        
        if len(games_by_genre) > 3:
            logger.info(f"   ... и еще {len(games_by_genre)-3} игр")
        logger.info("")
    
    # Тестируем парсер на одной игре
    logger.info("🧪 ТЕСТ ПАРСЕРА:")
    if all_games:
        test_game = all_games[0]
        url = test_game.get('url')
        title = test_game.get('title')
        
        if url:
            logger.info(f"🎮 Тестирую парсер для: {title}")
            logger.info(f"🔗 URL: {url}")
            
            try:
                # Парсим игру
                parsed_data = await parser.parse_game_details(url)
                
                logger.info("📋 Результаты парсинга:")
                logger.info(f"   📝 Название: {parsed_data.get('title', 'N/A')}")
                logger.info(f"   🏷️ Жанры: {parsed_data.get('genres', [])}")
                logger.info(f"   ⭐ Рейтинг: {parsed_data.get('rating', 'N/A')}")
                logger.info(f"   📅 Дата: {parsed_data.get('release_date', 'N/A')}")
                
                # Сравниваем с базой
                db_genres = test_game.get('genres', [])
                if isinstance(db_genres, str):
                    db_genres = json.loads(db_genres) if db_genres else []
                
                parsed_genres = parsed_data.get('genres', [])
                
                logger.info("🔍 Сравнение жанров:")
                logger.info(f"   📊 В базе: {db_genres}")
                logger.info(f"   🔍 Парсер: {parsed_genres}")
                
                if db_genres == parsed_genres:
                    logger.info("✅ Жанры совпадают!")
                else:
                    logger.warning("⚠️ Жанры отличаются")
                
            except Exception as e:
                logger.error(f"❌ Ошибка парсинга: {e}")
    
    logger.info("🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")

async def main():
    await test_bot_database()

if __name__ == "__main__":
    asyncio.run(main())
