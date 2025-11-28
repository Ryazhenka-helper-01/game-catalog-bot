#!/usr/bin/env python3
"""
Обновление бота: добавление всех 514 игр Nintendo Switch с жанрами
"""

import json
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_bot_with_all_games():
    """Обновить бота всеми 514 играми"""
    
    # Загружаем все игры
    with open('all_switch_games_complete.json', 'r', encoding='utf-8') as f:
        all_games = json.load(f)
    
    logger.info(f"📊 Загружено игр из файла: {len(all_games)}")
    
    # Создаем уникальные игры (title -> лучшая запись с жанрами)
    unique_games = {}
    
    for game in all_games:
        title = game['title']
        
        # Если игры еще нет или у текущей есть жанры
        if title not in unique_games or (game['found_genres'] and not unique_games[title]['found_genres']):
            unique_games[title] = game
    
    logger.info(f"🎯 Уникальных игр: {len(unique_games)}")
    
    # Подключаемся к базе
    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()
    
    # Удаляем старые данные
    cursor.execute("DELETE FROM games")
    conn.commit()
    logger.info("🗑️ Старые данные удалены")
    
    # Добавляем все уникальные игры
    added_count = 0
    with_genres_count = 0
    
    for title, game in unique_games.items():
        try:
            # Подготавливаем данные
            url = game['url']
            genres = json.dumps(game['genres'], ensure_ascii=False) if game['genres'] else '[]'
            
            # Вставляем игру
            cursor.execute('''
                INSERT INTO games (title, url, genres)
                VALUES (?, ?, ?)
            ''', (title, url, genres))
            
            added_count += 1
            if game['found_genres']:
                with_genres_count += 1
            
            # Показываем прогресс
            if added_count % 50 == 0:
                logger.info(f"📊 Добавлено {added_count}/{len(unique_games)} игр...")
                
        except Exception as e:
            logger.error(f"❌ Ошибка добавления {title}: {e}")
            continue
    
    # Сохраняем изменения
    conn.commit()
    conn.close()
    
    logger.info(f"✅ Добавлено игр в базу: {added_count}")
    logger.info(f"🏷️ Игр с жанрами: {with_genres_count}")
    logger.info(f"📈 Процент с жанрами: {(with_genres_count/added_count*100):.1f}%")
    
    return added_count, with_genres_count

def show_final_database_stats():
    """Показать финальную статистику базы данных"""
    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()
    
    # Общая статистика
    cursor.execute("SELECT COUNT(*) FROM games")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM games WHERE genres != '[]' AND genres IS NOT NULL")
    with_genres = cursor.fetchone()[0]
    
    # Получаем все игры для примеров
    cursor.execute("SELECT title, genres FROM games ORDER BY title")
    all_games_db = cursor.fetchall()
    
    # Получаем все уникальные жанры
    all_unique_genres = set()
    for title, genres in all_games_db:
        if genres:
            try:
                genre_list = json.loads(genres)
                all_unique_genres.update(genre_list)
            except:
                continue
    
    conn.close()
    
    logger.info("=" * 80)
    logger.info("🎯 ФИНАЛЬНАЯ СТАТИСТИКА БОТА:")
    logger.info(f"📊 Всего игр в боте: {total}")
    logger.info(f"🏷️ Игр с жанрами: {with_genres}")
    logger.info(f"📈 Процент с жанрами: {(with_genres/total*100):.1f}%")
    logger.info(f"🎯 Уникальных жанров: {len(all_unique_genres)}")
    
    logger.info("")
    logger.info("🏷️ Все жанры в боте:")
    for genre in sorted(all_unique_genres):
        cursor = sqlite3.connect('games.db')
        count = cursor.execute("SELECT COUNT(*) FROM games WHERE genres LIKE ?", (f'%{genre}%',)).fetchone()[0]
        cursor.close()
        logger.info(f"   📊 {genre}: {count} игр")
    
    logger.info("")
    logger.info("📋 Примеры игр в боте (первые 20):")
    for i, (title, genres) in enumerate(all_games_db[:20], 1):
        try:
            genre_list = json.loads(genres) if genres else []
            genres_str = ", ".join(genre_list) if genre_list else "Нет жанров"
            status = "✅" if genre_list else "❌"
            logger.info(f"{status} [{i:2d}] {title}")
            logger.info(f"     🏷️ {genres_str}")
        except:
            logger.info(f"❌ [{i:2d}] {title} -> Ошибка жанров")
        logger.info("")
    
    if len(all_games_db) > 20:
        logger.info(f"... и еще {len(all_games_db)-20} игр")

def update_bot_version():
    """Обновить версию бота"""
    try:
        with open('main.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Обновляем версию
        content = content.replace('📱 **Версия:** beta-1.0.7', '📱 **Версия:** beta-1.0.8')
        content = content.replace('📱 Версия: beta-1.0.7', '📱 Версия: beta-1.0.8')
        
        with open('main.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("📱 Версия бота обновлена до beta-1.0.8")
    except Exception as e:
        logger.error(f"❌ Ошибка обновления версии: {e}")

def main():
    logger.info("🚀 ОБНОВЛЕНИЕ БОТА ВСЕМИ 514 ИГРАМИ NINTENDO SWITCH!")
    
    # Обновляем базу данных
    added, with_genres = update_bot_with_all_games()
    
    # Показываем статистику
    show_final_database_stats()
    
    # Обновляем версию бота
    update_bot_version()
    
    logger.info("🎉 БОТ ПОЛНОСТЬЮ ОБНОВЛЕН!")
    logger.info(f"📊 Теперь в боте {added} игр Nintendo Switch с жанрами!")
    logger.info("🎮 Бот готов к работе!")

if __name__ == "__main__":
    main()
