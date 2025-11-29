#!/usr/bin/env python3
"""
Извлечение недостающих описаний для 7 игр
"""

import json
import asyncio
import aiohttp
import logging
from bs4 import BeautifulSoup
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MissingDescriptionsExtractor:
    def __init__(self):
        self.base_url = "https://asst2game.ru"
        self.session = None
        self.processed_count = 0
        self.found_count = 0
    
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
    
    async def extract_description_from_page(self, url, title):
        """Извлечение описания со страницы игры"""
        try:
            logger.info(f"Extracting description for: {title}")
            
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
                        logger.info(f"✓ Found meta description ({len(description)} chars)")
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
                            logger.info(f"✓ Found description with selector {selector}")
                            return text
                
                # 3. Запасной вариант - первый абзац
                paragraphs = soup.find_all('p')
                for p in paragraphs:
                    text = self.clean_text(p.get_text())
                    if len(text) > 50 and 'Nintendo Switch' not in text:
                        logger.info(f"✓ Found paragraph description")
                        return text
                
                logger.warning(f"✗ No description found for {title}")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting description from {url}: {e}")
            return None
    
    async def process_missing_games(self):
        """Обработка игр без описаний"""
        
        # Игры без описаний
        missing_games = [
            {
                'title': 'Ni no Kuni II: Revenant Kingdom The Prince\'s Edition',
                'url': 'https://asst2game.ru/1101-ni-no-kuni-ii-revenant-kingdom-switch.html'
            },
            {
                'title': 'Onimusha: Warlords',
                'url': 'https://asst2game.ru/1104-onimusha-warlords-switch.html'
            },
            {
                'title': 'Sniper Elite III: Ultimate Edition',
                'url': 'https://asst2game.ru/895-sniper-elite-3-switch.html'
            },
            {
                'title': 'Teenage Mutant Ninja Turtles: Mutants Unleashed',
                'url': 'https://asst2game.ru/966-tmnt-mutants-unleashed-switch.html'
            },
            {
                'title': 'The Legend of Zelda: Link\'s Awakening',
                'url': 'https://asst2game.ru/316-1-the-legend-of-zelda-links-awakening-switch.html'
            },
            {
                'title': 'Tormented Souls',
                'url': 'https://asst2game.ru/1106-tormented-souls-switch.html'
            },
            {
                'title': 'Until Then',
                'url': 'https://asst2game.ru/1234-until-then-switch.html'
            }
        ]
        
        logger.info(f"Processing {len(missing_games)} games without descriptions")
        
        results = []
        
        for game in missing_games:
            self.processed_count += 1
            
            try:
                description = await self.extract_description_from_page(game['url'], game['title'])
                
                result = {
                    'title': game['title'],
                    'url': game['url'],
                    'description': description or '',
                    'found_description': bool(description)
                }
                
                results.append(result)
                
                if description:
                    self.found_count += 1
                    logger.info(f"✓ SUCCESS: {game['title']}")
                else:
                    logger.warning(f"✗ FAILED: {game['title']}")
                
                # Небольшая задержка
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing {game['title']}: {e}")
                results.append({
                    'title': game['title'],
                    'url': game['url'],
                    'description': '',
                    'found_description': False
                })
        
        # Сохраняем результаты
        output_file = 'missing_descriptions_results.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info("=" * 80)
        logger.info("MISSING DESCRIPTIONS EXTRACTION COMPLETED!")
        logger.info(f"Total games processed: {self.processed_count}")
        logger.info(f"Descriptions found: {self.found_count}")
        logger.info(f"Success rate: {(self.found_count/self.processed_count*100):.1f}%")
        logger.info(f"Results saved to: {output_file}")
        logger.info("=" * 80)
        
        return results

async def main():
    start_time = time.time()
    
    async with MissingDescriptionsExtractor() as extractor:
        await extractor.process_missing_games()
    
    end_time = time.time()
    duration = end_time - start_time
    
    logger.info(f"Total execution time: {duration:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())
