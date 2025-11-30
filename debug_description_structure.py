#!/usr/bin/env python3
"""
Анализ структуры страницы для поиска описаний
"""

import asyncio
from parser import GameParser
from bs4 import BeautifulSoup
import json

async def debug_description_structure():
    """Анализ структуры страницы для поиска описаний"""
    
    parser = GameParser()
    
    # Пробуем найти рабочую страницу
    test_urls = [
        "https://asst2game.ru/1234-until-then-switch.html",
        "https://asst2game.ru/nintendo-switch/1234-until-then-switch.html",
        "https://asst2game.ru/consoles/nintendo-switch/1234-until-then-switch.html"
    ]
    
    try:
        async with parser:
            for url in test_urls:
                print(f"\n=== Testing URL: {url} ===")
                
                html = await parser.get_page(url)
                if not html:
                    print("Failed to load page")
                    continue
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Ищем все параграфы на странице
                all_paragraphs = soup.find_all('p')
                print(f"Total paragraphs found: {len(all_paragraphs)}")
                
                # Показываем первые 10 параграфов с их содержимым
                print("\nFirst 10 paragraphs:")
                for i, p in enumerate(all_paragraphs[:10]):
                    text = p.get_text().strip()
                    if text and len(text) > 20:  # Показываем только осмысленные параграфы
                        print(f"\nParagraph {i+1}:")
                        print(f"Length: {len(text)} chars")
                        print(f"Preview: {text[:200]}...")
                        
                        # Показываем путь к этому параграфу
                        path = get_element_path(p)
                        print(f"Path: {path}")
                
                # Ищем контейнеры с описанием
                print("\n=== Looking for description containers ===")
                
                # Метод 1: Ищем по указанному пути
                try:
                    container = soup.select_one('body > section.wrap.cf > section > div > div > article > div:nth-of-type(5) > div:nth-of-type(2) > div > div > div:nth-of-type(1) > div:nth-of-type(2) > main')
                    if container:
                        paragraphs = container.find_all('p')
                        print(f"Method 1: Found {len(paragraphs)} paragraphs in specified container")
                        for i, p in enumerate(paragraphs[:3]):
                            text = p.get_text().strip()
                            if text:
                                print(f"  P{i+1}: {text[:100]}...")
                    else:
                        print("Method 1: Container not found")
                except Exception as e:
                    print(f"Method 1: Error - {e}")
                
                # Метод 2: Ищем article и все параграфы в нем
                try:
                    article = soup.find('article')
                    if article:
                        paragraphs = article.find_all('p')
                        print(f"Method 2: Found {len(paragraphs)} paragraphs in article")
                        for i, p in enumerate(paragraphs[:3]):
                            text = p.get_text().strip()
                            if text and len(text) > 50:
                                print(f"  P{i+1}: {text[:100]}...")
                    else:
                        print("Method 2: Article not found")
                except Exception as e:
                    print(f"Method 2: Error - {e}")
                
                # Метод 3: Ищем по классам
                description_classes = ['.description', '.game-description', '.summary', '.about', '.post-content', '.entry-content']
                for class_name in description_classes:
                    try:
                        elem = soup.select_one(class_name)
                        if elem:
                            paragraphs = elem.find_all('p')
                            print(f"Method 3 ({class_name}): Found {len(paragraphs)} paragraphs")
                            for i, p in enumerate(paragraphs[:2]):
                                text = p.get_text().strip()
                                if text and len(text) > 50:
                                    print(f"  P{i+1}: {text[:100]}...")
                        else:
                            print(f"Method 3 ({class_name}): Not found")
                    except Exception as e:
                        print(f"Method 3 ({class_name}): Error - {e}")
                
                # Метод 4: Ищем main элементы
                try:
                    mains = soup.find_all('main')
                    print(f"Method 4: Found {len(mains)} main elements")
                    for i, main in enumerate(mains):
                        paragraphs = main.find_all('p')
                        print(f"  Main {i+1}: {len(paragraphs)} paragraphs")
                        for j, p in enumerate(paragraphs[:2]):
                            text = p.get_text().strip()
                            if text and len(text) > 50:
                                print(f"    P{j+1}: {text[:100]}...")
                except Exception as e:
                    print(f"Method 4: Error - {e}")
                
                # Сохраняем HTML для анализа
                with open(f"debug_page_{url.split('/')[-1].replace('.html', '')}.html", 'w', encoding='utf-8') as f:
                    f.write(html)
                print(f"Saved HTML to debug_page_{url.split('/')[-1].replace('.html', '')}.html")
                
                break  # Если нашли рабочую страницу, выходим
                
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        if hasattr(parser, 'session') and parser.session:
            await parser.session.close()

def get_element_path(element):
    """Получить путь элемента в DOM"""
    path = []
    current = element
    
    while current and current.name:
        # Добавляем информацию о теге
        path_info = current.name
        
        # Добавляем класс если есть
        if current.get('class'):
            classes = ' '.join(current.get('class'))
            path_info += f".{classes}"
        
        # Добавляем nth-child если нужно
        siblings = [sibling for sibling in current.previous_siblings if sibling.name == current.name]
        if siblings:
            path_info += f":nth-of-type({len(siblings) + 2})"
        
        path.insert(0, path_info)
        current = current.parent
    
    return ' > '.join(path[:8])  # Ограничиваем глубину пути

if __name__ == "__main__":
    asyncio.run(debug_description_structure())
