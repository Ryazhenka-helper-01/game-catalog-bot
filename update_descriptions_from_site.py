#!/usr/bin/env python3
"""
Обновление описаний и жанров игр с сайта
"""

import asyncio
import logging
from database import Database
from parser import GameParser
from bs4 import BeautifulSoup
import re

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def update_all_descriptions():
    """Обновление описаний всех игр в базе данных"""
    
    print("=== UPDATING DESCRIPTIONS FROM SITE ===")
    
    db = Database()
    parser = GameParser()
    
    try:
        # Получаем все игры из базы
        games = await db.get_all_games()
        print(f"Found {len(games)} games in database")
        
        updated_count = 0
        failed_count = 0
        
        async with parser:
            for i, game in enumerate(games):
                try:
                    game_url = game.get('url')
                    game_title = game.get('title', 'Unknown')
                    
                    if not game_url or game_url == parser.base_url:
                        print(f"[{i+1}/{len(games)}] Skipping {game_title} - no URL")
                        failed_count += 1
                        continue
                    
                    print(f"[{i+1}/{len(games)}] Updating: {game_title}")
                    
                    # Загружаем страницу игры
                    html = await parser.get_page(game_url)
                    if not html:
                        print(f"  Failed to load page")
                        failed_count += 1
                        continue
                    
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Извлекаем полное описание
                    full_description = extract_full_description(soup)
                    
                    # Извлекаем жанры
                    genres = extract_genres_from_page(soup)
                    
                    # Извлекаем рейтинг
                    rating = extract_rating_from_page(soup)
                    
                    # Обновляем игру в базе
                    updated_game = {
                        'description': full_description,
                        'genres': genres,
                        'rating': rating
                    }
                    
                    await db.update_game(game['id'], updated_game)
                    
                    print(f"  ✓ Updated: {len(full_description)} chars, {len(genres)} genres")
                    updated_count += 1
                    
                    # Небольшая задержка между запросами
                    if i < len(games) - 1:
                        await asyncio.sleep(0.5)
                    
                    # Показываем прогресс каждые 10 игр
                    if (i + 1) % 10 == 0:
                        print(f"Progress: {i+1}/{len(games)} games processed")
                        print(f"Updated: {updated_count}, Failed: {failed_count}")
                
                except Exception as e:
                    print(f"  Error updating {game.get('title', 'Unknown')}: {e}")
                    failed_count += 1
                    continue
        
        print(f"\n=== UPDATE COMPLETE ===")
        print(f"Total games: {len(games)}")
        print(f"Successfully updated: {updated_count}")
        print(f"Failed: {failed_count}")
        
        return updated_count > 0
        
    except Exception as e:
        print(f"Error in update process: {e}")
        return False
    
    finally:
        if hasattr(parser, 'session') and parser.session:
            await parser.session.close()

def extract_full_description(soup):
    """Извлечение полного описания со всеми параграфами"""
    
    # Способ 1: Ищем контейнер по указанному пути
    selectors = [
        'body > section.wrap.cf > section > div > div > article > div:nth-of-type(5) > div:nth-of-type(2) > div > div > div:nth-of-type(1) > div:nth-of-type(2) > main',
        'article div.description-container main',
        'article div.description main',
        'div.description main',
        'main.description',
        'article main',
        '.post-content main',
        '.entry-content main'
    ]
    
    for selector in selectors:
        try:
            container = soup.select_one(selector)
            if container:
                # Собираем все параграфы
                paragraphs = container.find_all('p')
                if paragraphs:
                    texts = []
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if text and len(text) > 10:  # Пропускаем короткие параграфы
                            texts.append(text)
                    
                    if texts:
                        full_text = "\n\n".join(texts)
                        if len(full_text) > 100:  # Проверяем, что описание достаточно длинное
                            return full_text
        except Exception:
            continue
    
    # Способ 2: Ищем все параграфы в статье
    try:
        article = soup.find('article')
        if article:
            paragraphs = article.find_all('p')
            texts = []
            for p in paragraphs:
                text = p.get_text().strip()
                if text and len(text) > 10:
                    texts.append(text)
            
            if texts:
                full_text = "\n\n".join(texts)
                if len(full_text) > 100:
                    return full_text
    except Exception:
        pass
    
    # Способ 3: Ищем по классам описания
    description_selectors = [
        '.description',
        '.game-description', 
        '.summary',
        '.about',
        '.post-content',
        '.entry-content',
        '.content'
    ]
    
    for selector in description_selectors:
        try:
            elem = soup.select_one(selector)
            if elem:
                paragraphs = elem.find_all('p')
                if paragraphs:
                    texts = []
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if text and len(text) > 10:
                            texts.append(text)
                    
                    if texts:
                        full_text = "\n\n".join(texts)
                        if len(full_text) > 100:
                            return full_text
        except Exception:
            continue
    
    return ""  # Возвращаем пустую строку если ничего не нашли

