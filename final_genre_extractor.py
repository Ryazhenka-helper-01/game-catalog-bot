#!/usr/bin/env python3
"""
ФИНАЛЬНЫЙ СКРИПТ - обрабатывает ВСЕ 800 игр сразу
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import logging
import json
import sqlite3
from urllib.parse import urljoin

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FinalGenreExtractor:
    def __init__(self):
        self.base_url = "https://asst2game.ru"
        self.found_genres = {}
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
    
    async def get_page(self, url: str) -> str:
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.text()
        except Exception as e:
            logger.error(f"Ошибка загрузки {url}: {e}")
        return ""
    
    def extract_games_from_page(self, html_content: str) -> list:
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            games = []
            
            articles = soup.find_all('article')
            for article in articles:
                link = article.find('a', href=True)
                if link and link.get('href').endswith('.html'):
                    href = link.get('href')
                    full_url = urljoin(self.base_url, href)
                    
                    title_elem = article.find('h1') or article.find('h2') or article.find('h3') or link
                    title = title_elem.get_text().strip() if title_elem else ""
                    
                    if title and full_url:
                        games.append({'title': title, 'url': full_url})
            
            return games
        except Exception as e:
            logger.error(f"Ошибка извлечения игр: {e}")
            return []
    
    def extract_genres_from_page(self, html_content: str, url: str) -> list:
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Ищем контейнер
            main_container = soup.select_one('body > section.wrap.cf > section > div > div > article')
            
            if main_container:
                meta_genre = main_container.find('meta', attrs={'itemprop': 'genre'})
                if meta_genre and meta_genre.get('content'):
                    content = meta_genre.get('content').strip()
                    genres = [genre.strip() for genre in content.split(',') if genre.strip()]
                    return genres
            
            # Запасной вариант
            meta_genre_any = soup.find('meta', attrs={'itemprop': 'genre'})
            if meta_genre_any and meta_genre_any.get('content'):
                content = meta_genre_any.get('content').strip()
                genres = [genre.strip() for genre in content.split(',') if genre.strip()]
                return genres
            
            return []
        except Exception as e:
            logger.error(f"Ошибка извлечения жанров: {e}")
            return []
    
    async def process_all_games(self, max_pages: int = 100):
        """Обработать ВСЕ игры"""
        logger.info(f"🚀 Начинаю обработку ВСЕХ игр с {max_pages} страниц")
        
        all_games = []
        
        # Шаг 1: Собрать все игры
        for page in range(1, max_pages + 1):
            url = f"{self.base_url}/page/{page}/" if page > 1 else self.base_url
            
            html = await self.get_page(url)
            if not html:
                continue
            
            games = self.extract_games_from_page(html)
            if not games:
                logger.info(f"Игры на странице {page} не найдены")
                break
            
            all_games.extend(games)
            logger.info(f"📄 Страница {page}: +{len(games)} игр, всего: {len(all_games)}")
            
            await asyncio.sleep(0.5)
        
        logger.info(f"🎯 Всего собрано игр: {len(all_games)}")
        
        # Шаг 2: Обработать каждую игру
        processed = 0
        for i, game in enumerate(all_games, 1):
            logger.info(f"🎮 [{i}/{len(all_games)}] {game['title']}")
            
            html = await self.get_page(game['url'])
            if html:
                genres = self.extract_genres_from_page(html, game['url'])
                
                if genres:
                    self.found_genres[game['title']] = genres
                    logger.info(f"✅ {game['title']} -> {genres}")
                    processed += 1
                else:
                    logger.warning(f"❌ Жанры не найдены: {game['title']}")
            
            # Задержка
            if i % 10 == 0:
                await asyncio.sleep(2)
        
        logger.info(f"🎉 Обработано игр с жанрами: {processed}/{len(all_games)}")
        return processed
    
    def display_results(self):
        logger.info("🎯 КОНКРЕТНЫЕ РЕЗУЛЬТАТЫ:")
        logger.info("=" * 80)
        
        for title, genres in self.found_genres.items():
            genres_str = ", ".join(genres)
            logger.info(f"🎮 {title} - {genres_str}")
        
        logger.info("=" * 80)
        logger.info(f"📊 Всего игр с жанрами: {len(self.found_genres)}")
    
    def save_results(self, filename: str = "all_genres.json"):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.found_genres, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 Сохранено в {filename}")
    
    def update_database(self):
        """Обновить базу данных бота"""
        try:
            conn = sqlite3.connect('games.db')
            cursor = conn.cursor()
            
            updated = 0
            for title, genres in self.found_genres.items():
                try:
                    genres_json = json.dumps(genres, ensure_ascii=False)
                    cursor.execute('''
                        UPDATE games SET genres = ? WHERE title = ?
                    ''', (genres_json, title))
                    
                    if cursor.rowcount > 0:
                        updated += 1
                except Exception as e:
                    logger.warning(f"Ошибка обновления {title}: {e}")
            
            conn.commit()
            conn.close()
            
            logger.info(f"🗄️ Обновлено записей в БД: {updated}")
            return updated
            
        except Exception as e:
            logger.error(f"Ошибка работы с БД: {e}")
            return 0

async def main():
    logger.info("🚀 ФИНАЛЬНЫЙ ЗАПУСК - ВСЕ 800 ИГР!")
    
    async with FinalGenreExtractor() as extractor:
        # Обрабатываем все игры
        processed = await extractor.process_all_games(max_pages=100)
        
        # Показываем результаты
        extractor.display_results()
        
        # Сохраняем
        extractor.save_results()
        
        # Обновляем базу данных
        extractor.update_database()
        
        logger.info("🎉 РАБОТА ЗАВЕРШЕНА! ВСЕ ЖАНРЫ ИЗВЛЕЧЕНЫ!")

if __name__ == "__main__":
    asyncio.run(main())
