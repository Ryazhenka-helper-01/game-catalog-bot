#!/usr/bin/env python3
"""
Скрипт для извлечения жанров из игр на asst2game.ru
Инструкция:
1. Заходишь на сайт игры (URL с https://asst2game.ru/название-игры.html)
2. Ищешь в коде: body > section.wrap.cf > section > div > div > article
3. Находишь <meta itemprop="genre" content="жанры через запятую">
4. Заносишь в память: Название игры - жанры
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import logging
import json
from urllib.parse import urlparse
import re

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GenreExtractor:
    def __init__(self):
        self.base_url = "https://asst2game.ru"
        self.found_genres = {}  # Название игры -> жанры
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
        """Получить HTML страницы"""
        try:
            logger.info(f"Загружаю страницу: {url}")
            async with self.session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    logger.info(f"Страница загружена успешно: {len(content)} символов")
                    return content
                else:
                    logger.error(f"Ошибка загрузки страницы: {response.status}")
                    return ""
        except Exception as e:
            logger.error(f"Ошибка при загрузке {url}: {e}")
            return ""
    
    def extract_title_from_url(self, url: str) -> str:
        """Извлечь название игры из URL"""
        parsed = urlparse(url)
        path = parsed.path
        # Убираем .html и преобразуем в читаемое название
        filename = path.split('/')[-1]
        if filename.endswith('.html'):
            filename = filename[:-5]
        # Заменяем дефисы на пробелы и делаем заглавные буквы
        title = filename.replace('-', ' ').title()
        return title
    
    def extract_genres_from_page(self, html_content: str, url: str) -> list:
        """Извлечь жанры из HTML кода страницы"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 1. Ищем основной контейнер: body > section.wrap.cf > section > div > div > article
            main_container = soup.select_one('body > section.wrap.cf > section > div > div > article')
            if main_container:
                logger.info(f"✅ Найден основной контейнер для {url}")
                
                # 2. Ищем мета-тег с жанрами внутри этого контейнера
                meta_genre = main_container.find('meta', attrs={'itemprop': 'genre'})
                if meta_genre and meta_genre.get('content'):
                    content = meta_genre.get('content').strip()
                    logger.info(f"✅ Найден мета-тег жанров: {content}")
                    
                    # Разделяем жанры по запятым
                    genres = [genre.strip() for genre in content.split(',') if genre.strip()]
                    logger.info(f"✅ Извлечены жанры: {genres}")
                    return genres
                else:
                    logger.warning(f"⚠️ Мета-тег itemprop='genre' не найден в контейнере")
                    
                    # Ищем в любом месте страницы
                    meta_genre_any = soup.find('meta', attrs={'itemprop': 'genre'})
                    if meta_genre_any and meta_genre_any.get('content'):
                        content = meta_genre_any.get('content').strip()
                        logger.info(f"✅ Найден мета-тег жанров в любом месте: {content}")
                        genres = [genre.strip() for genre in content.split(',') if genre.strip()]
                        return genres
                    else:
                        logger.warning(f"❌ Мета-тег itemprop='genre' не найден нигде на странице")
            else:
                logger.warning(f"⚠️ Основной контейнер не найден для {url}")
                
                # Ищем мета-тег в любом случае
                meta_genre_any = soup.find('meta', attrs={'itemprop': 'genre'})
                if meta_genre_any and meta_genre_any.get('content'):
                    content = meta_genre_any.get('content').strip()
                    logger.info(f"✅ Найден мета-тег жанров без контейнера: {content}")
                    genres = [genre.strip() for genre in content.split(',') if genre.strip()]
                    return genres
            
            return []
            
        except Exception as e:
            logger.error(f"Ошибка при извлечении жанров из {url}: {e}")
            return []
    
    async def process_game(self, url: str) -> tuple:
        """Обработать одну игру"""
        logger.info(f"🎮 Начинаю обработку: {url}")
        
        # 1. Получаем HTML
        html_content = await self.get_page(url)
        if not html_content:
            return "", []
        
        # 2. Извлекаем название из URL
        title = self.extract_title_from_url(url)
        logger.info(f"📝 Название игры: {title}")
        
        # 3. Извлекаем жанры
        genres = self.extract_genres_from_page(html_content, url)
        
        # 4. Сохраняем результат
        if genres:
            self.found_genres[title] = genres
            logger.info(f"✅ СОХРАНЕНО: {title} -> {genres}")
        else:
            logger.warning(f"❌ Жанры не найдены для: {title}")
        
        return title, genres
    
    async def process_games_from_list(self, game_urls: list):
        """Обработать список игр"""
        logger.info(f"🚀 Начинаю обработку {len(game_urls)} игр")
        
        results = []
        for i, url in enumerate(game_urls, 1):
            logger.info(f"📊 Прогресс: {i}/{len(game_urls)}")
            
            title, genres = await self.process_game(url)
            if title and genres:
                results.append({
                    'title': title,
                    'url': url,
                    'genres': genres
                })
            
            # Небольшая задержка
            if i % 10 == 0:
                await asyncio.sleep(1)
        
        return results
    
    def display_results(self):
        """Показать результаты в формате: Название игры - жанры"""
        logger.info("🎯 РЕЗУЛЬТАТЫ ИЗВЛЕЧЕНИЯ ЖАНРОВ:")
        logger.info("=" * 60)
        
        for title, genres in self.found_genres.items():
            genres_str = ", ".join(genres)
            logger.info(f"🎮 {title} - {genres_str}")
        
        logger.info("=" * 60)
        logger.info(f"📊 Всего обработано игр: {len(self.found_genres)}")
    
    def save_to_file(self, filename: str = "extracted_genres.json"):
        """Сохранить результаты в файл"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.found_genres, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 Результаты сохранены в {filename}")

async def main():
    """Главная функция для тестирования"""
    # Тестовые URL игр
    test_urls = [
        "https://asst2game.ru/1234-until-then-switch.html",
        "https://asst2game.ru/the-legend-of-zelda-tears-of-the-kingdom-switch.html",
        "https://asst2game.ru/super-mario-odyssey-switch.html",
        "https://asst2game.ru/animal-crossing-new-horizons-switch.html",
        "https://asst2game.ru/mario-kart-8-deluxe-switch.html",
    ]
    
    async with GenreExtractor() as extractor:
        # Обрабатываем игры
        results = await extractor.process_games_from_list(test_urls)
        
        # Показываем результаты
        extractor.display_results()
        
        # Сохраняем в файл
        extractor.save_to_file()
        
        logger.info("🎉 Работа завершена!")

if __name__ == "__main__":
    asyncio.run(main())
