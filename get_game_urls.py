#!/usr/bin/env python3
"""
Скрипт для получения реальных URL всех игр с asst2game.ru
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def get_all_game_urls():
    """Получить URL всех игр с сайта"""
    base_url = "https://asst2game.ru"
    all_urls = []
    
    async with aiohttp.ClientSession() as session:
        page = 1
        while True:
            url = f"{base_url}/page/{page}/" if page > 1 else base_url
            
            try:
                logger.info(f"Загружаю страницу {page}: {url}")
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Ошибка загрузки страницы {page}: {response.status}")
                        break
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Ищем все ссылки на игры
                    game_links = soup.find_all('a', href=True)
                    page_urls = []
                    
                    for link in game_links:
                        href = link.get('href')
                        if href and href.endswith('.html') and '/switch.html' in href:
                            full_url = base_url + href if not href.startswith('http') else href
                            if full_url not in all_urls:
                                page_urls.append(full_url)
                    
                    if not page_urls:
                        logger.info(f"Больше игр не найдено на странице {page}")
                        break
                    
                    all_urls.extend(page_urls)
                    logger.info(f"Найдено {len(page_urls)} игр на странице {page}")
                    page += 1
                    
                    # Ограничимся для теста
                    if page > 20:  # Максимум 20 страниц
                        break
                        
            except Exception as e:
                logger.error(f"Ошибка при загрузке страницы {page}: {e}")
                break
    
    logger.info(f"Всего найдено игр: {len(all_urls)}")
    return all_urls

async def main():
    urls = await get_all_game_urls()
    
    # Сохраняем в файл
    with open('game_urls.json', 'w', encoding='utf-8') as f:
        json.dump(urls, f, indent=2)
    
    logger.info(f"URL игр сохранены в game_urls.json")
    
    # Показываем первые 10 для проверки
    logger.info("Первые 10 URL:")
    for i, url in enumerate(urls[:10], 1):
        logger.info(f"{i}. {url}")

if __name__ == "__main__":
    asyncio.run(main())
