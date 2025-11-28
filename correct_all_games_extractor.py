#!/usr/bin/env python3
"""
ИСПРАВЛЕННЫЙ скрипт для извлечения ВСЕХ игр с правильной пагинацией
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import logging
import json
from urllib.parse import urljoin

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CorrectAllGamesExtractor:
    def __init__(self):
        self.base_url = "https://asst2game.ru"
        self.all_games_with_genres = []
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
        """Извлечь игры со страницы"""
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
        """Извлечь жанры по инструкции"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Ищем body > section.wrap.cf > section > div > div > article
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
    
    async def process_all_switch_games(self, max_pages: int = 200):
        """Обработать ВСЕ игры Nintendo Switch с правильной пагинацией"""
        logger.info(f"🚀 Начинаю обработку ВСЕХ игр Nintendo Switch с {max_pages} страниц")
        logger.info(f"🔗 Использую правильный URL: https://asst2game.ru/consoles/nintendo-switch/page/2/")
        
        total_processed = 0
        
        for page in range(1, max_pages + 1):
            # ПРАВИЛЬНЫЙ URL для пагинации
            if page == 1:
                url = "https://asst2game.ru/consoles/nintendo-switch/"
            else:
                url = f"https://asst2game.ru/consoles/nintendo-switch/page/{page}/"
            
            logger.info(f"📄 Страница {page}: {url}")
            html = await self.get_page(url)
            if not html:
                logger.warning(f"⚠️ Страница {page} не загрузилась")
                continue
            
            games = self.extract_games_from_page(html)
            if not games:
                logger.info(f"🏁 Игры на странице {page} не найдены - возможно это последняя страница")
                continue
            
            logger.info(f"📋 Найдено игр на странице {page}: {len(games)}")
            
            # Обрабатываем каждую игру на странице
            for i, game in enumerate(games, 1):
                total_processed += 1
                logger.info(f"🎮 [{total_processed}] {game['title']}")
                
                # Получаем страницу игры
                game_html = await self.get_page(game['url'])
                if game_html:
                    # Извлекаем жанры
                    genres = self.extract_genres_from_page(game_html, game['url'])
                    
                    # Сохраняем результат
                    result = {
                        'page': page,
                        'position_on_page': i,
                        'title': game['title'],
                        'url': game['url'],
                        'genres': genres,
                        'found_genres': len(genres) > 0
                    }
                    
                    self.all_games_with_genres.append(result)
                    
                    if genres:
                        genres_str = ", ".join(genres)
                        logger.info(f"✅ {game['title']} -> {genres_str}")
                    else:
                        logger.warning(f"❌ {game['title']} -> Жанры не найдены")
                
                # Небольшая задержка
                await asyncio.sleep(0.1)
            
            # Задержка между страницами
            await asyncio.sleep(0.5)
        
        logger.info(f"🎯 ВСЕГО обработано игр: {total_processed}")
        return total_processed
    
    def show_summary_stats(self):
        """Показать статистику"""
        total = len(self.all_games_with_genres)
        with_genres = sum(1 for g in self.all_games_with_genres if g['found_genres'])
        without_genres = total - with_genres
        
        logger.info("📊 СТАТИСТИКА:")
        logger.info(f"🎮 Всего игр: {total}")
        logger.info(f"✅ С жанрами: {with_genres}")
        logger.info(f"❌ Без жанров: {without_genres}")
        logger.info(f"📈 Процент с жанрами: {(with_genres/total*100):.1f}%")
        
        # Уникальные игры
        unique_titles = set(game['title'] for game in self.all_games_with_genres)
        logger.info(f"🎯 Уникальных игр: {len(unique_titles)}")
    
    def save_results(self, filename: str = "all_switch_games_correct.json"):
        """Сохранить результаты"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.all_games_with_genres, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 Результаты сохранены в {filename}")

async def main():
    logger.info("🚀 ЗАПУСК - ПРАВИЛЬНЫЙ СБОР ВСЕХ ИГР NINTENDO SWITCH!")
    
    async with CorrectAllGamesExtractor() as extractor:
        # Обрабатываем все игры с правильной пагинацией
        total = await extractor.process_all_switch_games(max_pages=50)  # Начнем с 50 страниц
        
        # Показываем статистику
        extractor.show_summary_stats()
        
        # Сохраняем
        extractor.save_results()
        
        logger.info("🎉 РАБОТА ЗАВЕРШЕНА!")

if __name__ == "__main__":
    asyncio.run(main())
