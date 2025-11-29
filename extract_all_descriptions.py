#!/usr/bin/env python3
"""
Извлечение описаний для всех 510 игр Nintendo Switch
"""

import json
import asyncio
import aiohttp
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DescriptionExtractor:
    def __init__(self):
        self.base_url = "https://asst2game.ru"
        self.session = None
        self.processed_count = 0
        self.found_descriptions = 0
        self.errors = 0
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def clean_text(self, text):
        """Очистка текста"""
        if not text:
            return ""
        
        # Удаляем лишние пробелы и переносы
        text = ' '.join(text.split())
        
        # Удаляем HTML entities
        import html
        text = html.unescape(text)
        
        # Возвращаем полный текст без обрезки по длине
        return text.strip()
    
    async def extract_description_from_page(self, url):
        """Извлечение описания со страницы игры"""
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch {url}: {response.status}")
                    return None
                
                html_content = await response.text()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # 1. Приоритет: meta itemprop="description" content="..."
                meta_desc = soup.find('meta', attrs={'itemprop': 'description'})
                if meta_desc and meta_desc.get('content'):
                    description = self.clean_text(meta_desc.get('content'))
                    if len(description) > 20:
                        logger.info(f"Found meta description for {url}")
                        return description
                
                # 2. Стандартные селекторы
                selectors = [
                    '.description', '.game-description', '.summary', '.about',
                    '.post-content', '.entry-content', '.content', 'article p',
                    '.game-info', '.details', 'div[itemprop="description"]'
                ]
                
                for selector in selectors:
                    elem = soup.select_one(selector)
                    if elem:
                        text = self.clean_text(elem.get_text())
                        if len(text) > 50:
                            logger.info(f"Found description with selector {selector} for {url}")
                            return text
                
                # 3. Запасной вариант - первый абзац
                paragraphs = soup.find_all('p')
                for p in paragraphs:
                    text = self.clean_text(p.get_text())
                    if len(text) > 50 and 'Nintendo Switch' not in text:
                        logger.info(f"Found paragraph description for {url}")
                        return text
                
                logger.warning(f"No description found for {url}")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting description from {url}: {e}")
            self.errors += 1
            return None
    
    async def process_games(self):
        """Обработка всех игр"""
        
        # Загружаем игры с жанрами
        with open('all_switch_games_complete.json', 'r', encoding='utf-8') as f:
            games = json.load(f)
        
        logger.info(f"Loaded {len(games)} games for description extraction")
        
        # Создаем уникальные игры
        unique_games = {}
        for game in games:
            title = game['title']
            if title not in unique_games:
                unique_games[title] = game
        
        logger.info(f"Processing {len(unique_games)} unique games")
        
        # Обрабатываем каждую игру
        for title, game in unique_games.items():
            self.processed_count += 1
            
            try:
                url = game['url']
                logger.info(f"[{self.processed_count}/{len(unique_games)}] Processing: {title}")
                
                # Извлекаем описание
                description = await self.extract_description_from_page(url)
                
                if description:
                    game['description'] = description
                    game['found_description'] = True
                    self.found_descriptions += 1
                    logger.info(f"✓ Found description ({len(description)} chars): {title[:50]}...")
                else:
                    game['description'] = ""
                    game['found_description'] = False
                    logger.warning(f"✗ No description found: {title}")
                
                # Показываем прогресс
                if self.processed_count % 50 == 0:
                    progress = (self.processed_count / len(unique_games)) * 100
                    logger.info(f"Progress: {self.processed_count}/{len(unique_games)} ({progress:.1f}%) - Descriptions: {self.found_descriptions}")
                
                # Небольшая задержка
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error processing {title}: {e}")
                self.errors += 1
                continue
        
        # Сохраняем результаты
        output_file = 'all_switch_games_with_descriptions.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(list(unique_games.values()), f, ensure_ascii=False, indent=2)
        
        logger.info("=" * 80)
        logger.info("DESCRIPTION EXTRACTION COMPLETED!")
        logger.info(f"Total games processed: {self.processed_count}")
        logger.info(f"Descriptions found: {self.found_descriptions}")
        logger.info(f"Coverage: {(self.found_descriptions/self.processed_count*100):.1f}%")
        logger.info(f"Errors: {self.errors}")
        logger.info(f"Results saved to: {output_file}")
        logger.info("=" * 80)

async def main():
    start_time = time.time()
    
    async with DescriptionExtractor() as extractor:
        await extractor.process_games()
    
    end_time = time.time()
    duration = end_time - start_time
    
    logger.info(f"Total execution time: {duration:.2f} seconds ({duration/60:.1f} minutes)")

if __name__ == "__main__":
    asyncio.run(main())
