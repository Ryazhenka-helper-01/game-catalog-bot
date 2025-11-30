#!/usr/bin/env python3
"""
Блокировка для предотвращения запуска нескольких экземпляров бота
"""

import os
import sys
import fcntl
import time

class SingleInstance:
    def __init__(self, lock_file="/tmp/bot.lock"):
        self.lock_file = lock_file
        self.fp = None
        
        try:
            self.fp = open(self.lock_file, 'w')
            fcntl.flock(self.fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (IOError, OSError):
            # Не удалось получить блокировку - другой экземпляр уже запущен
            print("Another bot instance is already running. Exiting...")
            sys.exit(1)
        except Exception as e:
            # fcntl может не работать на всех системах
            print(f"Warning: Could not create lock file: {e}")
            pass
    
    def __del__(self):
        if self.fp:
            try:
                fcntl.flock(self.fp.fileno(), fcntl.LOCK_UN)
                self.fp.close()
                os.unlink(self.lock_file)
            except:
                pass

# Альтернативная реализация для систем без fcntl
import tempfile
import atexit

class SimpleSingleInstance:
    def __init__(self):
        self.lock_dir = tempfile.gettempdir()
        self.lock_file = os.path.join(self.lock_dir, "game_bot_single_instance.lock")
        
        try:
            # Проверяем существует ли файл блокировки
            if os.path.exists(self.lock_file):
                # Читаем PID из файла
                with open(self.lock_file, 'r') as f:
                    try:
                        pid = int(f.read().strip())
                        # Проверяем жив ли процесс
                        try:
                            os.kill(pid, 0)
                            print(f"Bot instance with PID {pid} is already running. Exiting...")
                            sys.exit(1)
                        except OSError:
                            # Процесс не существует, удаляем старый файл
                            pass
                    except ValueError:
                        pass
                
                # Удаляем старый файл блокировки
                os.unlink(self.lock_file)
            
            # Создаем новый файл блокировки с текущим PID
            with open(self.lock_file, 'w') as f:
                f.write(str(os.getpid()))
            
            # Регистрируем удаление файла при выходе
            atexit.register(self.cleanup)
            
        except Exception as e:
            print(f"Warning: Could not create simple lock: {e}")
    
    def cleanup(self):
        try:
            if os.path.exists(self.lock_file):
                os.unlink(self.lock_file)
        except:
            pass

# Используем простую блокировку
def ensure_single_instance():
    try:
        return SimpleSingleInstance()
    except Exception as e:
        print(f"Warning: Single instance lock failed: {e}")
        return None
