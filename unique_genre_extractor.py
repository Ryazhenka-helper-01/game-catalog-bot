#!/usr/bin/env python3
"""
Скрипт для получения УНИКАЛЬНЫХ игр и их жанров
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

class UniqueGenreExtractor:
    def __init__(self):
        self.base_url = "https://asst2game.ru"
        self.unique_games = {}  # URL -> title для уникальности
        self.found_genres = {}  # title -> genres
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
    
    def extract_unique_games_from_page(self, html_content: str) -> dict:
        """Извлечь УНИКАЛЬНЫЕ игры со страницы"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            page_games = {}
            
            articles = soup.find_all('article')
            for article in articles:
                link = article.find('a', href=True)
                if link and link.get('href').endswith('.html'):
                    href = link.get('href')
                    full_url = urljoin(self.base_url, href)
                    
                    # Проверяем уникальность по URL
                    if full_url not in self.unique_games:
                        title_elem = article.find('h1') or article.find('h2') or article.find('h3') or link
                        title = title_elem.get_text().strip() if title_elem else ""
                        
                        if title and full_url:
                            page_games[full_url] = title
            
            return page_games
        except Exception as e:
            logger.error(f"Ошибка извлечения игр: {e}")
            return {}
    
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
    
    async def collect_unique_games(self, max_pages: int = 100):
        """Собрать УНИКАЛЬНЫЕ игры"""
        logger.info(f"🚀 Собираю УНИКАЛЬНЫЕ игры с {max_pages} страниц")
        
        for page in range(1, max_pages + 1):
            url = f"{self.base_url}/page/{page}/" if page > 1 else self.base_url
            
            html = await self.get_page(url)
            if not html:
                continue
            
            page_games = self.extract_unique_games_from_page(html)
            if not page_games:
                logger.info(f"Новые игры на странице {page} не найдены")
                continue
            
            # Добавляем только новые игры
            new_count = 0
            for game_url, title in page_games.items():
                if game_url not in self.unique_games:
                    self.unique_games[game_url] = title
                    new_count += 1
            
            logger.info(f"📄 Страница {page}: +{new_count} новых игр, всего уникальных: {len(self.unique_games)}")
            
            await asyncio.sleep(0.5)
        
        logger.info(f"🎯 Всего собрано УНИКАЛЬНЫХ игр: {len(self.unique_games)}")
        return len(self.unique_games)
    
    async def extract_genres_for_unique_games(self):
        """Извлечь жанры для УНИКАЛЬНЫХ игр"""
        logger.info(f"🚀 Извлекаю жанры для {len(self.unique_games)} УНИКАЛЬНЫХ игр")
        
        processed = 0
        for i, (game_url, title) in enumerate(self.unique_games.items(), 1):
            logger.info(f"🎮 [{i}/{len(self.unique_games)}] {title}")
            
            html = await self.get_page(game_url)
            if html:
                genres = self.extract_genres_from_page(html, game_url)
                
                if genres:
                    self.found_genres[title] = genres
                    logger.info(f"✅ {title} -> {genres}")
                    processed += 1
                else:
                    logger.warning(f"❌ Жанры не найдены: {title}")
            
            # Задержка
            if i % 5 == 0:
                await asyncio.sleep(1)
        
        logger.info(f"🎉 Обработано УНИКАЛЬНЫХ игр с жанрами: {processed}/{len(self.unique_games)}")
        return processed
    
    def display_results(self):
        logger.info("🎯 КОНКРЕТНЫЕ РЕЗУЛЬТАТЫ УНИКАЛЬНЫХ ИГР:")
        logger.info("=" * 80)
        
        for title, genres in self.found_genres.items():
            genres_str = ", ".join(genres)
            logger.info(f"🎮 {title} - {genres_str}")
        
        logger.info("=" * 80)
        logger.info(f"📊 Всего УНИКАЛЬНЫХ игр с жанрами: {len(self.found_genres)}")
    
    def save_results(self, filename: str = "unique_genres.json"):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.found_genres, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 Сохранено в {filename}")
    
    def update_bot_database(self):
        """Обновить базу данных бота УНИКАЛЬНЫМИ играми"""
        try:
            conn = sqlite3.connect('games.db')
            cursor = conn.cursor()
            
            # Сначала добавляем уникальные игры в базу
            added = 0
            for game_url, title in self.unique_games.items():
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO games (title, url)
                        VALUES (?, ?)
                    ''', (title, game_url))
                    
                    if cursor.rowcount > 0:
                        added += 1
                except Exception as e:
                    logger.warning(f"Ошибка добавления {title}: {e}")
            
            conn.commit()
            logger.info(f"➕ Добавлено УНИКАЛЬНЫХ игр в БД: {added}")
            
            # Теперь обновляем жанры
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
                    logger.warning(f"Ошибка обновления жанров {title}: {e}")
            
            conn.commit()
            conn.close()
            
            logger.info(f"🗄️ Обновлено жанров в БД: {updated}")
            return added, updated
            
        except Exception as e:
            logger.error(f"Ошибка работы с БД: {e}")
            return 0, 0

async def main():
    logger.info("🚀 ЗАПУСК - УНИКАЛЬНЫЕ ИГРЫ И ЖАНРЫ")
    
    async with UniqueGenreExtractor() as extractor:
        # Шаг 1: Собрать уникальные игры
        unique_count = await extractor.collect_unique_games(max_pages=100)
        
        # Шаг 2: Извлечь жанры для уникальных игр
        processed = await extractor.extract_genres_for_unique_games()
        
        # Шаг 3: Показать результаты
        extractor.display_results()
        
        # Шаг 4: Сохранить
        extractor.save_results()
        
        # Шаг 5: Обновить базу бота
        added, updated = extractor.update_bot_database()
        
        logger.info("🎉 РАБОТА ЗАВЕРШЕНА!")
        logger.info(f"📊 Уникальных игр: {unique_count}")
        logger.info(f"✅ Обработано с жанрами: {processed}")
        logger.info(f"➕ Добавлено в БД: {added}")
        logger.info(f"🗄️ Обновлено жанров: {updated}")

if __name__ == "__main__":
    asyncio.run(main())
