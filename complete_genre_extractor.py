#!/usr/bin/env python3
"""
ПОЛНЫЙ СКРИПТ ДЛЯ ИЗВЛЕЧЕНИЯ ЖАНРОВ:
1. Наполняет базу данных играми
2. Извлекает жанры для каждой игры
3. Показывает результаты: Название игры - жанры
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import logging
import json
import sqlite3
import re
from datetime import datetime
from urllib.parse import urlparse, urljoin

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CompleteGenreExtractor:
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
        await self.init_db()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def init_db(self):
        """Инициализация базы данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL UNIQUE,
                    description TEXT,
                    rating TEXT,
                    genres TEXT,
                    image_url TEXT,
                    screenshots TEXT,
                    release_date TEXT,
                    url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ База данных инициализирована")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации БД: {e}")
    
    async def get_page(self, url: str) -> str:
        """Получить HTML страницы"""
        try:
            logger.info(f"🌐 Загружаю: {url}")
            async with self.session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    logger.info(f"✅ Загружено: {len(content)} символов")
                    return content
                else:
                    logger.error(f"❌ Ошибка: {response.status}")
                    return ""
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки {url}: {e}")
            return ""
    
    def extract_games_from_page(self, html_content: str) -> list:
        """Извлечь игры со страницы"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            games = []
            
            # Ищем все статьи с играми
            articles = soup.find_all('article')
            logger.info(f"📄 Найдено статей: {len(articles)}")
            
            for article in articles:
                # Ищем ссылку на игру
                link = article.find('a', href=True)
                if link:
                    href = link.get('href')
                    if href and href.endswith('.html'):
                        full_url = urljoin(self.base_url, href)
                        
                        # Ищем название
                        title_elem = article.find('h1') or article.find('h2') or article.find('h3') or link
                        title = title_elem.get_text().strip() if title_elem else ""
                        
                        if title and full_url:
                            games.append({
                                'title': title,
                                'url': full_url
                            })
            
            logger.info(f"🎮 Найдено игр на странице: {len(games)}")
            return games
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения игр: {e}")
            return []
    
    async def scrape_games(self, max_pages: int = 10):
        """Собрать игры с сайта"""
        logger.info(f"🚀 Начинаю сбор игр (максимум {max_pages} страниц)")
        
        all_games = []
        
        for page in range(1, max_pages + 1):
            url = f"{self.base_url}/page/{page}/" if page > 1 else self.base_url
            
            html = await self.get_page(url)
            if not html:
                continue
            
            games = self.extract_games_from_page(html)
            if not games:
                logger.info(f"⚠️ Игры на странице {page} не найдены")
                break
            
            all_games.extend(games)
            logger.info(f"📊 Страница {page}: +{len(games)} игр, всего: {len(all_games)}")
            
            # Задержка
            await asyncio.sleep(1)
        
        logger.info(f"🎯 Всего собрано игр: {len(all_games)}")
        return all_games
    
    def save_games_to_db(self, games: list):
        """Сохранить игры в базу данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            saved = 0
            for game in games:
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO games (title, url)
                        VALUES (?, ?)
                    ''', (game['title'], game['url']))
                    
                    if cursor.rowcount > 0:
                        saved += 1
                        
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка сохранения {game['title']}: {e}")
                    continue
            
            conn.commit()
            conn.close()
            
            logger.info(f"💾 Сохранено игр в БД: {saved}")
            return saved
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения в БД: {e}")
            return 0
    
    def extract_genres_from_page(self, html_content: str, url: str) -> list:
        """Извлечь жанры по ТВОЕЙ инструкции"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Ищем основной контейнер: body > section.wrap.cf > section > div > div > article
            main_container = soup.select_one('body > section.wrap.cf > section > div > div > article')
            
            if main_container:
                logger.info(f"✅ Найден контейнер для {url}")
                
                # Ищем мета-тег с жанрами
                meta_genre = main_container.find('meta', attrs={'itemprop': 'genre'})
                if meta_genre and meta_genre.get('content'):
                    content = meta_genre.get('content').strip()
                    logger.info(f"✅ НАЙДЕНО: {content}")
                    
                    genres = [genre.strip() for genre in content.split(',') if genre.strip()]
                    logger.info(f"✅ ЖАНРЫ: {genres}")
                    return genres
                else:
                    logger.warning(f"⚠️ Мета-тег не найден в контейнере")
            else:
                logger.warning(f"⚠️ Контейнер не найден для {url}")
            
            # Запасной вариант
            meta_genre_any = soup.find('meta', attrs={'itemprop': 'genre'})
            if meta_genre_any and meta_genre_any.get('content'):
                content = meta_genre_any.get('content').strip()
                logger.info(f"✅ НАЙДЕНО В ЛЮБОМ МЕСТЕ: {content}")
                genres = [genre.strip() for genre in content.split(',') if genre.strip()]
                return genres
            
            return []
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения жанров: {e}")
            return []
    
    async def extract_genres_for_all_games(self):
        """Извлечь жанры для всех игр из БД"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, title, url FROM games WHERE url IS NOT NULL")
            games = cursor.fetchall()
            conn.close()
            
            logger.info(f"🚀 Извлекаю жанры для {len(games)} игр")
            
            for i, (game_id, title, url) in enumerate(games, 1):
                logger.info(f"📊 Прогресс: {i}/{len(games)}")
                
                html = await self.get_page(url)
                if html:
                    genres = self.extract_genres_from_page(html, url)
                    
                    if genres:
                        self.found_genres[title] = genres
                        logger.info(f"🎯 РЕЗУЛЬТАТ: {title} -> {genres}")
                        
                        # Обновляем в БД
                        try:
                            conn = sqlite3.connect(self.db_path)
                            cursor = conn.cursor()
                            cursor.execute('''
                                UPDATE games SET genres = ? WHERE id = ?
                            ''', (json.dumps(genres, ensure_ascii=False), game_id))
                            conn.commit()
                            conn.close()
                        except Exception as e:
                            logger.warning(f"⚠️ Ошибка обновления БД: {e}")
                    else:
                        logger.warning(f"❌ Жанры не найдены: {title}")
                
                # Задержка
                if i % 5 == 0:
                    await asyncio.sleep(1)
            
            logger.info(f"🎯 Всего найдено жанров: {len(self.found_genres)}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения жанров: {e}")
    
    def display_results(self):
        """Показать КОНКРЕТНЫЕ результаты"""
        logger.info("🎯 КОНКРЕТНЫЕ РЕЗУЛЬТАТЫ: Название игры - жанры")
        logger.info("=" * 80)
        
        for title, genres in self.found_genres.items():
            genres_str = ", ".join(genres)
            logger.info(f"🎮 {title} - {genres_str}")
        
        logger.info("=" * 80)
        logger.info(f"📊 Всего игр с жанрами: {len(self.found_genres)}")
    
    def save_results(self, filename: str = "complete_genres.json"):
        """Сохранить результаты"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.found_genres, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 Сохранено в {filename}")

async def main():
    """Главная функция"""
    logger.info("🚀 ЗАПУСК ПОЛНОГО ИЗВЛЕЧЕНИЯ ЖАНРОВ")
    
    async with CompleteGenreExtractor() as extractor:
        # Шаг 1: Собираем игры
        games = await extractor.scrape_games(max_pages=100)  # ВСЕ СТРАНИЦЫ - ПОЛНЫЙ СБОР
        
        if games:
            # Шаг 2: Сохраняем в БД
            saved = extractor.save_games_to_db(games)
            logger.info(f"💾 Сохранено игр: {saved}")
            
            # Шаг 3: Извлекаем жанры
            await extractor.extract_genres_for_all_games()
            
            # Шаг 4: Показываем КОНКРЕТНЫЕ результаты
            extractor.display_results()
            
            # Шаг 5: Сохраняем
            extractor.save_results()
        
        logger.info("🎉 РАБОТА ЗАВЕРШЕНА! ПРОВЕРЬ РЕЗУЛЬТАТЫ ВЫШЕ.")

if __name__ == "__main__":
    asyncio.run(main())
