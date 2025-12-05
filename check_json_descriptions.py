import json

with open('all_switch_games_with_descriptions.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

game = data[0]
print('Sample from JSON:')
print(f'Title: {game["title"]}')
print(f'Description: {game["description"][:100]}...')
