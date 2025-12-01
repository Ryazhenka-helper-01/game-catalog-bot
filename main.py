import os
import asyncio
import logging
import traceback
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from database import Database
from parser import GameParser
from scheduler import GameScheduler
from admin import AdminCommands
from utils import setup_logger, safe_execute

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logger = setup_logger(__name__, level=logging.INFO)

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
    
    async def _ensure_db_schema(self):
        """Выполнить миграцию БД при старте, если нужно"""
        await self.db.init_db()
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        try:
            # Получаем количество игр в базе для отображения в приветствии
            all_games = await self.db.get_all_games()
            total_games = len(all_games)

            welcome_text = (
                "Game Tracker Bot - ваш гид по играм Nintendo Switch. (на базе https://asst2game.ru)\n\n"
                "Версия: beta-1.1.1\n"
                f"Кол-во игр в базе: {total_games}\n\n"
                "Доступные команды:\n"
                "/start - краткая информация о боте и клавиатура команд\n"
                "/help - подробная справка по всем командам\n"
                "/genres - список жанров интерактивными кнопками\n"
                "/games - все игры с пагинацией по 5 штук\n"
                "/search [жанр] - поиск игр по жанру (можно писать жанр просто текстом)\n"
                "/stats - статистика по базе игр\n"
                "/update_genres - админ-команда обновления жанров из сайта\n\n"
                "Напишите жанр (например: Экшен, RPG, Приключение) или используйте кнопки ниже."
            )

            # Кнопки рядом с полем ввода: help, жанры, игры
            reply_keyboard = [["/help", "/genres", "/games"]]
            reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

            await update.message.reply_text(welcome_text, reply_markup=reply_markup)
            logger.info(f"User {update.effective_user.id} started the bot")
            
        except Exception as e:
            logger.error(f"Error in start_command: {e}")
            await safe_execute(
                update.message.reply_text,
                "Game Tracker Bot - Ваш гид по играм Nintendo Switch! Версия: beta-1.1.1"
            )
    
    async def genres_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список жанров"""
        try:
            genres = await self.db.get_all_genres()
            
            if not genres:
                await update.message.reply_text(
                    "🎮 **Жанры пока не загружены.**\n\n"
                    "База данных пуста, игры загружаются...\n"
                    "Попробуйте через несколько минут.",
                    parse_mode='Markdown'
                )
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
            logger.info(f"User {update.effective_user.id} viewed genres ({len(genres)} total)")
            
        except Exception as e:
            logger.error(f"Error in genres_command: {e}")
            await safe_execute(
                update.message.reply_text,
                "❌ Ошибка при загрузке жанров. Попробуйте позже."
            )
    
    async def games_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать все игры в виде кнопок по 5 штук"""
        try:
            games = await self.db.get_all_games()
            
            if not games:
                await update.message.reply_text("🎮 Игры пока не загружены. Попробуйте позже.")
                return
            
            logger.info(f"User {update.effective_user.id} requested all games ({len(games)} total)")
            
            # Показываем первые 5 игр
            await self.show_games_page(update, games, 0)
            
        except Exception as e:
            logger.error(f"Error in games_command: {e}")
            await safe_execute(
                update.message.reply_text,
                "❌ Ошибка при загрузке игр. Попробуйте позже."
            )
    
    async def show_games_page(self, update, games: list, offset: int):
        """Показать страницу с играми"""
        # Берем 5 игр для текущей страницы
        page_games = games[offset:offset+5]
        
        if not page_games:
            # Ничего не показываем, если игр больше нет
            if hasattr(update, "answer"):
                await update.answer("Больше игр нет")
            return
        
        # Создаем кнопки для игр
        keyboard = []
        for game in page_games:
            title = game.get('title', 'Без названия')
            game_id = game.get('id', 0)
            keyboard.append([InlineKeyboardButton(f"🎮 {title}", callback_data=f"game_{game_id}_0")])
        
        # Добавляем навигационные кнопки
        nav_buttons = []
        
        # Кнопка "Назад" если не первая страница
        if offset > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"games_page_{offset-5}"))
        
        # Кнопка "Еще" если есть еще игры
        if offset + 5 < len(games):
            nav_buttons.append(InlineKeyboardButton("➡️ Еще 5 игр", callback_data=f"games_page_{offset+5}"))
        
        # Добавляем навигацию если есть кнопки
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Формируем сообщение
        page_num = offset // 5 + 1
        total_pages = (len(games) + 4) // 5  # Округляем вверх
        
        message_text = f"🎮 **Все игры Nintendo Switch**\n\n"
        message_text += f"📄 Страница {page_num} из {total_pages}\n"
        message_text += f"📊 Показано игр {offset+1}-{min(offset+5, len(games))} из {len(games)}\n\n"
        message_text += "Выберите игру для подробной информации:"

        # Если это callback (нажатие на кнопку) — обновляем существующее сообщение
        if hasattr(update, "edit_message_text"):
            await update.edit_message_text(
                message_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            # Обычный вызов из /games — отправляем новое сообщение
            await update.message.reply_text(
                message_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    async def update_descriptions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обновить описания игр с сайта"""
        try:
            await update.message.reply_text("🔄 Начинаю обновление описаний игр с сайта...")
            
            games = await self.db.get_all_games()
            if not games:
                await update.message.reply_text("❌ Игры не найдены в базе данных.")
                return
            
            await update.message.reply_text(f"📊 Найдено {len(games)} игр. Начинаю обновление...")
            
            updated_count = 0
            failed_count = 0
            
            async with self.parser:
                for i, game in enumerate(games):
                    try:
                        game_url = game.get('url')
                        game_title = game.get('title', 'Unknown')
                        
                        if not game_url or game_url == self.parser.base_url:
                            failed_count += 1
                            continue
                        
                        # Загружаем страницу игры
                        html = await self.parser.get_page(game_url)
                        if not html or html == "":
                            failed_count += 1
                            continue
                        
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Извлекаем полное описание
                        full_description = self.extract_full_description(soup)
                        
                        # Извлекаем жанры (сохраняем существующие если новые не найдены)
                        new_genres = self.extract_genres_from_page(soup)
                        genres = new_genres if new_genres else game.get('genres', [])
                        
                        # Извлекаем рейтинг (сохраняем существующий если новый не найден)
                        new_rating = self.extract_rating_from_page(soup)
                        rating = new_rating if new_rating else game.get('rating', 'N/A')
                        
                        # Обновляем игру в базе
                        updated_game = {
                            'description': full_description,
                            'genres': genres,
                            'rating': rating
                        }
                        
                        await self.db.update_game(game['id'], updated_game)
                        
                        updated_count += 1
                        
                        # Небольшая задержка между запросами
                        if i < len(games) - 1:
                            await asyncio.sleep(0.5)
                        
                        # Показываем прогресс каждые 10 игр
                        if (i + 1) % 10 == 0:
                            await update.message.reply_text(
                                f"📈 Обработано {i+1}/{len(games)} игр...\n"
                                f"✅ Обновлено: {updated_count}\n"
                                f"❌ Пропущено: {failed_count}"
                            )
                    
                    except Exception as e:
                        failed_count += 1
                        logger.error(f"Error updating game {game.get('title', 'Unknown')}: {e}")
                        continue
            
            # Финальное сообщение
            await update.message.reply_text(
                f"✅ **Обновление описаний завершено!**\n\n"
                f"📊 **Статистика:**\n"
                f"🎮 Всего игр: {len(games)}\n"
                f"✅ Обновлено: {updated_count}\n"
                f"❌ Пропущено: {failed_count}\n\n"
                f"🎯 Теперь описания извлечены с сайта!\n"
                f"Используйте /games для просмотра обновленных игр.",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in update_descriptions_command: {e}")
            await safe_execute(
                update.message.reply_text,
                "❌ Ошибка при обновлении описаний. Попробуйте позже."
            )
    
    def extract_full_description(self, soup):
        """Извлечение полного описания из div class='full-story'"""
        
        # Способ 1: Ищем div class="full-story" (основной метод)
        try:
            full_story_div = soup.find('div', class_='full-story')
            if full_story_div:
                paragraphs = full_story_div.find_all('p')
                print(f"Found {len(paragraphs)} paragraphs in full-story")
                
                texts = []
                for p in paragraphs:
                    text = p.get_text().strip()
                    if text and len(text) > 20:  # Пропускаем очень короткие параграфы
                        texts.append(text)
                
                if texts:
                    full_text = "\n\n".join(texts)
                    if len(full_text) > 100:  # Проверяем, что описание достаточно длинное
                        return full_text
            else:
                print("div.full-story not found")
        except Exception as e:
            print(f"Error in full-story extraction: {e}")
        
        # Способ 2: Ищем все параграфы в article (резервный метод)
        try:
            article = soup.find('article')
            if article:
                paragraphs = article.find_all('p')
                print(f"Found {len(paragraphs)} paragraphs in article (fallback)")
                
                texts = []
                for p in paragraphs:
                    text = p.get_text().strip()
                    if text and len(text) > 20:  # Пропускаем очень короткие параграфы
                        texts.append(text)
                
                if texts:
                    full_text = "\n\n".join(texts)
                    if len(full_text) > 100:  # Проверяем, что описание достаточно длинное
                        return full_text
        except Exception:
            pass
        
        # Способ 3: Ищем контейнер по указанному пути (резервный)
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
        
        # Способ 4: Ищем по классам описания (резервный)
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
    
    def extract_genres_from_page(self, soup):
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
                    found_genres = self.extract_genre_names(text)
                    genres.extend(found_genres)
            except Exception:
                continue
        
        # Убираем дубликаты
        return list(set(genres))
    
    def extract_genre_names(self, text):
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
    
    def extract_rating_from_page(self, soup):
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
    
    async def update_genres_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обновить жанры для всех игр из HTML кода"""
        try:
            await update.message.reply_text("🔄 Начинаю обновление жанров для всех игр...")
            
            games = await self.db.get_all_games()
            if not games:
                await update.message.reply_text("❌ Игры не найдены в базе данных.")
                return
            
            await update.message.reply_text(f"📊 Найдено {len(games)} игр. Начинаю обработку...")
            
            updated_count = 0
            failed_count = 0
            
            async with self.parser:
                for i, game in enumerate(games):
                    try:
                        game_url = game.get('url')
                        if not game_url:
                            failed_count += 1
                            continue
                        
                        # Парсим страницу игры заново с новым методом извлечения жанров
                        updated_game = await self.parser.parse_game_details(game_url)
                        
                        if updated_game and updated_game.get('genres'):
                            # Обновляем только жанры в существующей игре
                            new_genres = updated_game.get('genres', [])
                            old_genres = game.get('genres', [])
                            
                            if new_genres != old_genres:
                                await self.db.update_game_genres(game['id'], new_genres)
                                updated_count += 1
                                
                                # Показываем прогресс каждые 10 игр
                                if (i + 1) % 10 == 0:
                                    await update.message.reply_text(
                                        f"📈 Обработано {i+1}/{len(games)} игр...\n"
                                        f"✅ Обновлено: {updated_count}\n"
                                        f"❌ Пропущено: {failed_count}"
                                    )
                            
                            logger.info(f"Updated genres for {game['title']}: {new_genres}")
                        else:
                            failed_count += 1
                            logger.warning(f"Failed to extract genres for {game['title']}")
                        
                        # Небольшая задержка чтобы не нагружать сайт
                        if (i + 1) % 20 == 0:
                            await asyncio.sleep(1)
                    
                    except Exception as e:
                        failed_count += 1
                        logger.error(f"Error processing game {game.get('title', 'Unknown')}: {e}")
                        continue
            
            # Финальное сообщение
            await update.message.reply_text(
                f"✅ **Обновление жанров завершено!**\n\n"
                f"📊 **Статистика:**\n"
                f"🎮 Всего игр: {len(games)}\n"
                f"✅ Обновлено: {updated_count}\n"
                f"❌ Пропущено: {failed_count}\n\n"
                f"🎯 Теперь жанры извлечены из HTML кода каждой игры!\n"
                f"Используйте /genres для просмотра обновленного списка.",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in update_genres_command: {e}")
            await safe_execute(
                update.message.reply_text,
                "❌ Ошибка при обновлении жанров. Попробуйте позже."
            )
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /search"""
        if not context.args:
            await update.message.reply_text("Использование: /search [жанр]")
            return
            
        genre = ' '.join(context.args)
        await self.search_games_by_genre(update, genre)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать помощь"""
        try:
            help_text = (
                "📋 ПОМОЩЬ - Game Tracker Bot\n\n"
                "Доступные команды:\n\n"
                "/start - краткая информация о боте и вывод основных кнопок команд.\n"
                "/help - это сообщение со списком всех команд и их описанием.\n"
                "/genres - показывает все жанры интерактивными кнопками.\n"
                "/games - список всех игр Nintendo Switch с пагинацией по 5 игр.\n"
                "/search [жанр] - поиск игр по жанру, можно писать жанр просто текстом (например: Экшен, RPG).\n"
                "/stats - статистика по базе игр и жанрам.\n"
                "/update_genres - админ-команда: обновить жанры для всех игр с сайта.\n"
                "/update_descriptions - админ-команда: обновить полные описания для всех игр с сайта.\n\n"
                "Как использовать бота:\n"
                "• В личке, группах и супергруппах можете писать жанр текстом или вызывать команды через слэш.\n"
                "• В каналах бот отвечает на команды администратора, отправленные как сообщения канала.\n"
                "• Для быстрых действий используйте кнопки под полем ввода: /help, /genres, /games.\n\n"
                "Пример: напишите 'Экшен' или вызовите /search Экшен — бот покажет игры этого жанра с кнопками."
            )

            await update.message.reply_text(help_text)
            logger.info(f"User {update.effective_user.id} requested help")
            
        except Exception as e:
            logger.error(f"Error in help_command: {e}")
            await safe_execute(update.message.reply_text, "📋 Помощь временно недоступна")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать статистику бота"""
        try:
            # Получаем статистику
            all_games = await self.db.get_all_games()
            all_genres = await self.db.get_all_genres()
            
            games_with_genres = [game for game in all_games if game.get('genres')]
            
            # Если база пустая
            if len(all_games) == 0:
                stats_text = """
📊 **СТАТИСТИКА БОТА**

🎮 **Игры в базе:** 0
🏷️ **С жанрами:** 0 (0.0%)
🎯 **Уникальных жанров:** 0

📈 **ТОП-10 ЖАНРОВ:**
   База данных пуста. Игры загружаются...

📱 **Версия:** beta-1.1.1
🔗 **Источник:** asst2game.ru
🚀 **Статус:** Инициализация
                """
                await update.message.reply_text(stats_text, parse_mode='Markdown')
                logger.info(f"User {update.effective_user.id} requested stats - database empty")
                return
            
            # Считаем топ жанры
            genre_counts = {}
            for genre in all_genres[:10]:  # Берем первые 10 для скорости
                games_by_genre = await self.db.get_games_by_genre(genre)
                genre_counts[genre] = len(games_by_genre)
            
            sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)
            
            stats_text = f"""
📊 **СТАТИСТИКА БОТА**

🎮 **Игры в базе:** {len(all_games)}
🏷️ **С жанрами:** {len(games_with_genres)} ({len(games_with_genres)/len(all_games)*100:.1f}%)
🎯 **Уникальных жанров:** {len(all_genres)}

📈 **ТОП-10 ЖАНРОВ:**
"""
            
            for i, (genre, count) in enumerate(sorted_genres, 1):
                stats_text += f"{i:2d}. {genre}: {count} игр\n"
            
            stats_text += f"""
📱 **Версия:** beta-1.1.1
🔗 **Источник:** asst2game.ru
🚀 **Статус:** Активен
            """
            
            await update.message.reply_text(stats_text, parse_mode='Markdown')
            logger.info(f"User {update.effective_user.id} requested stats")
            
        except Exception as e:
            logger.error(f"Error in stats_command: {e}")
            await safe_execute(update.message.reply_text, "📊 Статистика временно недоступна")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        message = update.effective_message
        if not message or not message.text:
            return
        genre = message.text.strip()
        await self.search_games_by_genre(update, genre)
    
    async def search_games_by_genre(self, update: Update, genre: str):
        """Поиск игр по жанру"""
        # Считаем общее количество игр в жанре
        total_games = await self.db.get_games_count_by_genre(genre)
        if total_games == 0:
            await update.message.reply_text(
                f"🎮 Игры в жанре '{genre}' не найдены.\n\n"
                "Попробуйте другой жанр или используйте /genres для просмотра всех жанров."
            )
            return
        
        # Берем первую страницу по 5 игр
        games = await self.db.get_games_by_genre(genre, limit=5, offset=0)
        
        # Создаем клавиатуру с первыми 5 играми
        keyboard = []
        for game in games[:5]:
            keyboard.append([InlineKeyboardButton(game['title'], callback_data=f"game_{game['id']}_0")])
        
        # Добавляем кнопку "Еще" если есть еще игры
        if total_games > 5:
            keyboard.append([InlineKeyboardButton("➡️ Еще", callback_data=f"more_{genre}_5")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🎮 **Найдено игр в жанре '{genre}': {total_games}**\n\n"
            "Выберите игру для подробной информации:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        
        try:
            # Навигация по страницам игр
            if callback_data.startswith("games_page_"):
                offset = int(callback_data.split("_")[-1])
                games = await self.db.get_all_games()
                await self.show_games_page(query, games, offset)
                return
            
            # Обработка кнопки жанра
            if callback_data.startswith("genre_"):
                genre = callback_data.replace("genre_", "")
                await self.search_games_by_genre_callback(query, genre)
                return
            
            # Обработка кнопки "больше жанров"
            if callback_data == "more_genres":
                await query.edit_message_text("📋 Все жанры загружены. Выберите интересующий:")
                return
            
            # Обработка кнопки "назад к жанрам"
            if callback_data == "back_to_genres":
                await self.genres_command_callback(query)
                return
            
            # Обработка кнопки игры
            if callback_data.startswith("game_"):
                parts = callback_data.split("_")
                game_id = int(parts[1])
                page = int(parts[2]) if len(parts) > 2 else 0
                await self.show_game_details(query, game_id, page, context)
                return
            
            # Обработка кнопки "Читать далее"
            if callback_data.startswith("read_more_"):
                game_id = int(callback_data.split("_")[2])
                await self.handle_read_more(query, game_id, context)
                return
            
            # Обработка кнопки "еще игры в жанре"
            if callback_data.startswith("more_"):
                parts = callback_data.split("_")
                genre = parts[1]
                offset = int(parts[2]) if len(parts) > 2 else 5
                await self.show_more_games(query, genre, offset)
                return
            
            # Обработка кнопки "назад к поиску"
            if callback_data == "back_to_search":
                await self.handle_back_to_search(query)
                return
            
            # Обработка noop (кнопка без действия)
            if callback_data == "noop":
                return
            
        except Exception as e:
            logger.error(f"Error handling callback {callback_data}: {e}")
            await query.edit_message_text("❌ Ошибка. Попробуйте снова.")
    
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
        # Считаем общее количество игр в жанре
        total_games = await self.db.get_games_count_by_genre(genre)
        if total_games == 0:
            await query.edit_message_text(
                f"🎮 Игры в жанре '{genre}' не найдены.\n\n"
                "Попробуйте другой жанр или используйте /genres для просмотра всех жанров."
            )
            return
        
        # Берем первую страницу по 5 игр
        games = await self.db.get_games_by_genre(genre, limit=5, offset=0)
        
        # Создаем клавиатуру с первыми 5 играми
        keyboard = []
        for game in games[:5]:
            keyboard.append([InlineKeyboardButton(game['title'], callback_data=f"game_{game['id']}_0")])
        
        # Добавляем кнопку "Показать еще игры" если есть еще игры
        if total_games > 5:
            keyboard.append([InlineKeyboardButton("📋 Показать еще игры", callback_data=f"more_{genre}_5")])
        
        # Кнопка "Назад к жанрам"
        keyboard.append([InlineKeyboardButton("🔙 Назад к жанрам", callback_data="back_to_genres")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🎮 **Найдено игр в жанре '{genre}': {total_games}**\n\n"
            "Выберите игру для подробной информации:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_game_details(self, query, game_id: int, page: int = 0, context: ContextTypes.DEFAULT_TYPE | None = None):
        """Показать подробную информацию об игре"""
        try:
            game = await self.db.get_game_by_id(game_id)
            if not game:
                await query.answer("Игра не найдена")
                return
            
            # Формируем сообщение с информацией об игре
            title = game.get('title', 'Без названия')
            genres = game.get('genres', [])
            rating = game.get('rating', 'N/A')
            release_date = game.get('release_date', 'Неизвестна')
            description = game.get('description', 'Описание отсутствует')
            image_url = game.get('image_url', '')
            url = game.get('url', '')
            
            # Жанры
            if genres and isinstance(genres, list):
                genre_text = ', '.join(genres[:3])  # Показываем первые 3 жанра
                if len(genres) > 3:
                    genre_text += f" и еще {len(genres) - 3}"
            else:
                genre_text = 'Не указаны'
            
            message_text = f"🎮 **{title}**\n\n"
            message_text += f"� **Жанры:** {genre_text}\n"
            
            # Рейтинг
            if rating and rating != 'N/A':
                message_text += f"⭐ **Рейтинг:** {rating}/10\n"
            
            # Дата релиза
            if release_date:
                message_text += f"📅 **Дата релиза:** {release_date}\n\n"
            
            # Обработка описания с сокращением
            full_description = description if description and description != 'Описание отсутствует' else ""
            
            if full_description:
                # Разбиваем описание на абзацы
                paragraphs = full_description.split('\n\n')
                paragraphs = [p.strip() for p in paragraphs if p.strip()]
                
                if len(paragraphs) > 2:
                    # Показываем только первые 2 абзаца
                    short_description = '\n\n'.join(paragraphs[:2])
                    message_text += f"📝 **Описание:**\n{short_description}\n\n"
                else:
                    # Если абзацев 2 или меньше, показываем все
                    message_text += f"📝 **Описание:**\n{full_description}\n\n"
            else:
                message_text += f"📝 **Описание:** Отсутствует\n\n"
            
            # Добавляем информацию о скриншотах
            screenshots = game.get('screenshots', [])
            if screenshots:
                message_text += f"🖼️ **Скриншоты:** {len(screenshots)} шт. (используйте кнопки ниже)\n\n"
            
            message_text += f"🔗 **Источник:** [Игры Nintendo Switch]({url})\n\n"
            
            # Создаем клавиатуру
            keyboard = []
            
            # Кнопка "Читать далее" если описание было сокращено
            if full_description and len(full_description.split('\n\n')) > 2:
                keyboard.append([InlineKeyboardButton("📖 Читать далее", callback_data=f"read_more_{game_id}")])
            
            # Кнопки навигации по скриншотам
            if screenshots:
                nav_buttons = []
                if page > 0:
                    nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"game_{game_id}_{page-1}"))
                nav_buttons.append(InlineKeyboardButton(f"📸 {page+1}/{len(screenshots)}", callback_data="noop"))
                if page < len(screenshots) - 1:
                    nav_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"game_{game_id}_{page+1}"))
                if nav_buttons:
                    keyboard.append(nav_buttons)
            
            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            
            # Отправка изображения или текста
            if image_url and image_url.startswith('http'):
                try:
                    chat_id = query.message.chat_id
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=image_url,
                        caption=message_text,
                        reply_markup=reply_markup,
                        parse_mode='Markdown',
                        disable_web_page_preview=True
                    )
                    # Обновляем старое сообщение
                    await query.edit_message_text(
                        text="Карточка игры отправлена ниже 👇",
                        reply_markup=None
                    )
                except Exception:
                    # Если фото не загрузилось, отправляем текст
                    await query.edit_message_text(
                        text=message_text,
                        reply_markup=reply_markup,
                        parse_mode='Markdown',
                        disable_web_page_preview=True
                    )
            else:
                await query.edit_message_text(
                    text=message_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
                
        except Exception as e:
            logger.error(f"Error showing game details: {e}")
            await query.answer("Ошибка при загрузке информации об игре")
    
    async def handle_read_more(self, query, game_id: int, context: ContextTypes.DEFAULT_TYPE | None = None):
        """Обработчик кнопки 'Читать далее'"""
        try:
            # Получаем игру напрямую из базы данных
            game = await self.db.get_game_by_id(game_id)
            if not game:
                await query.answer("Игра не найдена")
                return
            
            title = game.get('title', 'Без названия')
            description = game.get('description', 'Описание отсутствует')
            url = game.get('url', '')
            
            if not description or description == 'Описание отсутствует':
                await query.answer("Полное описание отсутствует")
                return
            
            # Формируем полное описание
            message_text = f"📖 **Полное описание игры {title}**\n\n"
            message_text += f"📝 **Описание:**\n{description}\n\n"
            message_text += f"🔗 **Источник:** [Игры Nintendo Switch]({url})"
            
            # Telegram ограничивает сообщение ~4096 символами
            if len(message_text) > 4000:
                # Разбиваем на части если слишком длинное
                parts = []
                current_part = ""
                
                lines = message_text.split('\n')
                for line in lines:
                    if len(current_part + line + '\n') <= 4000:
                        current_part += line + '\n'
                    else:
                        if current_part:
                            parts.append(current_part)
                        current_part = line + '\n'
                
                if current_part:
                    parts.append(current_part)
                
                # Отправляем части
                chat_id = query.message.chat_id
                for i, part in enumerate(parts):
                    if i == 0:
                        # Первую часть отправляем как обновление сообщения
                        await query.edit_message_text(
                            text=part,
                            parse_mode='Markdown',
                            disable_web_page_preview=True
                        )
                    else:
                        # Остальные части как новые сообщения
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=part,
                            parse_mode='Markdown',
                            disable_web_page_preview=True
                        )
            else:
                # Отправляем как обычное сообщение
                await query.edit_message_text(
                    text=message_text,
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
                
        except Exception as e:
            logger.error(f"Error in handle_read_more: {e}")
            await query.answer("Ошибка при загрузке полного описания")
    
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
        application.add_handler(CommandHandler("games", self.games_command))
        application.add_handler(CommandHandler("update_genres", self.update_genres_command))
        application.add_handler(CommandHandler("update_descriptions", self.update_descriptions_command))
        application.add_handler(CommandHandler("search", self.search_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        
        # Добавление админских команд
        admin_handlers = self.admin_commands.get_handlers()
        for handler in admin_handlers:
            application.add_handler(handler)
        
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Обработчик ошибок
        application.add_error_handler(self.error_handler)
        
        # Подсказки для слэш-команд (список команд в клиенте Telegram)
        async def post_init(application: Application) -> None:
            """Инициализация после запуска приложения"""
            # Установка команд бота
            commands = [
                BotCommand("start", "Запустить бота и краткая информация"),
                BotCommand("help", "Подробная справка по всем командам"),
                BotCommand("genres", "Показать список жанров"),
                BotCommand("games", "Показать все игры"),
                BotCommand("search", "Поиск игр по жанру"),
                BotCommand("stats", "Статистика по играм и жанрам"),
            ]
            await application.bot.set_my_commands(commands)
            
            # База данных уже инициализирована в main, повторно не вызываем

        application.post_init = post_init
        
        # Запуск бота (без планировщика на время)
        # self.scheduler.start()
        
        # Запуск бота
        application.run_polling()

if __name__ == '__main__':
    # Запуск для Railway с защитой от дублирования
    import os
    import asyncio
    import time
    import random
    
    # Простая защита от дублирования через переменную окружения
    bot_instance_id = os.environ.get('BOT_INSTANCE_ID', str(random.randint(1000, 9999)))
    os.environ['BOT_INSTANCE_ID'] = bot_instance_id
    
    print(f"Starting bot instance {bot_instance_id}")
    
    # Небольшая случайная задержка чтобы разнести запуски
    time.sleep(random.uniform(1, 3))
    
    # Импортируем функцию гарантированного исправления
    from railway_database_fix import guaranteed_railway_fix
    
    # Инициализация базы данных
    bot = GameTrackerBot()
    
    # Проверка наличия токена
    if not bot.bot_token:
        print("Bot token not found. Exiting...")
        exit(1)
    
    # Автоматический парсинг игр при первом запуске
    print("Starting initial game parsing...")
    try:
        # СНАЧАЛА инициализируем базу данных
        print("Initializing database...")
        asyncio.get_event_loop().run_until_complete(bot.db.init_db())
        print("Database initialized successfully!")
        
        # Затем проверяем, есть ли игры в базе
        existing_games = asyncio.get_event_loop().run_until_complete(bot.db.get_all_games())
        
        if len(existing_games) < 100:  # Если игр меньше 100, загружаем из JSON
            print(f"Database has only {len(existing_games)} games. Loading from JSON files...")
            
            # Пробуем гарантированное исправление (если есть JSON)
            try:
                result = guaranteed_railway_fix()
                if result:
                    print("✅ Games loaded from JSON successfully!")
                else:
                    print("❌ JSON loading failed - trying smart parser...")
                    # Если JSON нет, пробуем умный парсер
                    from smart_game_parser import smart_parse_all_games
                    fallback_result = smart_parse_all_games()
                    if fallback_result:
                        print("✅ Smart parser successful!")
                    else:
                        print("❌ All methods failed")
                
            except Exception as e:
                print(f"Error in guaranteed fix: {e}")
                print("❌ JSON loading failed - trying smart parser...")
                # Если JSON нет или ошибка, пробуем умный парсер
                try:
                    from smart_game_parser import smart_parse_all_games
                    fallback_result = smart_parse_all_games()
                    if fallback_result:
                        print("✅ Smart parser successful!")
                    else:
                        print("❌ All methods failed")
                except Exception as e2:
                    print(f"Error in smart parser: {e2}")
                    print("❌ All methods failed")
        
        # Проверяем, нужно ли обновлять описания (однократно с сохранением в файл)
        print("🔄 Checking if description updates are needed...")
        try:
            import os
            import time
            from datetime import datetime
            
            async def check_and_update_descriptions():
                # Проверяем файл-флаг
                flag_file = "descriptions_updated.flag"
                
                if os.path.exists(flag_file):
                    print("✅ Descriptions already updated. Skipping automatic update.")
                    # Проверяем время файла (не старше 7 дней)
                    file_age = time.time() - os.path.getmtime(flag_file)
                    if file_age < 7 * 24 * 3600:  # 7 дней
                        print(f"📅 Flag file is {int(file_age/3600)} hours old. Update skipped.")
                        return  # Выходим из функции
                    else:
                        print("📅 Flag file is older than 7 days. Forcing update...")
                        os.remove(flag_file)
                    if os.path.exists(flag_file):
                        return  # Выходим из функции
                
                print("📊 First run detected. Starting description updates...")
                
                games = await bot.db.get_all_games()
                if not games:
                    print("❌ No games found in database")
                    return
                
                updated_count = 0
                failed_count = 0
                
                for i, game in enumerate(games):
                    try:
                        # Проверяем что game не None
                        if not game:
                            failed_count += 1
                            continue
                            
                        game_url = game.get('url') if game else None
                        game_title = game.get('title', 'Unknown') if game else 'Unknown'
                        
                        if not game_url or game_url == bot.parser.base_url:
                            failed_count += 1
                            continue
                        
                        # Загружаем страницу игры
                        html = await bot.parser.get_page(game_url)
                        if not html or html == "":
                            failed_count += 1
                            continue
                        
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Извлекаем полное описание
                        full_description = bot.parser.extract_full_description(soup)
                        
                        # Извлекаем жанры (сохраняем существующие если новые не найдены)
                        new_genres = bot.parser.extract_genres_from_page(soup)
                        genres = new_genres if new_genres else game.get('genres', [])
                        
                        # Извлекаем рейтинг (сохраняем существующий если новый не найден)
                        new_rating = bot.parser.extract_rating_from_page(soup)
                        rating = new_rating if new_rating else game.get('rating', 'N/A')
                        
                        # Обновляем игру в базе
                        updated_game = {
                            'description': full_description,
                            'genres': genres,
                            'rating': rating
                        }
                        
                        await bot.db.update_game(game['id'], updated_game)
                        updated_count += 1
                        
                        # Небольшая задержка между запросами
                        if i < len(games) - 1:
                            await asyncio.sleep(0.5)
                        
                        # Показываем прогресс каждые 50 игр
                        if (i + 1) % 50 == 0:
                            print(f"📈 Processed {i+1}/{len(games)} games...")
                    
                    except Exception as e:
                        failed_count += 1
                        game_title = game.get('title', 'Unknown') if game else 'Unknown'
                        print(f"Error updating game {game_title}: {e}")
                        continue
                
                # Создаем файл-флаг
                with open(flag_file, 'w') as f:
                    f.write(f"Descriptions updated on {datetime.now().isoformat()}\n")
                    f.write(f"Updated: {updated_count} games\n")
                    f.write(f"Skipped: {failed_count} games\n")
                
                # Финальная статистика
                print(f"✅ **One-time description update completed!**")
                print(f"📊 **Statistics:**")
                print(f"🎮 Total games: {len(games)}")
                print(f"✅ Updated: {updated_count}")
                print(f"❌ Skipped: {failed_count}")
                print(f"🎯 Descriptions are now fresh from div.full-story!")
                print(f"🔒 This update will not run again automatically.")
                print(f"📁 Flag file created: {flag_file}")
            
            # Запускаем проверку и обновление
            asyncio.get_event_loop().run_until_complete(check_and_update_descriptions())
                
        except Exception as e:
            print(f"❌ Error during description update check: {e}")
        
        # Показываем статистику
        all_games = asyncio.get_event_loop().run_until_complete(bot.db.get_all_games())
        genres = asyncio.get_event_loop().run_until_complete(bot.db.get_all_genres())
        print(f"Database stats: {len(all_games)} games, {len(genres)} genres")
        
    except Exception as e:
        print(f"Error during initial parsing: {e}")
    
    print("Starting bot...")
    # Запуск бота (только один раз) с настройками для Railway
    port = int(os.environ.get('PORT', 8080))
    
    # Улучшенная защита от конфликтов с файловой блокировкой
    lock_file = f"bot_instance_{bot_instance_id}.lock"
    
    try:
        # Проверяем, есть ли другие экземпляры
        import glob
        existing_locks = glob.glob("bot_instance_*.lock")
        if existing_locks:
            print(f"⚠️ Found existing lock files: {existing_locks}")
            # Удаляем старые lock файлы (старше 10 минут)
            import time
            current_time = time.time()
            for lock in existing_locks:
                try:
                    file_age = current_time - os.path.getmtime(lock)
                    if file_age > 600:  # 10 минут
                        os.remove(lock)
                        print(f"🧹 Removed old lock file: {lock}")
                    else:
                        print(f"🔒 Another bot instance is running (lock: {lock}, age: {int(file_age)}s)")
                        print("Exiting to prevent conflicts...")
                        exit(0)
                except:
                    pass
        
        # Создаем свой lock файл
        with open(lock_file, 'w') as f:
            f.write(f"Bot instance {bot_instance_id} started at {time.time()}\n")
        
        print(f"🚀 Bot instance {bot_instance_id} starting...")
        print(f"🔒 Lock file created: {lock_file}")
        
        try:
            bot.run()
        finally:
            # Удаляем lock файл при выходе
            try:
                os.remove(lock_file)
                print(f"🔓 Lock file removed: {lock_file}")
            except:
                pass
                
    except Exception as e:
        print(f"❌ Bot instance {bot_instance_id} error: {e}")
        # Удаляем lock файл при ошибке
        try:
            os.remove(lock_file)
            print(f"🔓 Lock file removed due to error: {lock_file}")
        except:
            pass
        
        # Если конфликт, ждем и выходим
        if "Conflict" in str(e):
            print("🔄 Conflict detected, another instance is running. Exiting...")
            time.sleep(5)
            exit(1)
        else:
            raise
