#!/usr/bin/env python3
"""
Умный парсер, который анализирует структуру сайта и находит все игры
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

async def smart_parse_all_games():
    """Умный парсинг с анализом структуры сайта"""
    
    print("=== SMART GAME PARSER ===")
    
    db = Database()
    parser = GameParser()
    
    try:
        # Очищаем базу
        print("Clearing database...")
        all_games = await db.get_all_games()
        for game in all_games:
            await db.delete_game(game['id'])
        print("Database cleared")
        
        games_found = set()
        
        # Анализируем главную страницу
        print("Analyzing main page structure...")
        html = await parser.get_page(parser.base_url)
        if not html:
            print("Failed to load main page")
            return False
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # Ищем все возможные ссылки на игры
        all_links = soup.find_all('a', href=True)
        game_links = []
        
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text().strip()
            
            # Ищем ссылки, которые ведут на игры
            if ('nintendo-switch' in href and '.html' in href):
                full_url = parser.base_url + href if not href.startswith('http') else href
                
                if full_url not in games_found:
                    games_found.add(full_url)
                    
                    # Пытаемся извлечь название из текста ссылки
                    title = text if text and len(text) > 2 else ""
                    
                    # Если текст ссылки пустой, извлекаем из URL
                    if not title:
                        url_part = href.split('/')[-1].replace('.html', '')
                        title_words = url_part.split('-')
                        title = ' '.join([word.capitalize() for word in title_words])
                    
                    # Фильтруем некачественные названия
                    if len(title) >= 3 and not title.isdigit():
                        game_links.append({
                            'title': title,
                            'url': full_url,
                            'description': '',
                            'genres': [],
                            'rating': 'N/A',
                            'image_url': '',
                            'screenshots': [],
                            'release_date': ''
                        })
        
        print(f"Found {len(game_links)} games on main page")
        
        # Ищем навигацию по страницам
        pagination_links = []
        
        # Ищем ссылки с номерами страниц
        page_pattern = re.compile(r'page/\d+|/p\d+|\?p=\d+')
        
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text().strip()
            
            # Ищем пагинацию
            if page_pattern.search(href) or text.isdigit():
                full_url = parser.base_url + href if not href.startswith('http') else href
                if full_url not in pagination_links:
                    pagination_links.append(full_url)
        
        print(f"Found {len(pagination_links)} pagination links")
        
        # Если есть пагинация, парсим все страницы
        if pagination_links:
            print("Parsing pagination pages...")
            
            for page_url in pagination_links[:20]:  # Ограничим 20 страницами
                try:
                    print(f"Parsing page: {page_url}")
                    page_html = await parser.get_page(page_url)
                    
                    if page_html:
                        page_soup = BeautifulSoup(page_html, 'html.parser')
                        page_links = page_soup.find_all('a', href=True)
                        
                        for link in page_links:
                            href = link.get('href', '')
                            text = link.get_text().strip()
                            
                            if ('nintendo-switch' in href and '.html' in href):
                                full_url = parser.base_url + href if not href.startswith('http') else href
                                
                                if full_url not in games_found:
                                    games_found.add(full_url)
                                    
                                    title = text if text and len(text) > 2 else ""
                                    if not title:
                                        url_part = href.split('/')[-1].replace('.html', '')
                                        title_words = url_part.split('-')
                                        title = ' '.join([word.capitalize() for word in title_words])
                                    
                                    if len(title) >= 3 and not title.isdigit():
                                        game_links.append({
                                            'title': title,
                                            'url': full_url,
                                            'description': '',
                                            'genres': [],
                                            'rating': 'N/A',
                                            'image_url': '',
                                            'screenshots': [],
                                            'release_date': ''
                                        })
                    
                    await asyncio.sleep(0.3)
                    
                except Exception as e:
                    print(f"Error parsing page {page_url}: {e}")
                    continue
        
        # Ищем меню или навигацию по категориям
        print("Looking for category navigation...")
        nav_elements = soup.find_all(['nav', 'menu', 'div'], class_=re.compile(r'nav|menu|category|genre'))
        
        category_urls = set()
        for nav in nav_elements:
            links = nav.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                if ('category' in href or 'tag' in href or 'genre' in href) and '.html' not in href:
                    full_url = parser.base_url + href if not href.startswith('http') else href
                    category_urls.add(full_url)
        
        print(f"Found {len(category_urls)} category URLs")
        
        # Парсим категории
        for cat_url in list(category_urls)[:10]:  # Ограничим 10 категориями
            try:
                print(f"Parsing category: {cat_url}")
                cat_html = await parser.get_page(cat_url)
                
                if cat_html:
                    cat_soup = BeautifulSoup(cat_html, 'html.parser')
                    cat_links = cat_soup.find_all('a', href=True)
                    
                    for link in cat_links:
                        href = link.get('href', '')
                        text = link.get_text().strip()
                        
                        if ('nintendo-switch' in href and '.html' in href):
                            full_url = parser.base_url + href if not href.startswith('http') else href
                            
                            if full_url not in games_found:
                                games_found.add(full_url)
                                
                                title = text if text and len(text) > 2 else ""
                                if not title:
                                    url_part = href.split('/')[-1].replace('.html', '')
                                    title_words = url_part.split('-')
                                    title = ' '.join([word.capitalize() for word in title_words])
                                
                                if len(title) >= 3 and not title.isdigit():
                                    game_links.append({
                                        'title': title,
                                        'url': full_url,
                                        'description': '',
                                        'genres': [],
                                        'rating': 'N/A',
                                        'image_url': '',
                                        'screenshots': [],
                                        'release_date': ''
                                    })
                
                await asyncio.sleep(0.3)
                
            except Exception as e:
                print(f"Error parsing category {cat_url}: {e}")
                continue
        
        # Сохраняем все найденные игры
        print(f"Saving {len(game_links)} games to database...")
        
        for i, game in enumerate(game_links):
            await db.add_game(game)
            if (i + 1) % 50 == 0:
                print(f"Saved {i+1}/{len(game_links)} games...")
        
        final_count = len(await db.get_all_games())
        print(f"Final games count: {final_count}")
        
        if final_count > 50:
            print(f"✅ Successfully loaded {final_count} games!")
            return True
        else:
            print(f"❌ Only {final_count} games loaded")
            return False
            
    except Exception as e:
        print(f"Error in smart parsing: {e}")
        return False
    
    finally:
        if hasattr(parser, 'session') and parser.session:
            await parser.session.close()

if __name__ == "__main__":
    result = asyncio.run(smart_parse_all_games())
    if result:
        print("SUCCESS: Smart parsing completed")
    else:
        print("FAILED: Smart parsing failed")