def extract_genres_from_page(soup):
    """Извлечение жанров со страницы игры"""
    
    genres = []
    
    # Ищем жанры в разных местах
    genre_selectors = [
        '.genres',
        '.game-genres',
        '.category',
        '.game-category',
        '.tags',
        '.game-tags'
    ]
    
    for selector in genre_selectors:
        try:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text().strip()
                # Ищем жанры в тексте
                found_genres = extract_genre_names(text)
                genres.extend(found_genres)
        except Exception:
            continue
    
    # Ищем жанры в мета-тегах
    try:
        meta_genre = soup.find('meta', attrs={'name': 'keywords'})
        if meta_genre:
            content = meta_genre.get('content', '')
            found_genres = extract_genre_names(content)
            genres.extend(found_genres)
    except Exception:
        pass
    
    # Убираем дубликаты
    return list(set(genres))

def extract_genre_names(text):
    """Извлечение названий жанров из текста"""
    
    if not text:
        return []
    
    # Список жанров на русском и английском
    genre_keywords = [
        'Action', 'Adventure', 'RPG', 'Role-Playing', 'Strategy', 'Puzzle',
        'Simulation', 'Sports', 'Racing', 'Fighting', 'Platformer',
        'Shooter', 'Stealth', 'Survival', 'Horror', 'Music', 'Party',
        'Educational', 'Family', 'Casual', 'Indie', 'Multiplayer',
        'Single-player', 'Co-op', 'Online', 'Arcade', 'Board Game',
        'Card Game', 'Turn-based', 'Real-time', 'Open World',
        'Metroidvania', 'Roguelike', 'Visual Novel', 'Dating Sim',
        'Экшен', 'Приключение', 'RPG', 'Стратегия', 'Головоломка',
        'Симулятор', 'Спорт', 'Гонки', 'Бои', 'Платформер',
        'Шутер', 'Стелс', 'Выживание', 'Ужасы', 'Музыка', 'Вечеринка',
        'Образовательная', 'Семейная', 'Казуальная', 'Инди', 'Мультиплеер',
        'Одиночная', 'Кооператив', 'Онлайн', 'Аркада', 'Настольная игра',
        'Карточная игра', 'Пошаговая', 'Реального времени', 'Открытый мир',
        'Метроидвания', 'Рогалик', 'Визуальная новелла', 'Симулятор свиданий'
    ]
    
    found_genres = []
    text_lower = text.lower()
    
    for genre in genre_keywords:
        if genre.lower() in text_lower:
            found_genres.append(genre)
    
    return found_genres

def extract_rating_from_page(soup):
    """Извлечение рейтинга со страницы"""
    
    # Ищем рейтинг по указанному селектору
    rating_selectors = [
        '#fix_tabs_filess > div.tabs_header.content-background-024 > div.rating-game-info.rating-game-user-mini',
        '.rating',
        '.game-rating',
        '.score',
        '.rating-score'
    ]
    
    for selector in rating_selectors:
        try:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text().strip()
                # Извлекаем числовой рейтинг
                import re
                match = re.search(r'(\d+(?:\.\d+)?)', text)
                if match:
                    return match.group(1)
        except Exception:
            continue
    
    return "N/A"

if __name__ == "__main__":
    result = asyncio.run(update_all_descriptions())
    if result:
        print("SUCCESS: Descriptions updated successfully")
    else:
        print("FAILED: Could not update descriptions")
