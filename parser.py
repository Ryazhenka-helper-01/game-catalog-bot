import asyncio
import aiohttp
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class GameParser:
    def __init__(self):
        self.base_url = "https://asst2game.ru/consoles/nintendo-switch/"
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_page(self, url: str) -> Optional[str]:
        """Получить HTML страницы"""
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.error(f"Failed to fetch {url}: Status {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def clean_text(self, text: str) -> str:
        """Очистка текста от лишних пробелов и символов"""
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text.strip())
    
    def extract_rating(self, text: str) -> str:
        """Извлечь рейтинг из текста"""
        if not text:
            return "N/A"
        
        # Ищем рейтинг в разных форматах
        rating_patterns = [
            r'(\d+(?:\.\d+)?)\s*\/\s*10',
            r'(\d+(?:\.\d+)?)\s*из\s*10',
            r'Рейтинг:\s*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*балл',
        ]
        
        for pattern in rating_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return "N/A"
    
    def extract_genres(self, text: str) -> List[str]:
        """Извлечь жанры из текста"""
        if not text:
            return []
        
        # Список распространенных жанров игр
        genre_keywords = [
            'Action', 'Adventure', 'RPG', 'Role-Playing', 'Strategy', 'Puzzle',
            'Simulation', 'Sports', 'Racing', 'Fighting', 'Platformer',
            'Shooter', 'Stealth', 'Survival', 'Horror', 'Music', 'Party',
            'Educational', 'Family', 'Casual', 'Indie', 'Multiplayer',
            'Single-player', 'Co-op', 'Online', 'Arcade', 'Board Game',
            'Card Game', 'Turn-based', 'Real-time', 'Open World',
            'Metroidvania', 'Roguelike', 'Visual Novel', 'Dating Sim'
        ]
        
        genres = []
        text_lower = text.lower()
        
        for genre in genre_keywords:
            if genre.lower() in text_lower:
                genres.append(genre)
        
        # Дополнительная обработка для извлечения жанров из разделенных запятой списков
        if ',' in text:
            parts = text.split(',')
            for part in parts:
                part_clean = self.clean_text(part)
                for genre in genre_keywords:
                    if genre.lower() in part_clean.lower():
                        if genre not in genres:
                            genres.append(genre)
        
        return genres
    
    async def parse_game_list(self) -> List[Dict]:
        """Парсинг списка игр с главной страницы"""
        html = await self.get_page(self.base_url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        games = []
        
        # Ищем элементы с играми - разные возможные селекторы
        selectors = [
            'article.game',
            'div.game-item', 
            'div.item-game',
            'li.game',
            'div.post',
            'article.post',
            'div.catalog-item',
            'li.catalog-item',
            'div.product',
            'article.product',
            'a[href*="/game/"]',
            'a[href*="nintendo-switch"]'
        ]
        
        game_elements = []
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                game_elements = elements
                print(f"Found {len(elements)} elements with selector: {selector}")
                break
        
        # Если ничего не нашли, ищем по ссылкам
        if not game_elements:
            links = soup.find_all('a', href=True)
            game_elements = [link for link in links if 'nintendo-switch' in link.get('href', '') or 'game' in link.get('href', '')]
            print(f"Found {len(game_elements)} links containing nintendo-switch or game")
        
        for element in game_elements:
            try:
                game = await self.parse_game_element(element)
                if game and game.get('title'):
                    games.append(game)
                    print(f"Parsed game: {game.get('title', 'Unknown')}")
            except Exception as e:
                logger.error(f"Error parsing game element: {e}")
                continue
        
        print(f"Total games parsed: {len(games)}")
        return games
    
    async def parse_game_element(self, element, page_num: int = 1) -> Optional[Dict]:
        """Парсинг отдельного элемента игры"""
        game = {}
        
        # Заголовок/название игры
        title_elem = element.find(['h1', 'h2', 'h3', 'h4', 'span', 'a'], class_=re.compile(r'title|name|game', re.I))
        if not title_elem:
            title_elem = element.find('a')
        
        if title_elem:
            game['title'] = self.clean_text(title_elem.get_text())
        else:
            game['title'] = self.clean_text(element.get_text())[:50]  # Первые 50 символов как название
        
        # Ссылка на игру
        link_elem = element.find('a', href=True)
        if link_elem:
            href = link_elem.get('href', '')
            if href.startswith('http'):
                game['url'] = href
            else:
                game['url'] = urljoin(self.base_url, href)
        else:
            game['url'] = self.base_url
        
        # Изображение
        img_elem = element.find('img')
        if img_elem:
            game['image_url'] = img_elem.get('src') or img_elem.get('data-src')
            if game['image_url'] and not game['image_url'].startswith('http'):
                game['image_url'] = urljoin(self.base_url, game['image_url'])
        else:
            game['image_url'] = ""
        
        # Описание
        desc_elem = element.find(['p', 'div', 'span'], class_=re.compile(r'desc|description|summary', re.I))
        if desc_elem:
            game['description'] = self.clean_text(desc_elem.get_text())[:500]  # Первые 500 символов
        else:
            game['description'] = ""
        
        # Рейтинг
        rating_elem = element.find(['span', 'div', 'strong'], class_=re.compile(r'rating|score|rate', re.I))
        if rating_elem:
            game['rating'] = self.extract_rating(rating_elem.get_text())
        else:
            game['rating'] = "N/A"
        
        # Жанры
        genre_elem = element.find(['span', 'div', 'p'], class_=re.compile(r'genre|category|tag', re.I))
        if genre_elem:
            game['genres'] = self.extract_genres(genre_elem.get_text())
        else:
            game['genres'] = []
        
        # Дата добавления
        date_elem = element.find(['time', 'span', 'div'], class_=re.compile(r'date|time|published', re.I))
        if date_elem:
            game['release_date'] = self.clean_text(date_elem.get_text())
        else:
            game['release_date'] = datetime.now().strftime('%Y-%m-%d')
        
        # Добавляем номер страницы для отладки
        game['page_num'] = page_num
        
        return game if game.get('title') else None
    
    async def parse_game_details(self, game_url: str) -> Optional[Dict]:
        """Парсинг детальной страницы игры"""
        html = await self.get_page(game_url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        game = {'url': game_url}
        
        # Название игры
        title_elem = soup.find(['h1', 'h2'], class_=re.compile(r'title|name|game', re.I))
        if not title_elem:
            title_elem = soup.find('h1')
        if title_elem:
            game['title'] = self.clean_text(title_elem.get_text())
        
        # Описание
        desc_elem = soup.find(['div', 'section', 'p'], class_=re.compile(r'description|summary|about', re.I))
        if desc_elem:
            game['description'] = self.clean_text(desc_elem.get_text())
        
        # Рейтинг
        rating_elem = soup.find(['span', 'div', 'strong'], class_=re.compile(r'rating|score|rate', re.I))
        if rating_elem:
            game['rating'] = self.extract_rating(rating_elem.get_text())
        
        # Жанры
        genre_elem = soup.find(['div', 'span', 'p'], class_=re.compile(r'genre|category|tag', re.I))
        if genre_elem:
            game['genres'] = self.extract_genres(genre_elem.get_text())
        
        # Изображение
        img_elem = soup.find('img', class_=re.compile(r'poster|cover|main', re.I))
        if not img_elem:
            img_elem = soup.find('img')
        if img_elem:
            game['image_url'] = img_elem.get('src') or img_elem.get('data-src')
            if game['image_url'] and not game['image_url'].startswith('http'):
                game['image_url'] = urljoin(game_url, game['image_url'])
        
        # Скриншоты
        screenshots = []
        screenshot_elements = soup.find_all('img', class_=re.compile(r'screenshot|screen|gallery', re.I))
        for img in screenshot_elements:
            src = img.get('src') or img.get('data-src')
            if src:
                if not src.startswith('http'):
                    src = urljoin(game_url, src)
                screenshots.append(src)
        
        game['screenshots'] = screenshots[:10]  # Максимум 10 скриншотов
        
        # Дата релиза
        date_elem = soup.find(['time', 'span', 'div'], class_=re.compile(r'date|release|published', re.I))
        if date_elem:
            game['release_date'] = self.clean_text(date_elem.get_text())
        
        return game
    
    async def get_all_games(self) -> List[Dict]:
        """Получить все игры с сайта (все страницы)"""
        async with self:
            all_games = []
            page = 1
            max_pages = 50  # Ограничение для безопасности
            
            while page <= max_pages:
                # Формируем URL для пагинации
                if page == 1:
                    page_url = self.base_url
                else:
                    # Попробуем разные варианты пагинации
                    page_urls = [
                        f"{self.base_url}?page={page}",
                        f"{self.base_url}page/{page}/",
                        f"{self.base_url}page-{page}/",
                        f"{self.base_url}p/{page}/",
                        f"https://asst2game.ru/consoles/nintendo-switch/page/{page}/"
                    ]
                    
                    page_url = page_urls[-1]  # Используем последний вариант
                
                print(f"Parsing page {page}: {page_url}")
                
                # Получаем игры с текущей страницы
                games = await self.parse_page_games(page_url, page)
                
                if not games:
                    print(f"No games found on page {page}, stopping pagination")
                    break
                
                all_games.extend(games)
                print(f"Found {len(games)} games on page {page}, total: {len(all_games)}")
                
                # Небольшая задержка между запросами
                await asyncio.sleep(1)
                page += 1
            
            print(f"Total games found across all pages: {len(all_games)}")
            return all_games
    
    async def parse_page_games(self, page_url: str, page_num: int) -> List[Dict]:
        """Парсинг игр с конкретной страницы"""
        html = await self.get_page(page_url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        games = []
        
        # Расширенные селекторы для поиска игр
        selectors = [
            'article.game',
            'div.game-item', 
            'div.item-game',
            'li.game',
            'div.post',
            'article.post',
            'div.catalog-item',
            'li.catalog-item',
            'div.product',
            'article.product',
            'div.item',
            'li.item',
            'div.card',
            'article.card',
            'div.entry',
            'article.entry',
            'a[href*="/game/"]',
            'a[href*="nintendo-switch"]',
            'a[href*="switch"]'
        ]
        
        game_elements = []
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                game_elements = elements
                print(f"Page {page_num}: Found {len(elements)} elements with selector: {selector}")
                break
        
        # Если ничего не нашли, ищем по ссылкам и тексту
        if not game_elements:
            links = soup.find_all('a', href=True)
            game_links = []
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                if ('nintendo-switch' in href or 'game' in href or 'switch' in href) and text:
                    game_links.append(link)
            
            game_elements = game_links
            print(f"Page {page_num}: Found {len(game_links)} links containing game-related terms")
        
        # Если все еще ничего не нашли, ищем по заголовкам
        if not game_elements:
            headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            game_elements = [h for h in headers if h.get_text(strip=True)]
            print(f"Page {page_num}: Found {len(headers)} headers as fallback")
        
        for element in game_elements:
            try:
                game = await self.parse_game_element(element, page_num)
                if game and game.get('title') and len(game.get('title', '')) > 2:
                    # Проверяем, что игра еще не добавлена
                    if not any(g.get('title') == game.get('title') for g in games):
                        games.append(game)
                        print(f"Page {page_num}: Parsed game - {game.get('title', 'Unknown')}")
            except Exception as e:
                logger.error(f"Page {page_num}: Error parsing game element: {e}")
                continue
        
        print(f"Page {page_num}: Total unique games parsed: {len(games)}")
        return games
    
    async def check_for_new_games(self, existing_titles: set) -> List[Dict]:
        """Проверить наличие новых игр"""
        async with self:
            games = await self.parse_game_list()
            new_games = []
            
            for game in games:
                if game.get('title') and game['title'] not in existing_titles:
                    # Получаем детальную информацию для новой игры
                    if game.get('url') and game['url'] != self.base_url:
                        detailed_game = await self.parse_game_details(game['url'])
                        if detailed_game:
                            new_games.append(detailed_game)
                    else:
                        new_games.append(game)
            
            return new_games
