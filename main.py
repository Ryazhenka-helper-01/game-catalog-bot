import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from database import Database
from parser import GameParser
from scheduler import GameScheduler
from admin import AdminCommands

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class GameTrackerBot:
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        
        if not self.bot_token:
            print("ERROR: TELEGRAM_BOT_TOKEN not found in environment variables!")
            print("Please set TELEGRAM_BOT_TOKEN in Railway Settings → Variables")
            return
            
        self.db = Database()
        self.parser = GameParser()
        self.scheduler = GameScheduler(self.db, self.bot_token)
        self.admin_commands = AdminCommands(self.db, self.parser, self.scheduler)
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        welcome_text = """
🎮 **Game Tracker Bot** - Ваш гид по играм Nintendo Switch!

Я помогу вам найти игры по жанрам. Просто напишите название жанра, например:
- Action
- RPG  
- Adventure
- Puzzle
- Strategy

Доступные команды:
/start - Показать это сообщение
/genres - Список всех жанров
/search [жанр] - Поиск игр по жанру

Начните поиск прямо сейчас! 🚀
        """
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def genres_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать все доступные жанры в виде кнопок"""
        try:
            genres = await self.db.get_all_genres()
            
            if not genres:
                await update.message.reply_text("🎮 Жанры пока не загружены. Попробуйте позже.")
                return
            
            # Создаем кнопки для жанров
            keyboard = []
            for i, genre in enumerate(genres[:20]):  # Показываем первые 20 жанров
                if genre and genre.strip():
                    keyboard.append([InlineKeyboardButton(f"🎮 {genre}", callback_data=f"genre_{genre}")])
            
            # Добавляем кнопку "Показать еще" если жанров больше 20
            if len(genres) > 20:
                keyboard.append([InlineKeyboardButton("📋 Больше жанров", callback_data="more_genres")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🎮 **Выберите жанр игр:**\n\n"
                f"Найдено {len(genres)} жанров",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in genres_command: {e}")
            await update.message.reply_text("❌ Ошибка при загрузке жанров")
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /search"""
        if not context.args:
            await update.message.reply_text("Использование: /search [жанр]")
            return
            
        genre = ' '.join(context.args)
        await self.search_games_by_genre(update, genre)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        genre = update.message.text.strip()
        await self.search_games_by_genre(update, genre)
    
    async def search_games_by_genre(self, update: Update, genre: str):
        """Поиск игр по жанру"""
        games = await self.db.get_games_by_genre(genre)
        
        if not games:
            await update.message.reply_text(
                f"🎮 Игры в жанре '{genre}' не найдены.\n\n"
                "Попробуйте другой жанр или используйте /genres для просмотра всех жанров."
            )
            return
        
        # Создаем клавиатуру с первыми 5 играми
        keyboard = []
        for game in games[:5]:
            keyboard.append([InlineKeyboardButton(game['title'], callback_data=f"game_{game['id']}_0")])
        
        # Добавляем кнопку "Еще" если есть еще игры
        if len(games) > 5:
            keyboard.append([InlineKeyboardButton("➡️ Еще", callback_data=f"more_{genre}_5")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🎮 **Найдено игр в жанре '{genre}': {len(games)}**\n\n"
            "Выберите игру для подробной информации:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith('genre_'):
            # Поиск игр по жанру из кнопки
            genre = data.replace('genre_', '', 1)
            await self.search_games_by_genre_callback(query, genre)
            
        elif data.startswith('game_'):
            # Показать информацию об игре
            game_id = int(data.split('_')[1])
            page = int(data.split('_')[2])
            await self.show_game_details(query, game_id, page)
            
        elif data.startswith('more_'):
            # Показать еще игры
            parts = data.split('_')
            genre = '_'.join(parts[1:-1])
            offset = int(parts[-1])
            await self.show_more_games(query, genre, offset)
        elif data.startswith('back_to_search'):
            # Возврат к поиску
            await self.handle_back_to_search(query)
        elif data == 'back_to_genres':
            # Возврат к списку жанров
            await self.genres_command_callback(query)
        elif data.startswith('admin_'):
            # Админские команды
            await self.admin_commands.handle_admin_callback(update, context)
        elif data == 'admin_back':
            # Возврат в админское меню
            await self.admin_commands.admin_menu(update, context)
    
    async def genres_command_callback(self, query):
        """Показать все доступные жанры в виде кнопок (callback версия)"""
        try:
            genres = await self.db.get_all_genres()
            
            if not genres:
                await query.edit_message_text("🎮 Жанры пока не загружены. Попробуйте позже.")
                return
            
            # Создаем кнопки для жанров
            keyboard = []
            for i, genre in enumerate(genres[:20]):  # Показываем первые 20 жанров
                if genre and genre.strip():
                    keyboard.append([InlineKeyboardButton(f"🎮 {genre}", callback_data=f"genre_{genre}")])
            
            # Добавляем кнопку "Показать еще" если жанров больше 20
            if len(genres) > 20:
                keyboard.append([InlineKeyboardButton("📋 Больше жанров", callback_data="more_genres")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "🎮 **Выберите жанр игр:**\n\n"
                f"Найдено {len(genres)} жанров",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in genres_command_callback: {e}")
            await query.edit_message_text("❌ Ошибка при загрузке жанров")
    
    async def search_games_by_genre_callback(self, query, genre: str):
        """Поиск игр по жанру из кнопки"""
        games = await self.db.get_games_by_genre(genre)
        
        if not games:
            await query.edit_message_text(
                f"🎮 Игры в жанре '{genre}' не найдены.\n\n"
                "Попробуйте другой жанр или используйте /genres для просмотра всех жанров."
            )
            return
        
        # Создаем клавиатуру с первыми 5 играми
        keyboard = []
        for game in games[:5]:
            keyboard.append([InlineKeyboardButton(game['title'], callback_data=f"game_{game['id']}_0")])
        
        # Добавляем кнопку "Еще" если есть еще игры
        if len(games) > 5:
            keyboard.append([InlineKeyboardButton("➡️ Еще", callback_data=f"more_{genre}_5")])
        
        # Кнопка "Назад к жанрам"
        keyboard.append([InlineKeyboardButton("🔙 Назад к жанрам", callback_data="back_to_genres")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🎮 **Найдено игр в жанре '{genre}': {len(games)}**\n\n"
            "Выберите игру для подробной информации:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_game_details(self, query, game_id: int, page: int = 0):
        """Показать детальную информацию об игре"""
        game = await self.db.get_game_by_id(game_id)
        
        if not game:
            await query.edit_message_text("Игра не найдена")
            return
        
        # Формируем сообщение с информацией об игре
        title = game['title']
        description = game.get('description', 'Описание отсутствует')
        rating = game.get('rating', 'N/A')
        genres = game.get('genres', [])
        image_url = game.get('image_url', '')
        
        message_text = f"🎮 **{title}**\n\n"
        message_text += f"⭐ **Рейтинг:** {rating}/10\n\n"
        
        if genres:
            message_text += f"🏷️ **Жанры:** {', '.join(genres)}\n\n"
        
        message_text += f"📝 **Описание:**\n{description}\n\n"
        
        # Создаем клавиатуру для навигации по скриншотам
        keyboard = []
        
        # Кнопки навигации по скриншотам
        screenshots = game.get('screenshots', [])
        if screenshots:
            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"game_{game_id}_{page-1}"))
            nav_buttons.append(InlineKeyboardButton(f"📸 {page+1}/{len(screenshots)}", callback_data="noop"))
            if page < len(screenshots) - 1:
                nav_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"game_{game_id}_{page+1}"))
            keyboard.append(nav_buttons)
        
        # Кнопка "Назад к списку"
        keyboard.append([InlineKeyboardButton("🔙 Назад к списку", callback_data="back_to_search")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем изображение или скриншот
        try:
            if page < len(screenshots):
                photo_url = screenshots[page]
            elif image_url:
                photo_url = image_url
            else:
                photo_url = None
            
            if photo_url:
                await query.edit_message_media(
                    media={'type': 'photo', 'media': photo_url, 'caption': message_text},
                    reply_markup=reply_markup
                )
            else:
                await query.edit_message_text(
                    text=message_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Error sending game details: {e}")
            await query.edit_message_text(
                text=message_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    async def show_more_games(self, query, genre: str, offset: int):
        """Показать еще игры"""
        games = await self.db.get_games_by_genre(genre, limit=5, offset=offset)
        
        if not games:
            await query.answer("Больше игр нет")
            return
        
        # Создаем клавиатуру
        keyboard = []
        for game in games:
            keyboard.append([InlineKeyboardButton(game['title'], callback_data=f"game_{game['id']}_0")])
        
        # Добавляем кнопки навигации
        nav_buttons = []
        if offset >= 5:
            nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"more_{genre}_{offset-5}"))
        
        # Проверяем, есть ли еще игры
        total_games = await self.db.get_games_count_by_genre(genre)
        if offset + 5 < total_games:
            nav_buttons.append(InlineKeyboardButton("➡️ Еще", callback_data=f"more_{genre}_{offset+5}"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([InlineKeyboardButton("🔙 Назад к поиску", callback_data="back_to_search")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🎮 **Игры в жанре '{genre}'** (показано {offset+1}-{min(offset+5, total_games)} из {total_games})\n\n"
            "Выберите игру:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def handle_back_to_search(self, query):
        """Возврат к поиску"""
        await query.edit_message_text(
            "🔍 **Напишите жанр для поиска игр**\n\n"
            "Или используйте /genres для просмотра всех жанров",
            parse_mode='Markdown'
        )
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.message:
            await update.message.reply_text(
                "❌ Произошла ошибка. Попробуйте позже."
            )
    
    def run(self):
        """Запуск бота"""
        application = Application.builder().token(self.bot_token).build()
        
        # Регистрация обработчиков
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("genres", self.genres_command))
        application.add_handler(CommandHandler("search", self.search_command))
        
        # Добавление админских команд
        admin_handlers = self.admin_commands.get_handlers()
        for handler in admin_handlers:
            application.add_handler(handler)
        
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Обработчик ошибок
        application.add_error_handler(self.error_handler)
        
        # Запуск бота (без планировщика на время)
        # self.scheduler.start()
        
        # Запуск бота
        application.run_polling()

if __name__ == '__main__':
    # Запуск для Railway
    import os
    
    # Инициализация базы данных
    import asyncio
    bot = GameTrackerBot()
    
    # Проверка наличия токена
    if not bot.bot_token:
        print("Bot token not found. Exiting...")
        exit(1)
    
    asyncio.get_event_loop().run_until_complete(bot.db.init_db())
    
    # Автоматический парсинг игр при первом запуске
    print("Starting initial game parsing...")
    try:
        games = asyncio.get_event_loop().run_until_complete(bot.parser.get_all_games())
        if games:
            print(f"Found {len(games)} games from asst2game.ru")
            added_count = 0
            for game in games:
                success = asyncio.get_event_loop().run_until_complete(bot.db.add_game(game))
                if success:
                    added_count += 1
            print(f"Successfully added {added_count} games to database")
        else:
            print("No games found on the website")
    except Exception as e:
        print(f"Error during initial parsing: {e}")
    
    # Запуск бота
    port = int(os.environ.get('PORT', 8080))
    bot.run()
