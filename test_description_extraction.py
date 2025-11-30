#!/usr/bin/env python3
"""
Тестирование извлечения полных описаний игр
"""

import asyncio
from parser import GameParser
from bs4 import BeautifulSoup

async def test_description_extraction():
    """Тест извлечения описаний с сайта"""
    
    parser = GameParser()
    
    # Пример URL игры для теста
    test_urls = [
        "https://asst2game.ru/nintendo-switch/1236-max-the-curse-of-brotherhood-nsw.html",
        "https://asst2game.ru/nintendo-switch/dragon-ball-sparking-zero-switch.html"
    ]
    
    try:
        async with parser:
            for url in test_urls:
                print(f"\n=== Testing URL: {url} ===")
                
                # Загружаем страницу
                html = await parser.get_page(url)
                if not html:
                    print("Failed to load page")
                    continue
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Ищем контейнер с описанием по указанному пути
                description_container = soup.select_one('html body section:nth-of-type(2) section div div article div:nth-of-type(5) div:nth-of-type(2) div:nth-of-type(1) div div:nth-of-type(1) div:nth-of-type(2) main')
                
                if description_container:
                    print("Found description container!")
                    
                    # Ищем все <p> элементы внутри контейнера
                    paragraphs = description_container.find_all('p')
                    print(f"Found {len(paragraphs)} paragraphs")
                    
                    full_description = ""
                    for i, p in enumerate(paragraphs, 1):
                        text = p.get_text().strip()
                        if text:
                            print(f"\nParagraph {i}:")
                            print(f"Text: {text[:200]}...")  # Показываем первые 200 символов
                            full_description += text + "\n\n"
                    
                    print(f"\nFull description length: {len(full_description)} characters")
                    print(f"Full description preview: {full_description[:500]}...")
                    
                    # Сохраняем в файл
                    with open(f"description_{url.split('/')[-1].replace('.html', '')}.txt", 'w', encoding='utf-8') as f:
                        f.write(f"URL: {url}\n")
                        f.write("=" * 50 + "\n\n")
                        f.write(full_description)
                    
                    print(f"Saved to file: description_{url.split('/')[-1].replace('.html', '')}.txt")
                    
                else:
                    print("Description container not found!")
                    
                    # Пробуем другие селекторы
                    print("Trying alternative selectors...")
                    
                    # Селектор 1: ищем по классам
                    alt_container = soup.select_one('div.description-container, .description, .game-description')
                    if alt_container:
                        print("Found alternative container!")
                        paragraphs = alt_container.find_all('p')
                        print(f"Found {len(paragraphs)} paragraphs in alternative container")
                    
                    # Селектор 2: ищем по ID
                    alt_container2 = soup.select_one('#description, #game-description, #story')
                    if alt_container2:
                        print("Found container by ID!")
                        paragraphs = alt_container2.find_all('p')
                        print(f"Found {len(paragraphs)} paragraphs in ID container")
                
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        if hasattr(parser, 'session') and parser.session:
            await parser.session.close()

if __name__ == "__main__":
    asyncio.run(test_description_extraction())
