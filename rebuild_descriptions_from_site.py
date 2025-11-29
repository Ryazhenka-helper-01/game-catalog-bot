import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import Optional

from database import Database
from parser import GameParser
from utils import clean_text


async def fetch_full_description(parser: GameParser, url: str) -> Optional[str]:
    """Зайти на страницу игры и вытащить полное описание по нескольким селекторам."""
    if not url:
        return None

    html = await parser.get_page(url, use_cache=False)
    if not html:
        return None

    soup = BeautifulSoup(html, 'html.parser')

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

    # Ничего не нашлось
    return None


async def rebuild_descriptions():
    db = Database()
    parser = GameParser()

    games = await db.get_all_games()
    if not games:
        print("Игры в базе не найдены")
        return

    print(f"Найдено игр в базе: {len(games)}")

    # Файл, куда сложим все новые описания, чтобы ты мог их посмотреть
    dump_path = 'new_descriptions_dump.txt'
    missing_path = 'missing_descriptions.txt'

    with open(dump_path, 'w', encoding='utf-8') as dump_file:
        dump_file.write("НОВЫЕ ОПИСАНИЯ ИГР (скопированы с сайта по нескольким селекторам)\n\n")

    missing_entries = []

    async with parser:
        for idx, game in enumerate(games, start=1):
            title = game.get('title', 'Без названия')
            url = game.get('url', '')
            game_id = game.get('id')

            print(f"[{idx}/{len(games)}] Обрабатываю: {title}")

            try:
                full_desc = await fetch_full_description(parser, url)
                if not full_desc:
                    print(f"  ⚠ Не удалось получить описание для {title} ({url})")
                    missing_entries.append(f"ID: {game_id}\nНазвание: {title}\nURL: {url}\n\n")
                    continue

                # 1. Удаляем старое описание (по сути, перезаписываем его новым)
                await db.update_game(game_id, {'description': full_desc})

                # 2. Записываем в дамп-файл, чтобы ты мог увидеть, что именно скопировано
                with open(dump_path, 'a', encoding='utf-8') as dump_file:
                    dump_file.write("=" * 80 + "\n")
                    dump_file.write(f"ID: {game_id}\n")
                    dump_file.write(f"Название: {title}\n")
                    dump_file.write(f"URL: {url}\n")
                    dump_file.write("Описание:\n")
                    dump_file.write(full_desc + "\n\n")

            except Exception as e:
                print(f"  ❌ Ошибка при обработке {title}: {e}")
                missing_entries.append(f"ID: {game_id}\nНазвание: {title}\nURL: {url}\nОшибка: {e}\n\n")
                continue

    # Сохраняем список неудачников
    with open(missing_path, 'w', encoding='utf-8') as missing_file:
        missing_file.write("ИГРЫ, ГДЕ НЕ УДАЛОСЬ ПОЛУЧИТЬ ОПИСАНИЕ\n\n")
        for entry in missing_entries:
            missing_file.write(entry + "-" * 40 + "\n")

    print("Готово. Новые описания записаны в базу и сохранены в файле new_descriptions_dump.txt")
    print(f"Игры, где не удалось получить описание, сохранены в {missing_path}")


if __name__ == '__main__':
    asyncio.run(rebuild_descriptions())
