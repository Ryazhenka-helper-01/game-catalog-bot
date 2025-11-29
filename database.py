import sqlite3
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import aiosqlite

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "games.db"):
        self.db_path = db_path
        self._lock = asyncio.Lock()
    
    async def init_db(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL UNIQUE,
                    description TEXT,
                    rating TEXT,
                    genres TEXT,  -- JSON массив жанров
                    image_url TEXT,
                    screenshots TEXT,  -- JSON массив скриншотов
                    release_date TEXT,
                    url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Добавляем missing колонки, если их нет (для обратной совместимости)
            cursor = await db.execute("PRAGMA table_info(games)")
            columns = [row[1] for row in await cursor.fetchall()]
            if 'created_at' not in columns:
                await db.execute("ALTER TABLE games ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            if 'updated_at' not in columns:
                await db.execute("ALTER TABLE games ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (game_id) REFERENCES games (id)
                )
            ''')
            
            await db.commit()
            logger.info("Database initialized")
    
    async def add_game(self, game: Dict) -> bool:
        """Добавить игру в базу данных"""
        async with self._lock:
            try:
                async with aiosqlite.connect(self.db_path) as db:
                    import json
                    
                    await db.execute('''
                        INSERT OR REPLACE INTO games 
                        (title, description, rating, genres, image_url, screenshots, release_date, url, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        game.get('title', ''),
                        game.get('description', ''),
                        game.get('rating', 'N/A'),
                        json.dumps(game.get('genres', [])),
                        game.get('image_url', ''),
                        json.dumps(game.get('screenshots', [])),
                        game.get('release_date', ''),
                        game.get('url', ''),
                        datetime.now().isoformat()
                    ))
                    
                    await db.commit()
                    logger.info(f"Game added: {game.get('title', 'Unknown')}")
                    return True
                    
            except Exception as e:
                logger.error(f"Error adding game: {e}")
                return False
    
    async def get_game_by_id(self, game_id: int) -> Optional[Dict]:
        """Получить игру по ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('SELECT * FROM games WHERE id = ?', (game_id,))
            row = await cursor.fetchone()
            
            if row:
                import json
                game = dict(row)
                game['genres'] = json.loads(game['genres']) if game['genres'] else []
                game['screenshots'] = json.loads(game['screenshots']) if game['screenshots'] else []
                return game
            
            return None
    
    async def get_game_by_title(self, title: str) -> Optional[Dict]:
        """Получить игру по названию"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('SELECT * FROM games WHERE title = ?', (title,))
            row = await cursor.fetchone()
            
            if row:
                import json
                game = dict(row)
                game['genres'] = json.loads(game['genres']) if game['genres'] else []
                game['screenshots'] = json.loads(game['screenshots']) if game['screenshots'] else []
                return game
            
            return None
    
    async def get_all_games(self) -> List[Dict]:
        """Получить все игры"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('SELECT * FROM games ORDER BY title')
            rows = await cursor.fetchall()
            
            games = []
            import json
            for row in rows:
                game = dict(row)
                game['genres'] = json.loads(game['genres']) if game['genres'] else []
                game['screenshots'] = json.loads(game['screenshots']) if game['screenshots'] else []
                games.append(game)
            
            return games
    
    async def update_game(self, game_id: int, game_data: Dict) -> bool:
        """Обновить информацию об игре"""
        async with self._lock:
            try:
                import json
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute('''
                        UPDATE games 
                        SET title = ?, description = ?, rating = ?, genres = ?, 
                            image_url = ?, screenshots = ?, release_date = ?, url = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (
                        game_data.get('title', ''),
                        game_data.get('description', ''),
                        game_data.get('rating', 'N/A'),
                        json.dumps(game_data.get('genres', [])),
                        game_data.get('image_url', ''),
                        json.dumps(game_data.get('screenshots', [])),
                        game_data.get('release_date', ''),
                        game_data.get('url', ''),
                        game_id
                    ))
                    
                    await db.commit()
                    logger.info(f"Game updated: {game_data.get('title', 'Unknown')}")
                    return True
                    
            except Exception as e:
                logger.error(f"Error updating game: {e}")
                return False
    
    async def update_game_genres(self, game_id: int, new_genres: List[str]) -> bool:
        """Обновить только жанры для игры"""
        async with self._lock:
            try:
                async with aiosqlite.connect(self.db_path) as db:
                    import json
                    genres_json = json.dumps(new_genres, ensure_ascii=False)
                    
                    await db.execute(''''
                        UPDATE games 
                        SET genres = ?, updated_at = CURRENT_TIMESTAMP 
                        WHERE id = ?
                    ''', (genres_json, game_id))
                    
                    await db.commit()
                    logger.info(f"Updated genres for game ID {game_id}: {new_genres}")
                    return True
                    
            except Exception as e:
                logger.error(f"Error updating game genres: {e}")
                return False
    
    async def get_games_by_genre(self, genre: str, limit: int = 5, offset: int = 0) -> List[Dict]:
        """Получить игры по жанру"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT * FROM games 
                WHERE genres LIKE ? 
                ORDER BY title 
                LIMIT ? OFFSET ?
            ''', (f'%{genre}%', limit, offset))
            
            rows = await cursor.fetchall()
            games = []
            
            for row in rows:
                import json
                game = dict(row)
                game['genres'] = json.loads(game['genres']) if game['genres'] else []
                game['screenshots'] = json.loads(game['screenshots']) if game['screenshots'] else []
                games.append(game)
            
            return games
    
    async def get_all_genres(self) -> List[str]:
        """Получить все уникальные жанры"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT genres FROM games WHERE genres IS NOT NULL AND genres != "[]"')
            rows = await cursor.fetchall()
            
            all_genres = set()
            import json
            
            for row in rows:
                try:
                    genres = json.loads(row[0])
                    all_genres.update(genres)
                except:
                    continue
            
            return sorted(list(all_genres))
    
    async def get_games_count_by_genre(self, genre: str) -> int:
        """Получить количество игр по жанру"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT COUNT(*) FROM games 
                WHERE genres LIKE ?
            ''', (f'%{genre}%',))
            
            row = await cursor.fetchone()
            return row[0] if row else 0
    
    async def search_games(self, query: str, limit: int = 10) -> List[Dict]:
        """Поиск игр по названию"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT * FROM games 
                WHERE title LIKE ? OR description LIKE ?
                ORDER BY title 
                LIMIT ?
            ''', (f'%{query}%', f'%{query}%', limit))
            
            rows = await cursor.fetchall()
            games = []
            
            for row in rows:
                import json
                game = dict(row)
                game['genres'] = json.loads(game['genres']) if game['genres'] else []
                game['screenshots'] = json.loads(game['screenshots']) if game['screenshots'] else []
                games.append(game)
            
            return games
    
    async def get_recent_games(self, days: int = 7, limit: int = 10) -> List[Dict]:
        """Получить недавно добавленные игры"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT * FROM games 
                WHERE created_at >= datetime('now', '-{} days')
                ORDER BY created_at DESC 
                LIMIT ?
            '''.format(days), (limit,))
            
            rows = await cursor.fetchall()
            games = []
            
            for row in rows:
                import json
                game = dict(row)
                game['genres'] = json.loads(game['genres']) if game['genres'] else []
                game['screenshots'] = json.loads(game['screenshots']) if game['screenshots'] else []
                games.append(game)
            
            return games
    
    async def update_game(self, game_id: int, game_data: Dict) -> bool:
        """Обновить информацию об игре"""
        async with self._lock:
            try:
                async with aiosqlite.connect(self.db_path) as db:
                    import json
                    
                    set_clauses = []
                    values = []
                    
                    if 'description' in game_data:
                        set_clauses.append('description = ?')
                        values.append(game_data['description'])
                    
                    if 'rating' in game_data:
                        set_clauses.append('rating = ?')
                        values.append(game_data['rating'])
                    
                    if 'genres' in game_data:
                        set_clauses.append('genres = ?')
                        values.append(json.dumps(game_data['genres']))
                    
                    if 'image_url' in game_data:
                        set_clauses.append('image_url = ?')
                        values.append(game_data['image_url'])
                    
                    if 'screenshots' in game_data:
                        set_clauses.append('screenshots = ?')
                        values.append(json.dumps(game_data['screenshots']))
                    
                    if 'release_date' in game_data:
                        set_clauses.append('release_date = ?')
                        values.append(game_data['release_date'])
                    
                    if 'url' in game_data:
                        set_clauses.append('url = ?')
                        values.append(game_data['url'])
                    
                    # updated_at обновляется автоматически через DEFAULT CURRENT_TIMESTAMP,
                    # но если колонка уже есть и мы хотим явно обновить время:
                    set_clauses.append('updated_at = CURRENT_TIMESTAMP')
                    values.append(game_id)
                    
                    if set_clauses:
                        await db.execute(f'''
                            UPDATE games 
                            SET {', '.join(set_clauses)}
                            WHERE id = ?
                        ''', values)
                        
                        await db.commit()
                        logger.info(f"Game updated: {game_id}")
                        return True
                    
                    return False
                    
            except Exception as e:
                logger.error(f"Error updating game: {e}")
                return False
    
    async def delete_game(self, game_id: int) -> bool:
        """Удалить игру"""
        async with self._lock:
            try:
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute('DELETE FROM games WHERE id = ?', (game_id,))
                    await db.commit()
                    logger.info(f"Game deleted: {game_id}")
                    return True
                    
            except Exception as e:
                logger.error(f"Error deleting game: {e}")
                return False
    
    async def get_statistics(self) -> Dict:
        """Получить статистику базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            # Общее количество игр
            cursor = await db.execute('SELECT COUNT(*) FROM games')
            total_games = (await cursor.fetchone())[0]
            
            # Игры с рейтингами
            cursor = await db.execute('SELECT COUNT(*) FROM games WHERE rating != "N/A" AND rating IS NOT NULL')
            rated_games = (await cursor.fetchone())[0]
            
            # Игры с изображениями
            cursor = await db.execute('SELECT COUNT(*) FROM games WHERE image_url IS NOT NULL AND image_url != ""')
            games_with_images = (await cursor.fetchone())[0]
            
            # Игры со скриншотами
            cursor = await db.execute('SELECT COUNT(*) FROM games WHERE screenshots IS NOT NULL AND screenshots != "[]"')
            games_with_screenshots = (await cursor.fetchone())[0]
            
            return {
                'total_games': total_games,
                'rated_games': rated_games,
                'games_with_images': games_with_images,
                'games_with_screenshots': games_with_screenshots
            }
    
    async def add_notification(self, game_id: int) -> bool:
        """Добавить запись об отправленном уведомлении"""
        async with self._lock:
            try:
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute('''
                        INSERT INTO notifications (game_id)
                        VALUES (?)
                    ''', (game_id,))
                    
                    await db.commit()
                    return True
                    
            except Exception as e:
                logger.error(f"Error adding notification: {e}")
                return False
    
    async def was_notification_sent(self, game_id: int) -> bool:
        """Проверить, было ли отправлено уведомление об игре"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT COUNT(*) FROM notifications WHERE game_id = ?', (game_id,))
            row = await cursor.fetchone()
            return row[0] > 0 if row else False
