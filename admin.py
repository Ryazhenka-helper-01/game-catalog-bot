import asyncio
import logging
import aiosqlite
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from database import Database
from parser import GameParser
from scheduler import GameScheduler

logger = logging.getLogger(__name__)

class AdminCommands:
    def __init__(self, db: Database, parser: GameParser, scheduler: GameScheduler):
        self.db = db
        self.parser = parser
        self.scheduler = scheduler
        self.admin_chat_id = None
    
    def get_handlers(self):
        """Получить обработчики админских команд"""
        return [
            CommandHandler("admin", self.admin_menu),
            CommandHandler("update_db", self.update_database),
            CommandHandler("check_new", self.check_new_games),
            CommandHandler("stats", self.show_stats),
            CommandHandler("notify_chat", self.set_notification_chat),
            CommandHandler("manual_parse", self.manual_parse),
            CommandHandler("clear_db", self.clear_database),
            CallbackQueryHandler(self.handle_admin_callback, pattern='^admin_')
        ]
    
    async def admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать админское меню"""
        chat_id = update.effective_chat.id
        
        # Проверка на админа (здесь можно добавить проверку по ID)
        if not await self.is_admin(chat_id):
            await update.message.reply_text("❌ Доступ запрещен")
            return
        
        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("🔄 Обновить базу", callback_data="admin_update")],
            [InlineKeyboardButton("🔍 Проверить новые игры", callback_data="admin_check")],
            [InlineKeyboardButton("⚙️ Настройки уведомлений", callback_data="admin_notify")],
            [InlineKeyboardButton("🧹 Очистить базу", callback_data="admin_clear")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⚙️ **Админ панель Game Tracker**\n\n"
            "Выберите действие:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def handle_admin_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик админских callback'ов"""
        query = update.callback_query
        await query.answer()
        
        chat_id = update.effective_chat.id
        
        if not await self.is_admin(chat_id):
            await query.edit_message_text("❌ Доступ запрещен")
            return
        
        action = query.data.replace('admin_', '')
        
        if action == 'stats':
            await self._show_stats_inline(query)
        elif action == 'update':
            await self._update_database_inline(query)
        elif action == 'check':
            await self._check_new_games_inline(query)
        elif action == 'notify':
            await self._notify_settings_inline(query)
        elif action == 'clear':
            await self._clear_database_inline(query)
    
    async def _show_stats_inline(self, query):
        """Показать статистику"""
        try:
            stats = await self.db.get_statistics()
            recent_games = await self.db.get_recent_games(days=7, limit=5)
            genres = await self.db.get_all_genres()
            
            text = "📊 **Статистика Game Tracker:**\n\n"
            text += f"📱 Всего игр: {stats['total_games']}\n"
            text += f"⭐ С рейтингом: {stats['rated_games']}\n"
            text += f"🖼️ С изображениями: {stats['games_with_images']}\n"
            text += f"📸 Со скриншотами: {stats['games_with_screenshots']}\n"
            text += f"🏷️ Жанров: {len(genres)}\n"
            
            if recent_games:
                text += f"\n🆕 **Новые игры за неделю:** {len(recent_games)}\n"
                for game in recent_games[:3]:
                    title = game.get('title', 'Unknown')
                    text += f"• {title}\n"
            
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error showing stats: {e}")
            await query.edit_message_text("❌ Ошибка при получении статистики")
    
    async def _update_database_inline(self, query):
        """Обновить базу данных"""
        await query.edit_message_text("🔄 Начинаю обновление базы данных...")
        
        try:
            await self.scheduler.update_database()
            
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "✅ База данных успешно обновлена!",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error updating database: {e}")
            await query.edit_message_text("❌ Ошибка при обновлении базы данных")
    
    async def _check_new_games_inline(self, query):
        """Проверить новые игры"""
        await query.edit_message_text("🔍 Проверяю наличие новых игр...")
        
        try:
            await self.scheduler.check_new_games()
            
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "✅ Проверка новых игр завершена!",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error checking new games: {e}")
            await query.edit_message_text("❌ Ошибка при проверке новых игр")
    
    async def _notify_settings_inline(self, query):
        """Настройки уведомлений"""
        current_chat = self.scheduler.notification_chat_id
        
        text = "⚙️ **Настройки уведомлений:**\n\n"
        if current_chat:
            text += f"📢 Текущий чат для уведомлений: `{current_chat}`\n\n"
        else:
            text += "📢 Чат для уведомлений не настроен\n\n"
        
        text += "Отправьте команду /notify_chat в чате, где хотите получать уведомления"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def _clear_database_inline(self, query):
        """Очистить базу данных"""
        keyboard = [
            [InlineKeyboardButton("⚠️ Да, очистить", callback_data="admin_clear_confirm")],
            [InlineKeyboardButton("❌ Нет, отмена", callback_data="admin_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⚠️ **ВНИМАНИЕ!**\n\n"
            "Это действие удалит все игры из базы данных!\n"
            "Вы уверены?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def update_database(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда обновления базы данных"""
        chat_id = update.effective_chat.id
        
        if not await self.is_admin(chat_id):
            await update.message.reply_text("❌ Доступ запрещен")
            return
        
        await update.message.reply_text("🔄 Начинаю обновление базы данных...")
        
        try:
            await self.scheduler.update_database()
            await update.message.reply_text("✅ База данных успешно обновлена!")
            
        except Exception as e:
            logger.error(f"Error updating database: {e}")
            await update.message.reply_text("❌ Ошибка при обновлении базы данных")
    
    async def check_new_games(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда проверки новых игр"""
        chat_id = update.effective_chat.id
        
        if not await self.is_admin(chat_id):
            await update.message.reply_text("❌ Доступ запрещен")
            return
        
        await update.message.reply_text("🔍 Проверяю наличие новых игр...")
        
        try:
            await self.scheduler.check_new_games()
            await update.message.reply_text("✅ Проверка новых игр завершена!")
            
        except Exception as e:
            logger.error(f"Error checking new games: {e}")
            await update.message.reply_text("❌ Ошибка при проверке новых игр")
    
    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда показа статистики"""
        chat_id = update.effective_chat.id
        
        if not await self.is_admin(chat_id):
            await update.message.reply_text("❌ Доступ запрещен")
            return
        
        try:
            stats = await self.db.get_statistics()
            recent_games = await self.db.get_recent_games(days=7, limit=5)
            genres = await self.db.get_all_genres()
            
            text = "📊 **Статистика Game Tracker:**\n\n"
            text += f"📱 Всего игр: {stats['total_games']}\n"
            text += f"⭐ С рейтингом: {stats['rated_games']}\n"
            text += f"🖼️ С изображениями: {stats['games_with_images']}\n"
            text += f"📸 Со скриншотами: {stats['games_with_screenshots']}\n"
            text += f"🏷️ Жанров: {len(genres)}\n"
            
            if recent_games:
                text += f"\n🆕 **Новые игры за неделю:** {len(recent_games)}\n"
                for game in recent_games:
                    title = game.get('title', 'Unknown')
                    rating = game.get('rating', 'N/A')
                    text += f"• {title}"
                    if rating != 'N/A':
                        text += f" ⭐{rating}"
                    text += "\n"
            
            await update.message.reply_text(text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error showing stats: {e}")
            await update.message.reply_text("❌ Ошибка при получении статистики")
    
    async def set_notification_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установить чат для уведомлений"""
        chat_id = update.effective_chat.id
        
        if not await self.is_admin(chat_id):
            await update.message.reply_text("❌ Доступ запрещен")
            return
        
        self.scheduler.set_notification_chat(chat_id)
        await update.message.reply_text(
            f"✅ Этот чат ({chat_id}) установлен для получения уведомлений о новых играх"
        )
    
    async def manual_parse(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ручной парсинг сайта"""
        chat_id = update.effective_chat.id
        
        if not await self.is_admin(chat_id):
            await update.message.reply_text("❌ Доступ запрещен")
            return
        
        await update.message.reply_text("🔍 Начинаю парсинг сайта...")
        
        try:
            games = await self.parser.get_all_games()
            
            if games:
                await update.message.reply_text(f"📱 Найдено {len(games)} игр на сайте")
                
                # Добавляем игры в базу
                added_count = 0
                for game in games:
                    success = await self.db.add_game(game)
                    if success:
                        added_count += 1
                
                await update.message.reply_text(f"✅ Добавлено {added_count} игр в базу данных")
            else:
                await update.message.reply_text("⚠️ Игры на сайте не найдены")
                
        except Exception as e:
            logger.error(f"Error manual parsing: {e}")
            await update.message.reply_text("❌ Ошибка при парсинге сайта")
    
    async def clear_database(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Очистить базу данных"""
        chat_id = update.effective_chat.id
        
        if not await self.is_admin(chat_id):
            await update.message.reply_text("❌ Доступ запрещен")
            return
        
        # Подтверждение
        if context.args and context.args[0] == 'confirm':
            try:
                async with aiosqlite.connect(self.db.db_path) as db:
                    await db.execute('DELETE FROM games')
                    await db.execute('DELETE FROM notifications')
                    await db.commit()
                
                await update.message.reply_text("🧹 База данных очищена")
                
            except Exception as e:
                logger.error(f"Error clearing database: {e}")
                await update.message.reply_text("❌ Ошибка при очистке базы данных")
        else:
            await update.message.reply_text(
                "⚠️ Для очистки базы данных используйте: /clear_db confirm"
            )
    
    async def is_admin(self, chat_id: int) -> bool:
        """Проверка на админа (заглушка - нужно настроить)"""
        # Здесь можно добавить проверку по списку админов
        # Например: return chat_id in [123456789, 987654321]
        return True  # Временно разрешаем всем
