import logging
import traceback
import html
import re
import time
from typing import Optional, List, Dict, Any
from io import BytesIO
import requests
from urllib.parse import urljoin, urlparse

# Настройка логирования
def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Создает и настраивает логгер"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger

# Безопасное выполнение функций с логированием ошибок
def safe_execute(func, *args, default=None, log_errors=True, **kwargs):
    """Безопасно выполняет функцию, возвращая default_value при ошибке"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            logger = logging.getLogger(func.__module__ if hasattr(func, '__module__') else 'utils')
            logger.error(f"Error in {func.__name__}: {e}")
            logger.debug(traceback.format_exc())
        return default

# Очистка текста
def clean_text(text: str) -> str:
    """Очищает текст от HTML тегов и лишних пробелов"""
    if not text:
        return ""
    
    # Удаляем HTML теги
    text = re.sub(r'<[^>]+>', '', text)
    # Декодируем HTML сущности
    text = html.unescape(text)
    # Удаляем лишние пробелы и переносы
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

# Валидация URL
def is_valid_url(url: str) -> bool:
    """Проверяет валидность URL"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

# Нормализация URL
def normalize_url(base_url: str, url: str) -> str:
    """Нормализует относительный URL к абсолютному"""
    if not url:
        return base_url
    
    if url.startswith('http'):
        return url
    
    return urljoin(base_url, url)

# Безопасная загрузка изображения
def safe_download_image(url: str, timeout: int = 10) -> Optional[BytesIO]:
    """Безопасно загружает изображение"""
    if not is_valid_url(url):
        return None
    
    try:
        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()
        
        # Проверяем, что это изображение
        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            return None
        
        # Ограничиваем размер (5MB)
        content_length = response.headers.get('content-length')
        if content_length and int(content_length) > 5 * 1024 * 1024:
            return None
        
        image_data = BytesIO()
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                image_data.write(chunk)
        
        image_data.seek(0)
        return image_data
        
    except Exception as e:
        logging.getLogger('utils').error(f"Error downloading image {url}: {e}")
        return None

# Валидация данных игры
def validate_game_data(game: Dict[str, Any]) -> Dict[str, Any]:
    """Валидирует и очищает данные игры"""
    if not isinstance(game, dict):
        return {}
    
    validated = {}
    
    # Обязательные поля
    validated['title'] = clean_text(str(game.get('title', '')))[:200]
    if not validated['title']:
        return {}
    
    # Опциональные поля с очисткой (полное описание, без обрезки по длине)
    validated['description'] = clean_text(str(game.get('description', '')))
    validated['rating'] = clean_text(str(game.get('rating', 'N/A')))[:10]
    validated['url'] = normalize_url('https://asst2game.ru', str(game.get('url', '')))
    validated['image_url'] = normalize_url(validated['url'], str(game.get('image_url', '')))
    validated['release_date'] = clean_text(str(game.get('release_date', '')))[:20]
    
    # Жанры - список строк
    genres = game.get('genres', [])
    if isinstance(genres, list):
        validated['genres'] = [clean_text(str(g))[:50] for g in genres if g and clean_text(str(g))]
    else:
        validated['genres'] = []
    
    # Скриншоты - список валидных URL
    screenshots = game.get('screenshots', [])
    if isinstance(screenshots, list):
        validated['screenshots'] = [
            normalize_url(validated['url'], str(s)) 
            for s in screenshots 
            if s and is_valid_url(normalize_url(validated['url'], str(s)))
        ]
    else:
        validated['screenshots'] = []
    
    return validated

# Извлечение рейтинга
def extract_rating(text: str) -> str:
    """Извлекает рейтинг из текста и возвращает в формате X/100"""
    if not text:
        return "N/A"
    
    # Ищем рейтинг в разных форматах
    patterns = [
        r'(\d+\.?\d*)\s*/\s*100',  # X/100
        r'(\d+\.?\d*)\s*/\s*10',   # X/10
        r'(\d+\.?\d*)\s*%',        # X%
        r'(\d+\.?\d*)\s*из\s*100', # X из 100
        r'(\d+\.?\d*)\s*из\s*10',  # X из 10
        r'rating[:\s]*(\d+\.?\d*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            rating = float(match.group(1))
            
            # Если рейтинг в процентах или уже из 100, оставляем как есть
            if '/100' in pattern or '%' in pattern or 'из 100' in pattern:
                rating = max(0, min(100, rating))
                return f"{rating:.0f}/100"
            else:
                # Преобразуем из 10-балльной шкалы в 100-балльную
                rating = max(0, min(10, rating)) * 10
                return f"{rating:.0f}/100"
    
    return "N/A"

# Извлечение жанров
def extract_genres(text: str) -> List[str]:
    """Извлекает жанры из текста"""
    if not text:
        return []
    
    # Список известных жанров
    known_genres = [
        'Action', 'Adventure', 'RPG', 'Role-Playing', 'Strategy', 'Simulation',
        'Sports', 'Racing', 'Fighting', 'Platformer', 'Puzzle', 'Shooter',
        'Horror', 'Stealth', 'Survival', 'Music', 'Party', 'Educational',
        'Arcade', 'Casual', 'Indie', 'Multiplayer', 'Co-op', 'Single Player',
        'Open World', 'Fantasy', 'Sci-Fi', 'Historical', 'Modern', 'Post-Apocalyptic'
    ]
    
    genres = []
    text_lower = text.lower()
    
    # Ищем известные жанры
    for genre in known_genres:
        if genre.lower() in text_lower:
            genres.append(genre)
    
    # Ищем жанры через запятую или другие разделители
    if ',' in text or ';' in text or '/' in text:
        parts = re.split(r'[,;\/]', text)
        for part in parts:
            part_clean = clean_text(part)
            if len(part_clean) > 2 and len(part_clean) < 30:
                genres.append(part_clean)
    
    # Удаляем дубликаты и ограничиваем количество
    return list(dict.fromkeys(g for g in genres if g))[:5]

# Кэш для запросов
class SimpleCache:
    """Простой кэш в памяти"""
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.cache = {}
        self.access_times = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Получить значение из кэша"""
        if key in self.cache:
            self.access_times[key] = time.time()
            return self.cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Сохранить значение в кэш"""
        # Удаляем старые элементы если кэш переполнен
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.access_times, key=self.access_times.get)
            del self.cache[oldest_key]
            del self.access_times[oldest_key]
        
        self.cache[key] = value
        self.access_times[key] = time.time()
    
    def clear(self) -> None:
        """Очистить кэш"""
        self.cache.clear()
        self.access_times.clear()

# Глобальный кэш
request_cache = SimpleCache(max_size=200)
