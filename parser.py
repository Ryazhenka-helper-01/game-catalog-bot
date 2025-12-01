import asyncio
import aiohttp
import logging
import traceback
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from utils import (
    setup_logger, safe_execute, clean_text, is_valid_url, normalize_url,
    safe_download_image, validate_game_data, extract_rating, extract_genres,
    request_cache
)

logger = setup_logger(__name__)

class GameParser:
    def __init__(self):
        self.base_url = "https://asst2game.ru"
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
    
    async def get_page(self, url: str, use_cache: bool = True) -> Optional[str]:
        """Получить HTML страницы с кэшированием и улучшенной обработкой ошибок"""
        if not is_valid_url(url):
            logger.error(f"Invalid URL: {url}")
            return None
        
        # Проверяем кэш
        if use_cache and request_cache:
            cached_content = request_cache.get(url)
            if cached_content:
                logger.debug(f"Using cached content for {url}")
                return cached_content
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            async with self.session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    content = await response.text()
                    # Сохраняем в кэш
                    if use_cache and request_cache:
                        request_cache.set(url, content)
                    return content
                else:
                    logger.error(f"HTTP {response.status} for {url}")
                    return ""
                    
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching {url}")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"Client error fetching {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error args: {e.args}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
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
        logger.info("Starting game list parsing...")
        print("Starting game list parsing...")
        
        html = await self.get_page(self.base_url)
        if not html:
            logger.error("Failed to get page HTML")
            print("Failed to get page HTML")
            return []
        
        logger.info("Page HTML received, parsing...")
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
                logger.info(f"Found {len(elements)} elements with selector: {selector}")
                print(f"Found {len(elements)} elements with selector: {selector}")
                break
        
        # Если ничего не нашли, ищем по ссылкам
        if not game_elements:
            links = soup.find_all('a', href=True)
            game_elements = [link for link in links if 'nintendo-switch' in link.get('href', '') or 'game' in link.get('href', '')]
            logger.info(f"Found {len(game_elements)} links containing nintendo-switch or game")
            print(f"Found {len(game_elements)} links containing nintendo-switch or game")
        
        logger.info(f"Processing {len(game_elements)} game elements...")
        print(f"Processing {len(game_elements)} game elements...")
        
        for i, element in enumerate(game_elements):
            try:
                game = await self.parse_game_element(element)
                if game and game.get('title'):
                    games.append(game)
                    logger.info(f"[{i+1}/{len(game_elements)}] Parsed game: {game.get('title', 'Unknown')}")
                    print(f"[{i+1}/{len(game_elements)}] Parsed game: {game.get('title', 'Unknown')}")
            except Exception as e:
                logger.error(f"Error parsing game element {i+1}: {e}")
                print(f"Error parsing game element {i+1}: {e}")
                continue
        
        logger.info(f"Total games parsed: {len(games)}")
        print(f"Total games parsed: {len(games)}")
        return games
    
    async def parse_game_element(self, element, page_num: int = 1) -> Optional[Dict]:
        """Парсинг отдельного элемента игры"""
        game = {}
        
        # Расширенный поиск названия игры
        title = ""
        
        # 1. Пробуем разные селекторы для заголовков
        title_selectors = [
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            '.title', '.name', '.game-title', '.post-title',
            '.entry-title', '.item-title', '.product-title'
        ]
        
        for selector in title_selectors:
            title_elem = element.select_one(selector)
            if title_elem:
                title = self.clean_text(title_elem.get_text())
                if title:
                    break
        
        # 2. Если не нашли, пробуем сам элемент
        if not title:
            title = self.clean_text(element.get_text())
        
        # 3. Если это ссылка, берем текст ссылки
        if not title and element.name == 'a':
            title = self.clean_text(element.get_text())
        
        # 4. Если все еще нет названия, пробуем атрибуты
        if not title:
            title = element.get('title') or element.get('alt') or ""
        
        # Очищаем название от лишнего текста
        if title:
            # Убираем общие слова и фразы
            exclude_phrases = [
                'Nintendo Switch', 'Switch', 'nintendo switch',
                'Купить', 'Цена', 'Заказать', 'Скачать',
                'Обзор', 'Рецензия', 'Прохождение',
                'Читать далее', 'Подробнее', 'Перейти'
            ]
            
            for phrase in exclude_phrases:
                title = title.replace(phrase, '').strip()
            
            # Ограничиваем длину
            if len(title) > 100:
                title = title[:100].strip()
        
        game['title'] = title
        
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
        desc_elem = element.find(['p', 'div', 'span'], class_=re.compile(r'desc|description|summary|excerpt', re.I))
        if desc_elem:
            game['description'] = self.clean_text(desc_elem.get_text())[:500]
        else:
            # Берем первые 300 символов из текста элемента как описание
            full_text = self.clean_text(element.get_text())
            if len(full_text) > len(title) + 50:
                game['description'] = full_text[len(title):len(title)+300].strip()
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
            # Пытаемся извлечь жанры из текста
            full_text = self.clean_text(element.get_text())
            game['genres'] = self.extract_genres(full_text)
        
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
        """Парсинг детальной страницы игры с улучшенной обработкой"""
        if not is_valid_url(game_url):
            logger.error(f"Invalid game URL: {game_url}")
            return None
        
        html = await self.get_page(game_url, use_cache=True)
        if not html:
            logger.warning(f"No content fetched for {game_url}")
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        game = {'url': game_url}
        
        try:
            # Название игры с несколькими попытками
            title = safe_execute(self._extract_title, soup, default="")
            if not title:
                logger.warning(f"No title found for {game_url}")
                return None
            game['title'] = title
            
            # Описание с улучшенным поиском
            description = safe_execute(self._extract_description, soup, default="")
            game['description'] = description
            
            # Рейтинг
            rating = safe_execute(self._extract_rating, soup, default="N/A")
            game['rating'] = rating
            
            # Жанры
            genres = safe_execute(self._extract_genres_from_page, soup, game_url, default=[])
            game['genres'] = genres
            
            # Изображение
            image_url = safe_execute(self._extract_image, soup, game_url, default="")
            game['image_url'] = image_url
            
            # Скриншоты
            screenshots = safe_execute(self._extract_screenshots, soup, game_url, default=[])
            game['screenshots'] = screenshots
            
            # Дата релиза
            release_date = safe_execute(self._extract_release_date, soup, default="")
            game['release_date'] = release_date
            
            # Валидация данных
            validated_game = validate_game_data(game)
            
            if not validated_game.get('title'):
                logger.warning(f"Invalid game data after validation for {game_url}")
                return None
            
            logger.info(f"Successfully parsed {validated_game['title']}: {len(genres)} genres, {len(screenshots)} screenshots")
            return validated_game
            
        except Exception as e:
            logger.error(f"Error parsing game details for {game_url}: {e}")
            logger.debug(traceback.format_exc())
            return None
    
    def _extract_title(self, soup) -> str:
        """Извлечение названия игры"""
        selectors = [
            'h1', 'h2.title', '.game-title', '.entry-title',
            'h2', '.post-title', '.product-title', 'title'
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                title = clean_text(elem.get_text())
                if title and len(title) > 3:
                    return title[:200]
        
        return ""
    
    def _extract_description(self, soup) -> str:
        """Извлечь полное описание, используя несколько селекторов по порядку."""
        # Способ 0: #info > ... > .description-container + заголовок #copypast
        try:
            desc_root = soup.select_one('#info > div > div.full-story > div.description-container')
            if desc_root:
                for level in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    for heading in desc_root.find_all(level):
                        heading_text = clean_text(heading.get_text())
                        if '#copypast' not in heading_text:
                            continue

                        parts = []
                        for sibling in heading.next_siblings:
                            if not getattr(sibling, 'name', None):
                                continue
                            if sibling.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                                break

                            if sibling.name == 'p':
                                txt = clean_text(sibling.get_text())
                                if txt:
                                    parts.append(txt)
                            else:
                                for p in sibling.find_all('p'):
                                    txt = clean_text(p.get_text())
                                    if txt:
                                        parts.append(txt)

                        full_text = "\n\n".join(parts).strip()
                        if len(full_text) > 50:
                            return full_text
        except Exception:
            pass

        # Способ 1: Строгий путь, который ты дал: main/p[1..]
        try:
            main_container = soup.select_one(
                'body > section.wrap.cf > section > div > div > article > '
                'div:nth-of-type(5) > div:nth-of-type(2) > div > div > '
                'div:nth-of-type(1) > div:nth-of-type(2) > main'
            )
            if main_container:
                paragraphs = main_container.find_all('p')
                parts = [clean_text(p.get_text()) for p in paragraphs if clean_text(p.get_text())]
                full_text = "\n\n".join(parts).strip()
                if len(full_text) > 50:
                    return full_text
        except Exception:
            pass

        # Способ 2: Общие селекторы (fallback)
        selectors = [
            '.description', '.game-description', '.summary', '.about',
            '.post-content', '.entry-content', '.content', 'article p',
            '.game-info', '.details', 'div[itemprop="description"]'
        ]
        for selector in selectors:
            try:
                elem = soup.select_one(selector)
                if elem:
                    text = clean_text(elem.get_text())
                    if len(text) > 50:
                        return text
            except Exception:
                continue

        # Способ 3: Первый осмысленный абзац на странице
        try:
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                text = clean_text(p.get_text())
                if len(text) > 50 and 'Nintendo Switch' not in text:
                    return text
        except Exception:
            pass

        # Способ 4: Meta description как крайний запас
        try:
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                desc = clean_text(meta_desc['content'])
                if len(desc) > 20:
                    return desc
        except Exception:
            pass

        return ""
    
    def _extract_rating(self, soup) -> str:
        """Извлечение рейтинга"""
        # Приоритет: указанный селектор для пользовательского рейтинга
        selectors = [
            '#fix_tabs_filess > div.tabs_header.content-background-024 > div.rating-game-info.rating-game-user-mini',
            '.rating', '.score', '.game-rating', '.stars',
            'span.rating', 'div.rating', '.rate', '[itemprop="ratingValue"]'
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                rating = extract_rating(elem.get_text())
                if rating != "N/A":
                    return rating
        
        return "N/A"
    
    def _extract_genres_from_page(self, soup, game_url: str) -> List[str]:
        """Извлечение жанров из мета-тега itemprop="genre" - РАБОЧИЙ МЕТОД"""
        genres = []
        
        # 1. ПРИОРИТЕТ: Ищем мета-тег itemprop="genre" в основном контейнере
        main_container = soup.select_one('body > section.wrap.cf > section > div > div > article')
        
        if main_container:
            logger.info(f"✅ Найден основной контейнер для {game_url}")
            meta_genre = main_container.find('meta', attrs={'itemprop': 'genre'})
            if meta_genre and meta_genre.get('content'):
                content = meta_genre.get('content').strip()
                logger.info(f"✅ НАЙДЕНО В КОНТЕЙНЕРЕ: {content}")
                
                # Разделяем жанры по запятым
                genre_parts = [part.strip() for part in content.split(',') if part.strip()]
                for part in genre_parts:
                    genre = self._clean_genre_name(part)
                    if genre and genre not in genres:
                        genres.append(genre)
                
                if genres:
                    logger.info(f"✅ ИЗВЛЕЧЕНЫ ЖАНРЫ: {genres}")
                    return genres[:10]
            else:
                logger.warning(f"⚠️ Мета-тег не найден в контейнере")
        else:
            logger.warning(f"⚠️ Контейнер не найден для {game_url}")
        
        # 2. Запасной вариант: ищем в любом месте страницы
        meta_genre_any = soup.find('meta', attrs={'itemprop': 'genre'})
        if meta_genre_any and meta_genre_any.get('content'):
            content = meta_genre_any.get('content').strip()
            logger.info(f"✅ НАЙДЕНО В ЛЮБОМ МЕСТЕ: {content}")
            
            genre_parts = [part.strip() for part in content.split(',') if part.strip()]
            for part in genre_parts:
                genre = self._clean_genre_name(part)
                if genre and genre not in genres:
                    genres.append(genre)
            
            if genres:
                logger.info(f"✅ ИЗВЛЕЧЕНЫ ЖАНРЫ: {genres}")
                return genres[:10]
        
        # 3. Если ничего не найдено, ищем другие мета-теги
        logger.info(f"❌ Мета-тег itemprop='genre' не найден для {game_url}, ищем другие...")
        
        other_patterns = [
            ('meta', {'name': 'genre'}),
            ('meta', {'property': 'genre'}),
            ('meta', {'name': 'keywords'}),
        ]
        
        for tag_name, attrs in other_patterns:
            meta_tag = soup.find(tag_name, attrs=attrs)
            if meta_tag and meta_tag.get('content'):
                content = meta_tag.get('content').strip()
                logger.info(f"✅ НАЙДЕНО {attrs}: {content}")
                
                genre_parts = [part.strip() for part in content.split(',') if part.strip()]
                for part in genre_parts:
                    genre = self._clean_genre_name(part)
                    if genre and genre not in genres:
                        genres.append(genre)
                
                if genres:
                    logger.info(f"✅ ИЗВЛЕЧЕНЫ ЖАНРЫ: {genres}")
                    return genres[:10]
        
        # 4. Если ничего не найдено
        logger.warning(f"❌ Жанры не найдены для {game_url}")
        return []
    
    def _extract_genres_from_text(self, text: str) -> List[str]:
        """Извлечение жанров из любого текста с расширенным словарем"""
        if not text:
            return []
        
        text_lower = text.lower()
        found_genres = []
        
        # Расширенный словарь жанров на русском и английском
        genre_dict = {
            # Action
            'action': 'Action', 'экшен': 'Action', 'действие': 'Action', 'боевик': 'Action',
            
            # Adventure
            'adventure': 'Adventure', 'приключение': 'Adventure', 'приключения': 'Adventure',
            
            # RPG
            'rpg': 'RPG', 'role-playing': 'RPG', 'рпг': 'RPG', 'ролевая': 'RPG', 'ролевые': 'RPG',
            
            # Strategy
            'strategy': 'Strategy', 'стратегия': 'Strategy', 'стратегии': 'Strategy',
            
            # Puzzle
            'puzzle': 'Puzzle', 'головоломка': 'Puzzle', 'головоломки': 'Puzzle', 'пазл': 'Puzzle',
            
            # Simulation
            'simulation': 'Simulation', 'симулятор': 'Simulation', 'симуляторы': 'Simulation', 'сим': 'Simulation',
            
            # Sports
            'sports': 'Sports', 'спорт': 'Sports', 'спортивный': 'Sports', 'спортивные': 'Sports',
            
            # Racing
            'racing': 'Racing', 'гонки': 'Racing', 'гоночный': 'Racing', 'гоночные': 'Racing',
            
            # Fighting
            'fighting': 'Fighting', 'драки': 'Fighting', 'бои': 'Fighting', 'файтинг': 'Fighting',
            
            # Shooter
            'shooter': 'Shooter', 'шутер': 'Shooter', 'стрелялка': 'Shooter', 'стрелялки': 'Shooter',
            
            # Horror
            'horror': 'Horror', 'хоррор': 'Horror', 'ужасы': 'Horror', 'страшный': 'Horror',
            
            # Platformer
            'platformer': 'Platformer', 'платформер': 'Platformer', 'платформенная': 'Platformer',
            
            # Visual Novel
            'visual novel': 'Визуальная новелла', 'визуальная новелла': 'Визуальная новелла',
            'visual': 'Визуальная новелла', 'новелла': 'Визуальная новелла',
            
            # Music/Rhythm
            'music': 'Музыка', 'rhythm': 'Ритм', 'музыкальная': 'Музыка', 'ритмическая': 'Ритм',
            
            # Party
            'party': 'Вечеринка', 'вечеринка': 'Вечеринка', 'мультиплеер': 'Мультиплеер',
            
            # Educational
            'educational': 'Образовательная', 'образовательная': 'Образовательная', 'обучение': 'Образовательная',
            
            # Family
            'family': 'Семейная', 'семейная': 'Семейная', 'для семьи': 'Семейная',
            
            # Casual
            'casual': 'Казуальная', 'казуальная': 'Казуальная', 'случайная': 'Казуальная',
            
            # Indie
            'indie': 'Инди', 'независимая': 'Инди',
            
            # Arcade
            'arcade': 'Аркада', 'аркада': 'Аркада', 'аркадная': 'Аркада',
            
            # Board Game
            'board game': 'Настольная', 'настольная': 'Настольная', 'настольные': 'Настольная',
            
            # Card Game
            'card game': 'Карточная', 'карточная': 'Карточная', 'карточные': 'Карточная',
            
            # Turn-based
            'turn-based': 'Пошаговая', 'пошаговая': 'Пошаговая', 'пошаговые': 'Пошаговая',
            
            # Real-time
            'real-time': 'Реального времени', 'реального времени': 'Реального времени',
            
            # Open World
            'open world': 'Открытый мир', 'открытый мир': 'Открытый мир',
            
            # Metroidvania
            'metroidvania': 'Метроидвания', 'метроидвания': 'Метроидвания',
            
            # Roguelike
            'roguelike': 'Рогалик', 'рогалик': 'Рогалик', 'рогалики': 'Рогалик',
            
            # Survival
            'survival': 'Выживание', 'выживание': 'Выживание',
            
            # Stealth
            'stealth': 'Стелс', 'стелс': 'Стелс', 'скрытая': 'Стелс',
            
            # Multiplayer
            'multiplayer': 'Мультиплеер', 'мультиплеер': 'Мультиплеер',
            
            # Single-player
            'single-player': 'Одиночная', 'одиночная': 'Одиночная', 'синглплеер': 'Одиночная',
            
            # Co-op
            'co-op': 'Кооператив', 'кооператив': 'Кооператив', 'кооп': 'Кооператив',
            
            # Online
            'online': 'Онлайн', 'онлайн': 'Онлайн',
            
            # Additional genres
            'mmo': 'MMO', 'mmorpg': 'MMORPG', 'moba': 'MOBA',
            'tower defense': 'Защита башни', 'защита башни': 'Защита башни',
            'hidden object': 'Поиск предметов', 'поиск предметов': 'Поиск предметов',
            'match-3': 'Match-3', 'три в ряд': 'Match-3',
            'time management': 'Управление временем', 'управление временем': 'Управление временем',
            'word': 'Словесная', 'словесная': 'Словесная',
            'quiz': 'Викторина', 'викторина': 'Викторина',
            'trivia': 'Тривия', 'тривия': 'Тривия',
        }
        
        # Ищем совпадения в тексте
        for keyword, genre in genre_dict.items():
            if keyword in text_lower:
                if genre not in found_genres:
                    found_genres.append(genre)
        
        return found_genres
    
    def _clean_genre_name(self, genre: str) -> str:
        """Очищает название жанра от лишних слов"""
        if not genre:
            return ""
        
        genre_lower = genre.lower()
        
        # Убираем лишние слова
        exclude_words = [
            'игра', 'game', 'для', 'for', 'на', 'on', 'switch',
            'nintendo', 'консоль', 'console', 'платформа', 'platform'
        ]
        
        for word in exclude_words:
            genre_lower = genre_lower.replace(word, '').strip()
        
        # Возвращаем с правильной капитализацией
        if genre_lower:
            return genre_lower.title()
        
        return ""
    
    def _extract_genre_from_url(self, url: str) -> str:
        """Извлекает жанр из URL"""
        url_lower = url.lower()
        
        genre_keywords = {
            'action': 'Action',
            'adventure': 'Adventure', 
            'rpg': 'RPG',
            'role': 'RPG',
            'strategy': 'Strategy',
            'puzzle': 'Puzzle',
            'racing': 'Racing',
            'sports': 'Sports',
            'fighting': 'Fighting',
            'shooter': 'Shooter',
            'horror': 'Horror',
            'simulation': 'Simulation',
            'platformer': 'Platformer',
        }
        
        for keyword, genre in genre_keywords.items():
            if keyword in url_lower:
                return genre
        
        return ""
    
    def _extract_image(self, soup, base_url: str) -> str:
        """Извлечение главного изображения"""
        selectors = [
            '.poster img', '.cover img', '.main-image img',
            '.game-image img', 'img.poster', 'img.cover',
            '.product-image img', 'img[alt*="game"]'
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                src = elem.get('src') or elem.get('data-src')
                if src:
                    return normalize_url(base_url, src)
        
        # Запасной вариант - первое изображение
        img = soup.find('img')
        if img:
            src = img.get('src') or img.get('data-src')
            if src:
                return normalize_url(base_url, src)
        
        return ""
    
    def _extract_screenshots(self, soup, base_url: str) -> List[str]:
        """Извлечение скриншотов"""
        screenshots = []
        
        selectors = [
            '.screenshot img', '.gallery img', '.screenshots img',
            '.game-gallery img', '.media img', 'img.screenshot'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for elem in elements:
                src = elem.get('src') or elem.get('data-src')
                if src:
                    full_url = normalize_url(base_url, src)
                    if is_valid_url(full_url) and full_url not in screenshots:
                        screenshots.append(full_url)
        
        # Если скриншотов мало, добавляем обычные изображения
        if len(screenshots) < 3:
            all_images = soup.find_all('img')
            for img in all_images[1:6]:  # Пропускаем первый (обычно логотип)
                src = img.get('src') or img.get('data-src')
                if src and 'logo' not in src.lower() and 'icon' not in src.lower():
                    full_url = normalize_url(base_url, src)
                    if is_valid_url(full_url) and full_url not in screenshots:
                        screenshots.append(full_url)
        
        return screenshots
    
    def _extract_release_date(self, soup) -> str:
        """Извлечение даты релиза"""
        selectors = [
            '.release-date', '.date', '.publish-date',
            'time', '[itemprop="datePublished"]', '.game-date'
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                date_text = clean_text(elem.get_text())
                if date_text and len(date_text) > 4:
                    return date_text[:20]
        
        return datetime.now().strftime('%Y-%m-%d')
    
    async def get_all_games(self) -> List[Dict]:
        """Получить все игры с сайта (все страницы) с детальной информацией"""
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
                
                # Получаем детальную информацию для каждой игры
                detailed_games = []
                for i, game in enumerate(games):
                    try:
                        print(f"Getting details for game {i+1}/{len(games)}: {game.get('title', 'Unknown')}")
                        if game.get('url') and game['url'] != self.base_url:
                            detailed_game = await self.parse_game_details(game['url'])
                            if detailed_game:
                                detailed_games.append(detailed_game)
                            else:
                                detailed_games.append(game)
                        else:
                            detailed_games.append(game)
                        
                        # Небольшая задержка между запросами
                        if i < len(games) - 1:
                            await asyncio.sleep(0.5)
                            
                    except Exception as e:
                        logger.error(f"Error getting details for game {game.get('title', 'Unknown')}: {e}")
                        detailed_games.append(game)
                
                all_games.extend(detailed_games)
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
        
        # Исключаем пагинацию - ищем только контентные элементы
        # Сначала ищем основной контейнер с играми
        content_container = None
        container_selectors = [
            'div.content',
            'div.main-content', 
            'div.post-content',
            'div.catalog',
            'div.games',
            'section.content',
            'main',
            'div#content',
            '.catalog-list',
            '.games-list'
        ]
        
        for selector in container_selectors:
            container = soup.select_one(selector)
            if container:
                content_container = container
                print(f"Page {page_num}: Found content container with selector: {selector}")
                break
        
        # Если контейнер не найден, используем всю страницу
        if not content_container:
            content_container = soup
            print(f"Page {page_num}: Using full page as content container")
        
        # Ищем только внутри контейнера, исключая навигацию и футер
        navigation_selectors = [
            'nav', '.navigation', '.pagination', '.paging', 
            'footer', '.footer', 'header', '.header',
            '.menu', '.sidebar', '.widget'
        ]
        
        # Удаляем навигационные элементы
        for nav_selector in navigation_selectors:
            for nav_elem in content_container.select(nav_selector):
                nav_elem.decompose()
        
        # Расширенные селекторы для поиска игр (только контентные)
        selectors = [
            'article.post:not(:has(.pagination))',
            'div.post:not(:has(.nav))',
            'article.game',
            'div.game-item', 
            'div.item-game',
            'div.catalog-item',
            'div.product',
            'article.product',
            'div.item',
            'div.card',
            'article.card',
            'div.entry',
            'article.entry',
            'div[class*="post"]',
            'article[class*="post"]',
            'h2 a',  # Заголовки с ссылками
            'h3 a',
            'h4 a'
        ]
        
        game_elements = []
        for selector in selectors:
            elements = content_container.select(selector)
            # Фильтруем элементы, чтобы исключить пагинацию
            filtered_elements = []
            for elem in elements:
                text = elem.get_text(strip=True)
                href = elem.get('href', '') if elem.name == 'a' else ''
                
                # Исключаем элементы пагинации
                if any(num in text for num in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '20', '30', '40', '50']) and len(text) < 5:
                    continue
                if 'page' in href.lower() and len(text) < 5:
                    continue
                if text in ['«', '»', '→', '←', '...', 'Next', 'Prev', 'Далее', 'Назад']:
                    continue
                    
                filtered_elements.append(elem)
            
            if filtered_elements:
                game_elements = filtered_elements
                print(f"Page {page_num}: Found {len(filtered_elements)} elements with selector: {selector}")
                break
        
        # Если все еще ничего не нашли, ищем по заголовкам с текстом длиннее 5 символов
        if not game_elements:
            headers = content_container.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            game_elements = [h for h in headers if len(h.get_text(strip=True)) > 5]
            print(f"Page {page_num}: Found {len(game_elements)} headers with text > 5 chars")
        
        for i, element in enumerate(game_elements):
            try:
                print(f"Page {page_num}: Processing element {i+1}/{len(game_elements)}")
                game = await self.parse_game_element(element, page_num)
                
                if game:
                    title = game.get('title', '')
                    print(f"Page {page_num}: Raw title extracted: '{title}' (length: {len(title)})")
                    
                    # Фильтруем короткие названия (вероятно пагинация)
                    if title and title.strip() and len(title.strip()) > 3:
                        # Дополнительная проверка на пагинацию
                        if not any(char.isdigit() and len(title) < 10 for char in title):
                            # Проверяем, что игра еще не добавлена
                            if not any(g.get('title') == title for g in games):
                                games.append(game)
                                print(f"Page {page_num}: Successfully parsed game - {title}")
                            else:
                                print(f"Page {page_num}: Duplicate game skipped - {title}")
                        else:
                            print(f"Page {page_num}: Title looks like pagination, skipping - {title}")
                    else:
                        print(f"Page {page_num}: Empty or too short title, skipping")
                else:
                    print(f"Page {page_num}: parse_game_element returned None")
            except Exception as e:
                logger.error(f"Page {page_num}: Error parsing game element {i}: {e}")
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
