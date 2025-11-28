#!/usr/bin/env python3
"""
Скрипт для обхода ВСЕХ страниц Nintendo Switch от page/1/ до page/N/
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import logging
import json
from urllib.parse import urljoin

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AllPagesExtractor:
    def __init__(self):
        self.base_url = "https://asst2game.ru"
        self.all_games = []
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
                    content = await response.text()
                    logger.info(f"✅ Страница загружена: {len(content)} символов")
                    return content
                else:
                    logger.warning(f"⚠️ Статус {response.status} для {url}")
                    return ""
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки {url}: {e}")
            return ""
    
    def extract_games_from_page(self, html_content: str, page_num: int) -> list:
        """Извлечь игры со страницы"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            games = []
            
            articles = soup.find_all('article')
            logger.info(f"📄 Страница {page_num}: найдено {len(articles)} статей")
            
            for article in articles:
                link = article.find('a', href=True)
                if link and link.get('href') and link.get('href').endswith('.html'):
                    href = link.get('href')
                    full_url = urljoin(self.base_url, href)
                    
                    title_elem = article.find('h1') or article.find('h2') or article.find('h3') or link
                    title = title_elem.get_text().strip() if title_elem else ""
                    
                    if title and full_url:
                        games.append({
                            'title': title,
                            'url': full_url,
                            'page': page_num
                        })
            
            logger.info(f"🎮 Страница {page_num}: извлечено {len(games)} игр")
            return games
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения игр со страницы {page_num}: {e}")
            return []
    
    def extract_genres_from_game_page(self, html_content: str, game_url: str) -> list:
        """Извлечь жанры из страницы игры"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Ищем основной контейнер
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
            logger.error(f"❌ Ошибка извлечения жанров из {game_url}: {e}")
            return []
    
    async def process_all_pages(self, max_pages: int = 500):
        """Обработать ВСЕ страницы от page/1/ до page/max_pages/"""
        logger.info(f"🚀 Начинаю обход ВСЕХ страниц Nintendo Switch!")
        logger.info(f"📊 Буду проверять страницы от 1 до {max_pages}")
        logger.info(f"🔗 Формат URL: https://asst2game.ru/consoles/nintendo-switch/page/N/")
        
        total_games = 0
        pages_with_games = 0
        empty_pages = 0
        
        for page_num in range(1, max_pages + 1):
            # Формируем правильный URL
            if page_num == 1:
                url = "https://asst2game.ru/consoles/nintendo-switch/"
            else:
                url = f"https://asst2game.ru/consoles/nintendo-switch/page/{page_num}/"
            
            logger.info(f"📄 Обрабатываю страницу {page_num}: {url}")
            
            # Получаем страницу
            html = await self.get_page(url)
            if not html:
                empty_pages += 1
                logger.warning(f"⚠️ Страница {page_num} пуста или не доступна")
                
                # Если 3 страницы подряд пустые, возможно достигли конца
                if empty_pages >= 3:
                    logger.info(f"🏁 {empty_pages} страниц подряд пусты. Возможно достигнут конец.")
                    break
                continue
            
            # Извлекаем игры
            games = self.extract_games_from_page(html, page_num)
            if not games:
                empty_pages += 1
                logger.warning(f"⚠️ Игры на странице {page_num} не найдены")
                
                if empty_pages >= 3:
                    logger.info(f"🏁 {empty_pages} страниц подряд без игр. Прерываю поиск.")
                    break
                continue
            
            # Сбрасываем счетчик пустых страниц
            empty_pages = 0
            pages_with_games += 1
            
            # Обрабатываем каждую игру на странице
            page_games_with_genres = 0
            for i, game in enumerate(games, 1):
                total_games += 1
                
                # Получаем страницу игры
                game_html = await self.get_page(game['url'])
                if game_html:
                    # Извлекаем жанры
                    genres = self.extract_genres_from_game_page(game_html, game['url'])
                    
                    # Сохраняем результат
                    game_result = {
                        'page': page_num,
                        'position_on_page': i,
                        'title': game['title'],
                        'url': game['url'],
                        'genres': genres,
                        'found_genres': len(genres) > 0
                    }
                    
                    self.all_games.append(game_result)
                    
                    if genres:
                        page_games_with_genres += 1
                        genres_str = ", ".join(genres)
                        logger.info(f"✅ [{total_games}] {game['title']} -> {genres_str}")
                    else:
                        logger.warning(f"❌ [{total_games}] {game['title']} -> Жанры не найдены")
                
                # Небольшая задержка между играми
                await asyncio.sleep(0.1)
            
            logger.info(f"📊 Страница {page_num} завершена: {len(games)} игр, {page_games_with_genres} с жанрами")
            
            # Задержка между страницами
            await asyncio.sleep(0.3)
        
        logger.info(f"🎉 ОБХОД ЗАВЕРШЕН!")
        logger.info(f"📊 Статистика:")
        logger.info(f"📄 Всего страниц проверено: {page_num - 1}")
        logger.info(f"📄 Страниц с играми: {pages_with_games}")
        logger.info(f"📄 Пустых страниц: {empty_pages}")
        logger.info(f"🎮 Всего игр найдено: {total_games}")
        
        return total_games, pages_with_games
    
    def show_final_statistics(self):
        """Показать финальную статистику"""
        total = len(self.all_games)
        with_genres = sum(1 for g in self.all_games if g['found_genres'])
        without_genres = total - with_genres
        
        # Уникальные игры
        unique_titles = set(game['title'] for game in self.all_games)
        
        # Жанры
        all_genres = set()
        for game in self.all_games:
            if game['found_genres']:
                all_genres.update(game['genres'])
        
        logger.info("=" * 80)
        logger.info("🎯 ФИНАЛЬНАЯ СТАТИСТИКА:")
        logger.info(f"🎮 Всего игр обработано: {total}")
        logger.info(f"🎯 Уникальных игр: {len(unique_titles)}")
        logger.info(f"✅ Игр с жанрами: {with_genres}")
        logger.info(f"❌ Игр без жанров: {without_genres}")
        logger.info(f"📈 Процент с жанрами: {(with_genres/total*100):.1f}%")
        logger.info(f"🏷️ Всего уникальных жанров: {len(all_genres)}")
        
        logger.info("🏷️ Найденные жанры:")
        for genre in sorted(all_genres):
            count = sum(1 for g in self.all_games if g['found_genres'] and genre in g['genres'])
            logger.info(f"   📊 {genre}: {count} игр")
    
    def save_results(self, filename: str = "all_switch_games_complete.json"):
        """Сохранить все результаты"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.all_games, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 Все результаты сохранены в {filename}")

async def main():
    logger.info("🚀 НАЧИНАЮ ПОЛНЫЙ ОБХОД ВСЕХ СТРАНИЦ NINTENDO SWITCH!")
    
    async with AllPagesExtractor() as extractor:
        # Обрабатываем все страницы
        total_games, pages_with_games = await extractor.process_all_pages(max_pages=500)
        
        # Показываем статистику
        extractor.show_final_statistics()
        
        # Сохраняем результаты
        extractor.save_results()
        
        logger.info("🎉 РАБОТА ПОЛНОСТЬЮ ЗАВЕРШЕНА!")

if __name__ == "__main__":
    asyncio.run(main())
