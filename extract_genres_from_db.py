#!/usr/bin/env python3
"""
Скрипт для извлечения жанров из игр используя URL из базы данных
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import logging
import json
import sqlite3
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseGenreExtractor:
    def __init__(self):
        self.base_url = "https://asst2game.ru"
        self.found_genres = {}  # Название игры -> жанры
        self.session = None
        self.db_path = "games.db"
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def get_games_from_db(self):
        """Получить все игры из базы данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, title, url FROM games WHERE url IS NOT NULL AND url != ''")
            games = cursor.fetchall()
            
            conn.close()
            logger.info(f"Загружено {len(games)} игр из базы данных")
            return games
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке игр из БД: {e}")
            return []
    
    async def get_page(self, url: str) -> str:
        """Получить HTML страницы"""
        try:
            logger.info(f"🌐 Загружаю страницу: {url}")
            async with self.session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    logger.info(f"✅ Страница загружена: {len(content)} символов")
                    return content
                else:
                    logger.error(f"❌ Ошибка загрузки: {response.status}")
                    return ""
        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке {url}: {e}")
            return ""
    
    def extract_title_from_url(self, url: str) -> str:
        """Извлечь название игры из URL"""
        parsed = urlparse(url)
        path = parsed.path
        filename = path.split('/')[-1]
        if filename.endswith('.html'):
            filename = filename[:-5]
        title = filename.replace('-', ' ').title()
        return title
    
    def extract_genres_from_page(self, html_content: str, url: str) -> list:
        """Извлечь жанры из HTML по ТВОЕЙ инструкции"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Шаг 2: Ищем body > section.wrap.cf > section > div > div > article
            main_container = soup.select_one('body > section.wrap.cf > section > div > div > article')
            
            if main_container:
                logger.info(f"✅ Найден основной контейнер для {url}")
                
                # Шаг 3: Ищем <meta itemprop="genre" content="жанры">
                meta_genre = main_container.find('meta', attrs={'itemprop': 'genre'})
                if meta_genre and meta_genre.get('content'):
                    content = meta_genre.get('content').strip()
                    logger.info(f"✅ НАЙДЕНО МЕТА-ТЕГ: {content}")
                    
                    # Разделяем жанры по запятым
                    genres = [genre.strip() for genre in content.split(',') if genre.strip()]
                    logger.info(f"✅ ИЗВЛЕЧЕНЫ ЖАНРЫ: {genres}")
                    return genres
                else:
                    logger.warning(f"⚠️ Мета-тег itemprop='genre' не найден в контейнере")
            else:
                logger.warning(f"⚠️ Основной контейнер не найден для {url}")
            
            # Запасной вариант: ищем в любом месте страницы
            meta_genre_any = soup.find('meta', attrs={'itemprop': 'genre'})
            if meta_genre_any and meta_genre_any.get('content'):
                content = meta_genre_any.get('content').strip()
                logger.info(f"✅ НАЙДЕНО В ЛЮБОМ МЕСТЕ: {content}")
                genres = [genre.strip() for genre in content.split(',') if genre.strip()]
                return genres
            else:
                logger.warning(f"❌ Мета-тег itemprop='genre' не найден нигде на странице")
            
            return []
            
        except Exception as e:
            logger.error(f"❌ Ошибка при извлечении жанров из {url}: {e}")
            return []
    
    async def process_game(self, game_id: int, title: str, url: str) -> tuple:
        """Обработать одну игру"""
        logger.info(f"🎮 Обрабатываю игру: {title}")
        logger.info(f"🔗 URL: {url}")
        
        # 1. Получаем HTML
        html_content = await self.get_page(url)
        if not html_content:
            return title, []
        
        # 2. Извлекаем жанры
        genres = self.extract_genres_from_page(html_content, url)
        
        # 3. Сохраняем результат
        if genres:
            self.found_genres[title] = genres
            logger.info(f"🎯 РЕЗУЛЬТАТ: {title} -> {genres}")
        else:
            logger.warning(f"❌ ЖАНРЫ НЕ НАЙДЕНЫ: {title}")
        
        return title, genres
    
    async def process_all_games(self):
        """Обработать все игры из базы данных"""
        games = self.get_games_from_db()
        
        if not games:
            logger.error("❌ Игры в базе данных не найдены")
            return
        
        logger.info(f"🚀 Начинаю обработку {len(games)} игр")
        
        results = []
        for i, (game_id, title, url) in enumerate(games, 1):
            logger.info(f"📊 Прогресс: {i}/{len(games)}")
            
            processed_title, genres = await self.process_game(game_id, title, url)
            if genres:
                results.append({
                    'id': game_id,
                    'title': processed_title,
                    'url': url,
                    'genres': genres
                })
            
            # Небольшая задержка каждые 10 игр
            if i % 10 == 0:
                await asyncio.sleep(1)
        
        return results
    
    def display_results(self):
        """Показать результаты в формате: Название игры - жанры"""
        logger.info("🎯 КОНКРЕТНЫЕ РЕЗУЛЬТАТЫ ДЛЯ ПРОВЕРКИ:")
        logger.info("=" * 80)
        
        for title, genres in self.found_genres.items():
            genres_str = ", ".join(genres)
            logger.info(f"🎮 {title} - {genres_str}")
        
        logger.info("=" * 80)
        logger.info(f"📊 Всего игр с найденными жанрами: {len(self.found_genres)}")
    
    def save_to_file(self, filename: str = "final_genres.json"):
        """Сохранить результаты в файл"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.found_genres, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 Результаты сохранены в {filename}")

async def main():
    """Главная функция"""
    logger.info("🚀 ЗАПУСКАЮ ИЗВЛЕЧЕНИЕ ЖАНРОВ ИЗ БАЗЫ ДАННЫХ")
    
    async with DatabaseGenreExtractor() as extractor:
        # Обрабатываем все игры
        results = await extractor.process_all_games()
        
        # Показываем КОНКРЕТНЫЕ результаты
        extractor.display_results()
        
        # Сохраняем в файл
        extractor.save_to_file()
        
        logger.info("🎉 РАБОТА ЗАВЕРШЕНА! ПРОВЕРЬ РЕЗУЛЬТАТЫ ВЫШЕ.")

if __name__ == "__main__":
    asyncio.run(main())
