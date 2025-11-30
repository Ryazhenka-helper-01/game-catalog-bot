#!/usr/bin/env python3
"""
Гарантированное заполнение базы данных играми при старте
"""

import asyncio
import logging
from database import Database
from parser import GameParser

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def ensure_games_loaded():
    """Гарантированно загрузить игры в базу данных"""
    
    print("=== ENSURE GAMES LOADED ===")
    
    db = Database()
    parser = GameParser()
    
    try:
        # Проверяем текущее состояние базы
        existing_games = await db.get_all_games()
        print(f"Current games in database: {len(existing_games)}")
        
        if len(existing_games) >= 100:
            print("Database already has games. Skipping...")
            return True
        
        print("Database is empty or has too few games. Starting parsing...")
        
        # Пробуем несколько подходов для загрузки игр
        games_loaded = False
        
        # Подход 1: Парсинг с главной страницы
        try:
            print("Approach 1: Parsing from main page...")
            games = await parser.parse_game_list()
            print(f"Approach 1 result: {len(games)} games")
            
            if len(games) > 0:
                # Сохраняем игры
                for game in games:
                    await db.add_game(game)
                print(f"Saved {len(games)} games to database")
                games_loaded = True
                
        except Exception as e:
            print(f"Approach 1 failed: {e}")
        
        # Подход 2: Если основной парсинг не сработал, используем резервный метод
        if not games_loaded:
            try:
                print("Approach 2: Using fallback parsing method...")
                
                # Загружаем главную страницу
                html = await parser.get_page(parser.base_url)
                if html:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Ищем все ссылки на игры
                    links = soup.find_all('a', href=True)
                    game_links = []
                    
                    for link in links:
                        href = link.get('href', '')
                        if 'nintendo-switch' in href and href.endswith('.html'):
                            full_url = parser.base_url + href if not href.startswith('http') else href
                            if full_url not in game_links:
                                game_links.append(full_url)
                    
                    print(f"Found {len(game_links)} game links")
                    
                    # Создаем базовые записи для игр
                    for i, link in enumerate(game_links[:200]):  # Ограничим 200 играми
                        try:
                            # Извлекаем название из URL
                            title = link.split('/')[-1].replace('.html', '').replace('-', ' ').title()
                            
                            game = {
                                'title': title,
                                'url': link,
                                'description': '',
                                'genres': [],
                                'rating': 'N/A',
                                'image_url': '',
                                'screenshots': [],
                                'release_date': ''
                            }
                            
                            await db.add_game(game)
                            
                            if (i + 1) % 50 == 0:
                                print(f"Processed {i+1}/{len(game_links)} games...")
                                
                        except Exception as e:
                            print(f"Error processing link {i+1}: {e}")
                            continue
                    
                    print(f"Created basic records for {min(len(game_links), 200)} games")
                    games_loaded = True
                    
            except Exception as e:
                print(f"Approach 2 failed: {e}")
        
        # Проверяем результат
        final_count = len(await db.get_all_games())
        print(f"Final games count: {final_count}")
        
        if final_count > 0:
            print("✅ Games successfully loaded to database!")
            return True
        else:
            print("❌ Failed to load games to database")
            return False
            
    except Exception as e:
        print(f"Error in ensure_games_loaded: {e}")
        return False
    
    finally:
        # Закрываем соединения
        if hasattr(parser, 'session') and parser.session:
            await parser.session.close()

if __name__ == "__main__":
    result = asyncio.run(ensure_games_loaded())
    if result:
        print("SUCCESS: Games loaded to database")
    else:
        print("FAILED: Could not load games")
