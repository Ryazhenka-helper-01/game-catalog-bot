import asyncio
import logging
import schedule
import time
from threading import Thread
from telegram import Bot
from typing import List, Dict
from database import Database
from parser import GameParser

logger = logging.getLogger(__name__)

class GameScheduler:
    def __init__(self, db: Database, bot_token: str):
        self.db = db
        self.bot = Bot(token=bot_token)
        self.parser = GameParser()
        self.running = False
        self.scheduler_thread = None
        
        # ID чата для отправки уведомлений (можно будет настроить через команду)
        self.notification_chat_id = None
        
        # Настройка расписания
        self.setup_schedule()
    
    def setup_schedule(self):
        """Настройка расписания проверок"""
        # Проверка новых игр каждые 2 часа
        schedule.every(2).hours.do(self.check_new_games)
        
        # Ежедневное обновление базы данных в 3:00
        schedule.every().day.at("03:00").do(self.update_database)
        
        # Еженедельная статистика в понедельник в 10:00
        schedule.every().monday.at("10:00").do(self.send_weekly_stats)
    
    async def check_new_games(self):
        """Проверка новых игр"""
        try:
            logger.info("Checking for new games...")
            
            # Получаем существующие игры
            existing_games = await self.db.get_all_games(limit=1000)
            existing_titles = {game['title'] for game in existing_games}
            
            # Ищем новые игры
            new_games = await self.parser.check_for_new_games(existing_titles)
            
            if new_games:
                logger.info(f"Found {len(new_games)} new games")
                
                # Добавляем новые игры в базу
                for game in new_games:
                    await self.db.add_game(game)
                    
                    # Отправляем уведомление
                    await self.send_new_game_notification(game)
                
                # Отправляем сводное уведомление
                await self.send_summary_notification(new_games)
            else:
                logger.info("No new games found")
                
        except Exception as e:
            logger.error(f"Error checking new games: {e}")
    
    async def update_database(self):
        """Полное обновление базы данных"""
        try:
            logger.info("Starting database update...")
            
            # Получаем все игры с сайта
            all_games = await self.parser.get_all_games()
            
            if all_games:
                logger.info(f"Found {len(all_games)} games total")
                
                # Обновляем базу данных
                updated_count = 0
                for game in all_games:
                    success = await self.db.add_game(game)
                    if success:
                        updated_count += 1
                
                logger.info(f"Database updated: {updated_count} games processed")
                
                # Отправляем статистику
                stats = await self.db.get_statistics()
                await self.send_update_stats(stats)
            else:
                logger.warning("No games found during update")
                
        except Exception as e:
            logger.error(f"Error updating database: {e}")
    
    async def send_new_game_notification(self, game: Dict):
        """Отправить уведомление о новой игре"""
        if not self.notification_chat_id:
            return
        
        try:
            title = game.get('title', 'Unknown Game')
            description = game.get('description', 'Описание отсутствует')[:200]
            rating = game.get('rating', 'N/A')
            genres = game.get('genres', [])
            image_url = game.get('image_url', '')
            
            message_text = f"🎮 **НОВАЯ ИГРА!**\n\n"
            message_text += f"📱 **{title}**\n\n"
            
            if rating != 'N/A':
                message_text += f"⭐ **Рейтинг:** {rating}/10\n"
            
            if genres:
                message_text += f"🏷️ **Жанры:** {', '.join(genres[:3])}\n"
            
            message_text += f"\n📝 **Описание:**\n{description}...\n\n"
            message_text += "🔗 [Подробнее]({})".format(game.get('url', ''))
            
            # Добавляем игру в базу уведомлений
            game_record = await self.db.get_game_by_title(title)
            if game_record:
                await self.db.add_notification(game_record['id'])
            
            # Отправляем сообщение
            if image_url:
                await self.bot.send_photo(
                    chat_id=self.notification_chat_id,
                    photo=image_url,
                    caption=message_text,
                    parse_mode='Markdown'
                )
            else:
                await self.bot.send_message(
                    chat_id=self.notification_chat_id,
                    text=message_text,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error sending new game notification: {e}")
    
    async def send_summary_notification(self, new_games: List[Dict]):
        """Отправить сводное уведомление о новых играх"""
        if not self.notification_chat_id or len(new_games) <= 1:
            return
        
        try:
            message_text = f"🎉 **Найдено {len(new_games)} новых игр!**\n\n"
            
            for i, game in enumerate(new_games[:5], 1):  # Максимум 5 игр в сообщении
                title = game.get('title', 'Unknown')
                rating = game.get('rating', 'N/A')
                genres = game.get('genres', [])
                
                message_text += f"{i}. **{title}**"
                if rating != 'N/A':
                    message_text += f" ⭐{rating}"
                if genres:
                    message_text += f" 🏷️{genres[0]}"
                message_text += "\n"
            
            if len(new_games) > 5:
                message_text += f"\n...и еще {len(new_games) - 5} игр"
            
            message_text += "\n\n💡 Используйте /search [жанр] для поиска игр"
            
            await self.bot.send_message(
                chat_id=self.notification_chat_id,
                text=message_text,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error sending summary notification: {e}")
    
    async def send_update_stats(self, stats: Dict):
        """Отправить статистику обновления"""
        if not self.notification_chat_id:
            return
        
        try:
            message_text = "📊 **Статистика обновления базы данных:**\n\n"
            message_text += f"📱 Всего игр: {stats['total_games']}\n"
            message_text += f"⭐ С рейтингом: {stats['rated_games']}\n"
            message_text += f"🖼️ С изображениями: {stats['games_with_images']}\n"
            message_text += f"📸 Со скриншотами: {stats['games_with_screenshots']}\n\n"
            message_text += "✅ База данных успешно обновлена!"
            
            await self.bot.send_message(
                chat_id=self.notification_chat_id,
                text=message_text,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error sending update stats: {e}")
    
    async def send_weekly_stats(self):
        """Отправить еженедельную статистику"""
        if not self.notification_chat_id:
            return
        
        try:
            stats = await self.db.get_statistics()
            recent_games = await self.db.get_recent_games(days=7, limit=5)
            
            message_text = "📈 **Еженедельная статистика Game Tracker:**\n\n"
            message_text += f"📱 Игр в базе: {stats['total_games']}\n"
            message_text += f"⭐ С рейтингом: {stats['rated_games']}\n"
            message_text += f"🖼️ С изображениями: {stats['games_with_images']}\n"
            
            if recent_games:
                message_text += f"\n🆕 **Новые игры за неделю:**\n"
                for game in recent_games:
                    title = game.get('title', 'Unknown')
                    rating = game.get('rating', 'N/A')
                    message_text += f"• {title}"
                    if rating != 'N/A':
                        message_text += f" ⭐{rating}"
                    message_text += "\n"
            
            message_text += "\n💡 Используйте /genres для просмотра всех жанров"
            
            await self.bot.send_message(
                chat_id=self.notification_chat_id,
                text=message_text,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error sending weekly stats: {e}")
    
    def set_notification_chat(self, chat_id: int):
        """Установить чат для уведомлений"""
        self.notification_chat_id = chat_id
        logger.info(f"Notification chat set to: {chat_id}")
    
    def run_scheduler(self):
        """Запустить планировщик в отдельном потоке"""
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Проверка каждую минуту
    
    def start(self):
        """Запустить планировщик"""
        if not self.running:
            self.running = True
            self.scheduler_thread = Thread(target=self.run_scheduler, daemon=True)
            self.scheduler_thread.start()
            logger.info("Scheduler started")
    
    def stop(self):
        """Остановить планировщик"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join()
        logger.info("Scheduler stopped")
    
    async def manual_check(self):
        """Ручная проверка новых игр"""
        await self.check_new_games()
    
    async def manual_update(self):
        """Ручное обновление базы данных"""
        await self.update_database()
