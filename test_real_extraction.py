#!/usr/bin/env python3
"""
Тест реального извлечения описаний
"""

import asyncio
from parser import GameParser
from bs4 import BeautifulSoup

async def test_real_extraction():
    """Тест извлечения описаний как это делает бот"""
    
    parser = GameParser()
    
    try:
        async with parser:
            # Тестируем на одной игре
            url = "https://asst2game.ru/1234-until-then-switch.html"
            print(f"Testing URL: {url}")
            
            # Загружаем страницу как бот
            html = await parser.get_page(url)
            if not html:
                print("Failed to load page")
                return
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Используем ТОЧНО такой же метод как в боте
            def extract_full_description_bot(soup):
                """Извлечение полного описания как в боте"""
                
                # Способ 1: Ищем все параграфы в article (основной метод)
                try:
                    article = soup.find('article')
                    if article:
                        paragraphs = article.find_all('p')
                        print(f"Found {len(paragraphs)} paragraphs in article")
                        
                        texts = []
                        for i, p in enumerate(paragraphs):
                            text = p.get_text().strip()
                            print(f"\nParagraph {i+1}:")
                            print(f"Length: {len(text)} chars")
                            print(f"Text: {text[:200]}...")
                            
                            if text and len(text) > 20:  # Пропускаем очень короткие параграфы
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
                            return full_text
                        else:
                            print("No texts passed the filter")
                    else:
                        print("No article found")
                except Exception as e:
                    print(f"Error in method 1: {e}")
                
                return ""
            
            # Запускаем извлечение
            result = extract_full_description_bot(soup)
            
            print(f"\n=== FINAL RESULT ===")
            print(f"Description length: {len(result)} characters")
            print(f"Description:\n{result}")
            
            # Сохраняем результат
            with open("extracted_description.txt", 'w', encoding='utf-8') as f:
                f.write(f"URL: {url}\n")
                f.write("=" * 50 + "\n\n")
                f.write(result)
            
            print("\nSaved to extracted_description.txt")
            
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        if hasattr(parser, 'session') and parser.session:
            await parser.session.close()

if __name__ == "__main__":
    asyncio.run(test_real_extraction())
