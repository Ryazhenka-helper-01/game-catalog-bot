#!/usr/bin/env python3
"""
Скрипт для показа ВСЕХ 800 игр с их жанрами (включая дубликаты)
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import logging
import json
from urllib.parse import urljoin

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AllGamesExtractor:
    def __init__(self):
        self.base_url = "https://asst2game.ru"
        self.all_games_with_genres = []  # ВСЕ игры с жанрами
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
        """Извлечь ВСЕ игры со страницы"""
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
        """Извлечь жанры по ТОЧНОЙ инструкции"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Шаг 2: Ищем body > section.wrap.cf > section > div > div > article
            main_container = soup.select_one('body > section.wrap.cf > section > div > div > article')
            
            if main_container:
                # Шаг 3: Ищем <meta itemprop="genre" content="жанры">
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
    
    async def process_all_800_games(self, max_pages: int = 100):
        """Обработать ВСЕ 800 игр"""
        logger.info(f"🚀 Начинаю обработку ВСЕХ 800 игр с {max_pages} страниц")
        
        total_processed = 0
        
        for page in range(1, max_pages + 1):
            url = f"{self.base_url}/page/{page}/" if page > 1 else self.base_url
            
            logger.info(f"📄 Страница {page}")
            html = await self.get_page(url)
            if not html:
                continue
            
            games = self.extract_games_from_page(html)
            if not games:
                logger.info(f"Игры на странице {page} не найдены")
                continue
            
            logger.info(f"📋 Найдено игр на странице {page}: {len(games)}")
            
            # Обрабатываем каждую игру на странице
            for i, game in enumerate(games, 1):
                total_processed += 1
                logger.info(f"🎮 [{total_processed}/800] {game['title']}")
                
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
                await asyncio.sleep(0.2)
            
            # Задержка между страницами
            await asyncio.sleep(1)
        
        logger.info(f"🎯 ВСЕГО обработано игр: {total_processed}")
        return total_processed
    
    def display_all_results(self):
        """Показать ВСЕ результаты как в Complete Genres"""
        logger.info("🎯 ПОЛНЫЙ СПИСОК ВСЕХ 800 ИГР С ЖАНРАМИ:")
        logger.info("=" * 100)
        
        for i, game in enumerate(self.all_games_with_genres, 1):
            status = "✅" if game['found_genres'] else "❌"
            genres_str = ", ".join(game['genres']) if game['genres'] else "НЕ НАЙДЕНО"
            
            logger.info(f"{status} [{i:3d}] Стр.{game['page']:2d} Поз.{game['position_on_page']:2d} | {game['title']}")
            logger.info(f"     🔗 {game['url']}")
            logger.info(f"     🏷️ {genres_str}")
            logger.info("")
        
        # Статистика
        with_genres = sum(1 for g in self.all_games_with_genres if g['found_genres'])
        without_genres = len(self.all_games_with_genres) - with_genres
        
        logger.info("=" * 100)
        logger.info("📊 СТАТИСТИКА:")
        logger.info(f"🎮 Всего игр: {len(self.all_games_with_genres)}")
        logger.info(f"✅ С жанрами: {with_genres}")
        logger.info(f"❌ Без жанров: {without_genres}")
        logger.info(f"📈 Процент с жанрами: {(with_genres/len(self.all_games_with_genres)*100):.1f}%")
    
    def save_all_results(self, filename: str = "all_800_games_complete.json"):
        """Сохранить ВСЕ результаты"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.all_games_with_genres, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 ВСЕ результаты сохранены в {filename}")
    
    def create_summary_report(self):
        """Создать отчет по жанрам"""
        genre_stats = {}
        
        for game in self.all_games_with_genres:
            if game['found_genres']:
                for genre in game['genres']:
                    if genre not in genre_stats:
                        genre_stats[genre] = []
                    genre_stats[genre].append(game['title'])
        
        logger.info("🎯 ОТЧЕТ ПО ЖАНРАМ:")
        logger.info("=" * 80)
        
        for genre, games in sorted(genre_stats.items(), key=lambda x: len(x[1]), reverse=True):
            logger.info(f"🏷️ {genre} ({len(games)} игр):")
            for game in games[:5]:  # Показываем первые 5 игр
                logger.info(f"   • {game}")
            if len(games) > 5:
                logger.info(f"   ... и еще {len(games)-5} игр")
            logger.info("")
        
        logger.info(f"📊 Всего найдено уникальных жанров: {len(genre_stats)}")

async def main():
    logger.info("🚀 ЗАПУСК - ВСЕ 800 ИГР С ЖАНРАМИ!")
    
    async with AllGamesExtractor() as extractor:
        # Обрабатываем все игры
        total = await extractor.process_all_800_games(max_pages=100)
        
        # Показываем ВСЕ результаты
        extractor.display_all_results()
        
        # Сохраняем
        extractor.save_all_results()
        
        # Создаем отчет по жанрам
        extractor.create_summary_report()
        
        logger.info("🎉 РАБОТА ЗАВЕРШЕНА! ВСЕ 800 ИГР ОБРАБОТАНЫ!")

if __name__ == "__main__":
    asyncio.run(main())
