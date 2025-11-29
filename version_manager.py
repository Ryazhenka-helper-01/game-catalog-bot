#!/usr/bin/env python3
"""
Менеджер версий бота - автоматический инкремент
"""

import re
import json
from datetime import datetime

class VersionManager:
    def __init__(self):
        self.version_file = 'bot_version.json'
        self.version_pattern = r'beta-(\d+)\.(\d+)\.(\d+)'
    
    def load_version(self):
        """Загрузка текущей версии"""
        try:
            with open(self.version_file, 'r') as f:
                data = json.load(f)
                return data.get('version', 'beta-1.1.1')
        except FileNotFoundError:
            return 'beta-1.1.1'
    
    def save_version(self, version):
        """Сохранение версии"""
        data = {
            'version': version,
            'updated': datetime.now().isoformat(),
            'history': self.get_history() + [version]
        }
        
        with open(self.version_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_history(self):
        """Получение истории версий"""
        try:
            with open(self.version_file, 'r') as f:
                data = json.load(f)
                return data.get('history', [])
        except FileNotFoundError:
            return []
    
    def increment_version(self, increment_type='patch'):
        """Инкремент версии
        
        increment_type:
        - major: beta-X.0.0 (редко)
        - minor: beta-X.Y.0 (новые функции)
        - patch: beta-X.Y.Z (исправления)
        """
        current = self.load_version()
        match = re.match(self.version_pattern, current)
        
        if not match:
            return current
        
        major, minor, patch = map(int, match.groups())
        
        if increment_type == 'major':
            major += 1
            minor = 0
            patch = 0
        elif increment_type == 'minor':
            minor += 1
            patch = 0
        else:  # patch
            patch += 1
        
        new_version = f'beta-{major}.{minor}.{patch}'
        self.save_version(new_version)
        
        return new_version
    
    def update_files(self, new_version):
        """Обновление версии во всех файлах"""
        import os
        
        files_to_update = [
            'main.py',
            'README.md',
            'requirements.txt'
        ]
        
        updated_files = []
        
        for filename in files_to_update:
            if os.path.exists(filename):
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Ищем старую версию и заменяем
                    old_version = self.load_version()
                    
                    # Регулярные выражения для поиска версий
                    patterns = [
                        rf'Версия.*?{re.escape(old_version)}',
                        rf'Version.*?{re.escape(old_version)}',
                        rf'beta-\d+\.\d+\.\d+',
                    ]
                    
                    updated = False
                    for pattern in patterns:
                        if re.search(pattern, content):
                            content = re.sub(pattern, new_version, content)
                            updated = True
                    
                    if updated:
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(content)
                        updated_files.append(filename)
                        print(f"Updated version in {filename}: {old_version} -> {new_version}")
                
                except Exception as e:
                    print(f"Error updating {filename}: {e}")
        
        return updated_files
    
    def get_changelog_entry(self, version, changes):
        """Создание записи в changelog"""
        date = datetime.now().strftime('%Y-%m-%d')
        entry = f"## {version} - {date}\n\n"
        
        for change in changes:
            entry += f"- {change}\n"
        
        entry += "\n"
        return entry
    
    def update_changelog(self, version, changes):
        """Обновление CHANGELOG.md"""
        changelog_file = 'CHANGELOG.md'
        
        entry = self.get_changelog_entry(version, changes)
        
        try:
            if os.path.exists(changelog_file):
                with open(changelog_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Вставляем новую запись после заголовка
                lines = content.split('\n')
                insert_index = 0
                
                for i, line in enumerate(lines):
                    if line.startswith('# Changelog') or line.startswith('# CHANGELOG'):
                        insert_index = i + 2
                        break
                
                lines.insert(insert_index, entry)
                content = '\n'.join(lines)
            else:
                content = f"# Changelog\n\n{entry}"
            
            with open(changelog_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"Updated changelog with version {version}")
            
        except Exception as e:
            print(f"Error updating changelog: {e}")

def main():
    """Основная функция для управления версиями"""
    vm = VersionManager()
    
    print("Version Manager")
    print("=" * 40)
    
    current = vm.load_version()
    print(f"Current version: {current}")
    
    print("\nIncrement options:")
    print("1. Patch (beta-X.Y.Z+1) - fixes")
    print("2. Minor (beta-X.Y+1.0) - new features")
    print("3. Major (beta-X+1.0.0) - big changes")
    
    choice = input("\nChoose increment type (1/2/3): ").strip()
    
    increment_map = {
        '1': 'patch',
        '2': 'minor', 
        '3': 'major'
    }
    
    increment_type = increment_map.get(choice, 'patch')
    
    new_version = vm.increment_version(increment_type)
    print(f"\nNew version: {new_version}")
    
    # Обновляем файлы
    updated_files = vm.update_files(new_version)
    
    # Обновляем changelog
    changes = [
        "Updated bot functionality",
        "Fixed deployment issues",
        "Added new features"
    ]
    
    vm.update_changelog(new_version, changes)
    
    print(f"\nVersion updated successfully!")
    print(f"Updated files: {', '.join(updated_files)}")

if __name__ == "__main__":
    main()
