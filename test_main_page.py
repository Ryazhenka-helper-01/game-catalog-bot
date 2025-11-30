#!/usr/bin/env python3
"""
Тест загрузки главной страницы сайта
"""

import asyncio
from parser import GameParser
from bs4 import BeautifulSoup

async def test_main_page():
    """Тест загрузки главной страницы"""
    
    parser = GameParser()
    
    try:
        async with parser:
            print("Testing main page loading...")
            html = await parser.get_page(parser.base_url)
            
            if html:
                print("Main page loaded successfully!")
                print(f"HTML length: {len(html)} characters")
                
                # Ищем ссылки на игры
                soup = BeautifulSoup(html, 'html.parser')
                links = soup.find_all('a', href=True)
                
                game_links = []
                for link in links:
                    href = link.get('href', '')
                    if 'nintendo-switch' in href and '.html' in href:
                        full_url = parser.base_url + href if not href.startswith('http') else href
                        game_links.append(full_url)
                
                print(f"Found {len(game_links)} game links on main page")
                
                # Показываем первые 5 ссылок
                for i, link in enumerate(game_links[:5]):
                    print(f"  {i+1}. {link}")
                
                # Пробуем загрузить одну игру
                if game_links:
                    test_url = game_links[0]
                    print(f"\nTrying to load game page: {test_url}")
                    
                    game_html = await parser.get_page(test_url)
                    if game_html:
                        print("Game page loaded! Length: {len(game_html)} characters")
                        
                        # Сохраняем HTML для анализа
                        with open("game_page_sample.html", 'w', encoding='utf-8') as f:
                            f.write(game_html)
                        print("Saved game page HTML to game_page_sample.html")
                        
                        return True
                    else:
                        print("Failed to load game page")
                
            else:
                print("Failed to load main page")
                return False
                
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    finally:
        if hasattr(parser, 'session') and parser.session:
            await parser.session.close()

if __name__ == "__main__":
    asyncio.run(test_main_page())
