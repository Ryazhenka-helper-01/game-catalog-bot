#!/usr/bin/env python3
"""
Принудительное обновление Railway
"""

import os
import subprocess
from datetime import datetime

def force_railway_update():
    print("=" * 60)
    print("FORCE RAILWAY UPDATE")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")
    
    # 1. Проверяем статус
    print("1. CHECKING GIT STATUS:")
    result = subprocess.run(['git', 'status'], capture_output=True, text=True)
    print(result.stdout)
    
    # 2. Добавляем все файлы
    print("2. ADDING ALL FILES:")
    result = subprocess.run(['git', 'add', '.'], capture_output=True, text=True)
    print("Files added")
    
    # 3. Создаем новый коммит с триггером
    print("3. CREATING TRIGGER COMMIT:")
    commit_message = f"Railway deployment trigger {datetime.now().strftime('%Y%m%d_%H%M%S')}"
    result = subprocess.run(['git', 'commit', '-m', commit_message], capture_output=True, text=True)
    print(result.stdout)
    
    # 4. Push с принуждением
    print("4. FORCE PUSHING TO RAILWAY:")
    result = subprocess.run(['git', 'push', 'origin', 'main'], capture_output=True, text=True)
    print(result.stdout)
    
    if result.returncode == 0:
        print("✅ SUCCESS! Railway should update now")
        print("⏳ Wait 2-5 minutes for deployment")
        print("🔄 Check Railway dashboard for logs")
    else:
        print("❌ ERROR in push:")
        print(result.stderr)
    
    print("")
    print("NEXT STEPS:")
    print("1. Check Railway dashboard")
    print("2. Look for deployment logs")
    print("3. Wait 2-5 minutes")
    print("4. Test bot with /start")
    print("")
    
    print("RAILWAY DASHBOARD:")
    print("• railway.app/project")
    print("• railway.app/project/logs")
    print("• railway.app/project/services")

if __name__ == "__main__":
    force_railway_update()
