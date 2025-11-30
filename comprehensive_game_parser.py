#!/usr/bin/env python3
"""
Комплексный парсер всех игр с сайта asst2game.ru
"""

import asyncio
import logging
from database import Database
from parser import GameParser
from bs4 import BeautifulSoup
import re

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def parse_all_games_comprehensive():
    """Комплексный парсинг всех игр с сайта"""
    
    print("=== COMPREHENSIVE GAME PARSER ===")
    
    db = Database()
    parser = GameParser()
    
    try:
        # Очищаем базу перед загрузкой
        print("Clearing database...")
        all_games = await db.get_all_games()
        for game in all_games:
            await db.delete_game(game['id'])
        print("Database cleared")
        
        games_found = set()  # Для evitar дубликатов
        
        # Подход 1: Парсинг страниц пагинации
        try:
            print("Approach 1: Parsing all pages...")
            
            base_url = "https://asst2game.ru"
            page = 1
            
            while True:
                page_url = f"{base_url}/page/{page}/" if page > 1 else base_url
                
                print(f"Parsing page {page}: {page_url}")
                html = await parser.get_page(page_url)
                
                if not html:
                    print(f"No HTML for page {page}, stopping pagination")
                    break
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Ищем все ссылки на игры на странице
                links = soup.find_all('a', href=True)
                page_games = []
                
                for link in links:
                    href = link.get('href', '')
                    
                    # Ищем ссылки на игры Nintendo Switch
                    if ('nintendo-switch' in href and '.html' in href):
                        full_url = base_url + href if not href.startswith('http') else href
                        
                        if full_url not in games_found:
                            games_found.add(full_url)
                            
                            # Извлекаем название
                            url_part = href.split('/')[-1].replace('.html', '')
                            title_words = url_part.split('-')
                            title = ' '.join([word.capitalize() for word in title_words])
                            
                            # Фильтруем некачественные названия
                            if len(title) >= 3 and not title.isdigit():
                                page_games.append({
                                    'title': title,
                                    'url': full_url,
                                    'description': '',
                                    'genres': [],
                                    'rating': 'N/A',
                                    'image_url': '',
                                    'screenshots': [],
                                    'release_date': ''
                                })
                
                print(f"Page {page}: found {len(page_games)} games")
                
                # Сохраняем игры с текущей страницы
                for game in page_games:
                    await db.add_game(game)
                
                # Если на странице мало игр, возможно это последняя страница
                if len(page_games) < 5:
                    print(f"Page {page} has only {len(page_games)} games, stopping pagination")
                    break
                
                page += 1
                if page > 50:  # Ограничим 50 страниц чтобы не уйти в бесконечность
                    print("Reached page limit (50), stopping pagination")
                    break
                
                # Небольшая задержка между страницами
                await asyncio.sleep(0.5)
                
        except Exception as e:
            print(f"Approach 1 failed: {e}")
        
        # Подход 2: Поиск по категориям/тегам
        if len(games_found) < 200:
            try:
                print("Approach 2: Searching by categories...")
                
                # Загружаем главную страницу и ищем ссылки на категории
                html = await parser.get_page(base_url)
                if html:
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Ищем ссылки на категории или теги
                    category_links = []
                    links = soup.find_all('a', href=True)
                    
                    for link in links:
                        href = link.get('href', '')
                        text = link.get_text().strip().lower()
                        
                        # Ищем ссылки на категории игр
                        if ('category' in href or 'tag' in href or 'genre' in href) and '.html' not in href:
                            full_url = base_url + href if not href.startswith('http') else href
                            if full_url not in category_links:
                                category_links.append(full_url)
                    
                    print(f"Found {len(category_links)} category links")
                    
                    # Парсим каждую категорию
                    for cat_url in category_links[:20]:  # Ограничим 20 категориями
                        try:
                            print(f"Parsing category: {cat_url}")
                            cat_html = await parser.get_page(cat_url)
                            
                            if cat_html:
                                cat_soup = BeautifulSoup(cat_html, 'html.parser')
                                cat_links = cat_soup.find_all('a', href=True)
                                
                                for link in cat_links:
                                    href = link.get('href', '')
                                    if 'nintendo-switch' in href and '.html' in href:
                                        full_url = base_url + href if not href.startswith('http') else href
                                        
                                        if full_url not in games_found:
                                            games_found.add(full_url)
                                            
                                            # Извлекаем название
                                            url_part = href.split('/')[-1].replace('.html', '')
                                            title_words = url_part.split('-')
                                            title = ' '.join([word.capitalize() for word in title_words])
                                            
                                            if len(title) >= 3 and not title.isdigit():
                                                game = {
                                                    'title': title,
                                                    'url': full_url,
                                                    'description': '',
                                                    'genres': [],
                                                    'rating': 'N/A',
                                                    'image_url': '',
                                                    'screenshots': [],
                                                    'release_date': ''
                                                }
                                                await db.add_game(game)
                            
                            await asyncio.sleep(0.3)  # Задержка между категориями
                            
                        except Exception as e:
                            print(f"Error parsing category {cat_url}: {e}")
                            continue
                            
            except Exception as e:
                print(f"Approach 2 failed: {e}")
        
        # Подход 3: Прямой поиск по паттернам URL
        if len(games_found) < 300:
            try:
                print("Approach 3: Direct URL pattern search...")
                
                # Генерируем возможные URL на основе распространенных паттернов
                common_patterns = [
                    'action', 'adventure', 'rpg', 'strategy', 'puzzle', 'simulation',
                    'sports', 'racing', 'fighting', 'platformer', 'shooter', 'stealth',
                    'survival', 'horror', 'music', 'party', 'casual', 'indie'
                ]
                
                for pattern in common_patterns:
                    try:
                        # Пробуем разные варианты URL
                        test_urls = [
                            f"{base_url}/{pattern}-nintendo-switch",
                            f"{base_url}/{pattern}-switch",
                            f"{base_url}/games/{pattern}-nintendo-switch"
                        ]
                        
                        for test_url in test_urls:
                            html = await parser.get_page(test_url)
                            if html:
                                soup = BeautifulSoup(html, 'html.parser')
                                links = soup.find_all('a', href=True)
                                
                                for link in links:
                                    href = link.get('href', '')
                                    if 'nintendo-switch' in href and '.html' in href:
                                        full_url = base_url + href if not href.startswith('http') else href
                                        
                                        if full_url not in games_found:
                                            games_found.add(full_url)
                                            
                                            url_part = href.split('/')[-1].replace('.html', '')
                                            title_words = url_part.split('-')
                                            title = ' '.join([word.capitalize() for word in title_words])
                                            
                                            if len(title) >= 3 and not title.isdigit():
                                                game = {
                                                    'title': title,
                                                    'url': full_url,
                                                    'description': '',
                                                    'genres': [],
                                                    'rating': 'N/A',
                                                    'image_url': '',
                                                    'screenshots': [],
                                                    'release_date': ''
                                                }
                                                await db.add_game(game)
                        
                        await asyncio.sleep(0.2)
                        
                    except Exception as e:
                        continue
                        
            except Exception as e:
                print(f"Approach 3 failed: {e}")
        
        # Финальная проверка
        final_count = len(await db.get_all_games())
        print(f"Final games count: {final_count}")
        
        if final_count > 100:
            print(f"✅ Successfully loaded {final_count} games!")
            return True
        else:
            print(f"❌ Only {final_count} games loaded, expected more")
            return False
            
    except Exception as e:
        print(f"Error in comprehensive parsing: {e}")
        return False
    
    finally:
        if hasattr(parser, 'session') and parser.session:
            await parser.session.close()

if __name__ == "__main__":
    result = asyncio.run(parse_all_games_comprehensive())
    if result:
        print("SUCCESS: Comprehensive games loading completed")
    else:
        print("FAILED: Could not load sufficient games")
