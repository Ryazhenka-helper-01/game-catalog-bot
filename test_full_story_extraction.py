#!/usr/bin/env python3
"""
Тест извлечения описаний из div class="full-story"
"""

import asyncio
from parser import GameParser
from bs4 import BeautifulSoup

async def test_full_story_extraction():
    """Тест извлечения из full-story"""
    
    parser = GameParser()
    
    try:
        async with parser:
            url = "https://asst2game.ru/1234-until-then-switch.html"
            print(f"Testing URL: {url}")
            
            html = await parser.get_page(url)
            if not html:
                print("Failed to load page")
                return
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Ищем div class="full-story"
            full_story_div = soup.find('div', class_='full-story')
            
            if full_story_div:
                print("Found div.full-story!")
                
                # Ищем все параграфы внутри
                paragraphs = full_story_div.find_all('p')
                print(f"Found {len(paragraphs)} paragraphs in full-story")
                
                texts = []
                for i, p in enumerate(paragraphs):
                    text = p.get_text().strip()
                    print(f"\nParagraph {i+1}:")
                    print(f"Length: {len(text)} chars")
                    print(f"Text: {text[:200]}...")
                    
                    if text and len(text) > 20:
                        texts.append(text)
                        print("ADDED to result")
                    else:
                        print("SKIPPED (too short)")
                
                if texts:
                    full_text = "\n\n".join(texts)
                    print(f"\nFinal result:")
                    print(f"Total paragraphs used: {len(texts)}")
                    print(f"Total length: {len(full_text)} chars")
                    print(f"Full text preview:\n{full_text[:500]}...")
                    
                    # Сохраняем результат
                    with open("full_story_description.txt", 'w', encoding='utf-8') as f:
                        f.write(f"URL: {url}\n")
                        f.write("=" * 50 + "\n\n")
                        f.write(full_text)
                    
                    print("\nSaved to full_story_description.txt")
                else:
                    print("No texts passed the filter")
            else:
                print("div.full-story not found!")
                
                # Ищем похожие классы
                similar_divs = soup.find_all('div', class_=lambda x: x and 'story' in x.lower())
                print(f"Found {len(similar_divs)} divs with 'story' in class:")
                for div in similar_divs[:3]:
                    class_name = div.get('class', [])
                    print(f"  Class: {class_name}")
                    paragraphs = div.find_all('p')
                    print(f"  Paragraphs: {len(paragraphs)}")
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        if hasattr(parser, 'session') and parser.session:
            await parser.session.close()

if __name__ == "__main__":
    asyncio.run(test_full_story_extraction())
