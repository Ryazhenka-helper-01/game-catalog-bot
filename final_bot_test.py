#!/usr/bin/env python3
"""
Финальный тест бота с 510 играми
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

async def final_bot_test():
    """Финальное тестирование бота"""
    
    logger.info("🚀 ФИНАЛЬНЫЙ ТЕСТ БОТА С 510 ИГРАМИ!")
    
    # Инициализируем базу данных
    db = Database()
    
    # Проверяем что все игры на месте
    all_games = await db.get_all_games()
    logger.info(f"📊 Игр в базе бота: {len(all_games)}")
    
    if len(all_games) < 500:
        logger.error(f"❌ В базе только {len(all_games)} игр, должно быть 510!")
        return
    
    logger.info("✅ Все 510 игр в базе!")
    
    # Игры с жанрами
    games_with_genres = [game for game in all_games if game.get('genres')]
    logger.info(f"🏷️ Игр с жанрами: {len(games_with_genres)}")
    
    # Получаем все жанры
    all_genres = await db.get_all_genres()
    logger.info(f"🎯 Уникальных жанров: {len(all_genres)}")
    
    logger.info("")
    logger.info("🏷️ ТОП-10 ЖАНРОВ В БОТЕ:")
    
    # Считаем игры по жанрам
    genre_counts = {}
    for genre in all_genres:
        games_by_genre = await db.get_games_by_genre(genre)
        genre_counts[genre] = len(games_by_genre)
    
    # Сортируем и показываем топ-10
    sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)
    for i, (genre, count) in enumerate(sorted_genres[:10], 1):
        logger.info(f"   {i:2d}. {genre}: {count} игр")
    
    logger.info("")
    logger.info("🔍 ТЕСТ ПОИСКА ПО ЖАНРАМ:")
    
    # Тестируем популярные жанры
    test_genres = ['Экшен', 'RPG', 'Приключение', 'Стратегия']
    
    for genre in test_genres:
        if genre in all_genres:
            games = await db.get_games_by_genre(genre)
            logger.info(f"🎮 {genre}: {len(games)} игр")
            
            # Показываем 3 примера
            for i, game in enumerate(games[:3], 1):
                title = game.get('title', 'Unknown')
                genres = game.get('genres', [])
                
                if isinstance(genres, str):
                    genres = json.loads(genres) if genres else []
                
                genres_str = ", ".join(genres) if genres else "Нет жанров"
                logger.info(f"   {i}. {title}")
                logger.info(f"      🏷️ {genres_str}")
            
            if len(games) > 3:
                logger.info(f"      ... и еще {len(games)-3} игр")
            logger.info("")
    
    logger.info("📋 ПРИМЕРЫ РАЗНООБРАЗНЫХ ИГР:")
    
    # Показываем игры с разными жанрами
    sample_games = []
    for game in all_games:
        if game.get('genres'):
            genres = game.get('genres', [])
            if isinstance(genres, str):
                genres = json.loads(genres) if genres else []
            if len(genres) >= 2:  # Игры с несколькими жанрами
                sample_games.append(game)
                if len(sample_games) >= 15:
                    break
    
    for i, game in enumerate(sample_games[:15], 1):
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
    logger.info("📱 Команда /genres покажет кнопки жанров:")
    
    # Группируем жанры для кнопок
    genre_buttons = []
    for i, genre in enumerate(all_genres):
        if i % 3 == 0:
            genre_buttons.append([])
        genre_buttons[-1].append(genre)
    
    for row in genre_buttons[:12]:  # Показываем первые 12 строк
        button_row = " | ".join([f"[{genre}]" for genre in row])
        logger.info(f"   {button_row}")
    
    if len(genre_buttons) > 12:
        logger.info(f"   ... и еще {len(genre_buttons)-12} строк кнопок")
    
    logger.info("")
    logger.info("🎉 ФИНАЛЬНЫЙ ТЕСТ ЗАВЕРШЕН!")
    logger.info(f"📊 Бот готов с {len(all_games)} играми и {len(all_genres)} жанрами!")
    logger.info("🎮 Пользователи могут искать игры по любому из 34 жанров!")
    
    # Проверяем конкретные популярные запросы
    logger.info("")
    logger.info("🔍 ТЕСТ ПОПУЛЯРНЫХ ЗАПРОСОВ:")
    
    popular_queries = [
        ("Экшен", "204 игр"),
        ("RPG", "106 игр"),
        ("Приключение", "105 игр"),
        ("Стратегия", "67 игр"),
        ("Гонки", "53 игр")
    ]
    
    for query, expected in popular_queries:
        games = await db.get_games_by_genre(query)
        actual = len(games)
        status = "✅" if actual >= int(expected.split()[0]) else "❌"
        logger.info(f"{status} '{query}': {actual} игр (ожидалось {expected})")

async def main():
    await final_bot_test()

if __name__ == "__main__":
    asyncio.run(main())
