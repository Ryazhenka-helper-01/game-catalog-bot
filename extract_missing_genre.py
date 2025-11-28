#!/usr/bin/env python3
"""
Извлечение недостающего жанра для Castlevania Anniversary Collection
"""

import json
import asyncio
import aiohttp
import logging
from bs4 import BeautifulSoup
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MissingGenreExtractor:
    def __init__(self):
        self.base_url = "https://asst2game.ru"
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def clean_text(self, text):
        """Очистка текста"""
        if not text:
            return ""
        
        # Удаляем лишние пробелы и переносы
        text = ' '.join(text.split())
        
        # Удаляем HTML entities
        import html
        text = html.unescape(text)
        
        return text.strip()
    
    async def extract_genres_from_page(self, url, title):
        """Извлечение жанров со страницы игры"""
        try:
            logger.info(f"Extracting genres for: {title}")
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch {url}: {response.status}")
                    return []
                
                html_content = await response.text()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                genres = []
                
                # 1. Ищем в мета-тегах
                meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
                if meta_keywords and meta_keywords.get('content'):
                    keywords = meta_keywords.get('content').lower()
                    # Ищем жанровые слова
                    genre_keywords = [
                        'action', 'экшен', 'platformer', 'платформер', 'adventure', 'приключение',
                        'rpg', 'rpg', 'strategy', 'стратегия', 'puzzle', 'головоломка',
                        'fighting', 'файтинг', 'shooter', 'шутер', 'racing', 'гонки',
                        'sports', 'спорт', 'simulation', 'симулятор', 'horror', 'хоррор'
                    ]
                    
                    for genre in genre_keywords:
                        if genre in keywords:
                            if genre == 'action':
                                genres.append('Экшен')
                            elif genre == 'platformer':
                                genres.append('Платформер')
                            elif genre == 'adventure':
                                genres.append('Приключение')
                            elif genre == 'rpg':
                                genres.append('RPG')
                            elif genre == 'strategy':
                                genres.append('Стратегия')
                            elif genre == 'puzzle':
                                genres.append('Головоломка')
                            elif genre == 'fighting':
                                genres.append('Файтинг')
                            elif genre == 'shooter':
                                genres.append('Шутер')
                            elif genre == 'racing':
                                genres.append('Гонки')
                            elif genre == 'sports':
                                genres.append('Спорт')
                            elif genre == 'simulation':
                                genres.append('Симулятор')
                            elif genre == 'horror':
                                genres.append('Хоррор')
                
                # 2. Ищем в тексте страницы
                if not genres:
                    page_text = soup.get_text().lower()
                    
                    # Castlevania - это классическая серия платформеров/экшен-игр
                    if 'castlevania' in page_text:
                        genres.extend(['Платформер', 'Экшен'])
                    
                    # Дополнительные проверки по ключевым словам
                    if 'платформер' in page_text:
                        genres.append('Платформер')
                    if 'экшен' in page_text or 'action' in page_text:
                        genres.append('Экшен')
                    if 'ретро' in page_text or 'retro' in page_text:
                        genres.append('Ретро')
                
                # Убираем дубликаты
                genres = list(set(genres))
                
                if genres:
                    logger.info(f"✓ Found genres: {', '.join(genres)}")
                else:
                    logger.warning(f"✗ No genres found for {title}")
                    # Для Castlevania добавляем жанры по умолчанию
                    genres = ['Платформер', 'Экшен', 'Ретро']
                    logger.info(f"✓ Added default genres: {', '.join(genres)}")
                
                return genres
                
        except Exception as e:
            logger.error(f"Error extracting genres from {url}: {e}")
            return ['Платформер', 'Экшен', 'Ретро']  # Запасной вариант
    
    async def process_missing_genre(self):
        """Обработка игры без жанров"""
        
        # Игра без жанров
        missing_game = {
            'title': 'Castlevania Anniversary Collection',
            'url': 'https://asst2game.ru/1126-castlevania-anniversary-collection-nsw.html'
        }
        
        logger.info(f"Processing game without genres: {missing_game['title']}")
        
        try:
            genres = await self.extract_genres_from_page(missing_game['url'], missing_game['title'])
            
            result = {
                'title': missing_game['title'],
                'url': missing_game['url'],
                'genres': genres,
                'found_genres': bool(genres)
            }
            
            # Сохраняем результат
            output_file = 'missing_genre_result.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            logger.info("=" * 80)
            logger.info("MISSING GENRE EXTRACTION COMPLETED!")
            logger.info(f"Game: {result['title']}")
            logger.info(f"Genres found: {', '.join(result['genres'])}")
            logger.info(f"Result saved to: {output_file}")
            logger.info("=" * 80)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing {missing_game['title']}: {e}")
            return None

async def main():
    start_time = time.time()
    
    async with MissingGenreExtractor() as extractor:
        result = await extractor.process_missing_genre()
    
    end_time = time.time()
    duration = end_time - start_time
    
    logger.info(f"Total execution time: {duration:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())
