#!/usr/bin/env python3
"""
Тестирование обновленного бота с 510 играми
"""

import asyncio
import sys
import os
import json

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Database
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_updated_bot():
    """Тестирование обновленного бота"""
    
    logger.info("🚀 ТЕСТИРУЕМ ОБНОВЛЕННЫЙ БОТ С 510 ИГРАМИ!")
    
    # Инициализируем базу данных
    db = Database()
    
    # Получаем все игры
    all_games = await db.get_all_games()
    logger.info(f"📊 Игр в базе бота: {len(all_games)}")
    
    # Игры с жанрами
    games_with_genres = [game for game in all_games if game.get('genres')]
    logger.info(f"🏷️ Игр с жанрами: {len(games_with_genres)}")
    
    # Получаем все жанры
    all_genres = await db.get_all_genres()
    logger.info(f"🎯 Уникальных жанров: {len(all_genres)}")
    
    logger.info("")
    logger.info("🏷️ Все жанры в боте:")
    for genre in sorted(all_genres):
        games_by_genre = await db.get_games_by_genre(genre)
        logger.info(f"   📊 {genre}: {len(games_by_genre)} игр")
    
    logger.info("")
    logger.info("🔍 ТЕСТ ПОИСКА ПО ЖАНРАМ:")
    
    # Тестируем популярные жанры
    test_genres = ['Экшен', 'RPG', 'Приключение', 'Стратегия', 'Гонки']
    
    for genre in test_genres:
        if genre in all_genres:
            games = await db.get_games_by_genre(genre)
            logger.info(f"🎮 {genre}: найдено {len(games)} игр")
            
            # Показываем первые 3 игры
            for i, game in enumerate(games[:3], 1):
                title = game.get('title', 'Unknown')
                genres = game.get('genres', [])
                
                if isinstance(genres, str):
                    genres = json.loads(genres) if genres else []
                
                genres_str = ", ".join(genres) if genres else "Нет жанров"
                logger.info(f"   {i}. {title} -> {genres_str}")
            
            if len(games) > 3:
                logger.info(f"   ... и еще {len(games)-3} игр")
            logger.info("")
    
    logger.info("📋 Примеры игр с разными жанрами:")
    
    # Показываем разнообразные игры
    sample_games = []
    for game in all_games:
        if game.get('genres'):
            genres = game.get('genres', [])
            if isinstance(genres, str):
                genres = json.loads(genres) if genres else []
            if len(genres) > 1:  # Игры с несколькими жанрами
                sample_games.append(game)
                if len(sample_games) >= 10:
                    break
    
    for i, game in enumerate(sample_games[:10], 1):
        title = game.get('title', 'Unknown')
        genres = game.get('genres', [])
        
        if isinstance(genres, str):
            genres = json.loads(genres) if genres else []
        
        genres_str = ", ".join(genres) if genres else "Нет жанров"
        logger.info(f"{i:2d}. {title}")
        logger.info(f"    🏷️ {genres_str}")
        logger.info("")
    
    logger.info("🎯 ТЕСТ КОМАНДЫ /GENRES:")
    
    # Показываем как будет выглядеть команда /genres
    logger.info("📱 Команда /genres покажет кнопки:")
    
    # Группируем жанры для кнопок
    genre_buttons = []
    for i, genre in enumerate(all_genres):
        if i % 3 == 0:
            genre_buttons.append([])
        genre_buttons[-1].append(genre)
    
    for row in genre_buttons[:5]:  # Показываем первые 5 строк
        button_row = " | ".join([f"[{genre}]" for genre in row])
        logger.info(f"   {button_row}")
    
    if len(genre_buttons) > 5:
        logger.info(f"   ... и еще {len(genre_buttons)-5} строк кнопок")
    
    logger.info("")
    logger.info("🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")
    logger.info(f"📊 Бот готов с {len(all_games)} играми и {len(all_genres)} жанрами!")

async def main():
    await test_updated_bot()

if __name__ == "__main__":
    asyncio.run(main())
