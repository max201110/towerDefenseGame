from flask import Flask, render_template, send_from_directory, jsonify, request
import os
import json
import random
import math
from enum import Enum

app = Flask(__name__)

GRID_SIZE = 30
GRID_WIDTH = 35
GRID_HEIGHT = 18
CANVAS_WIDTH = GRID_WIDTH * GRID_SIZE
CANVAS_HEIGHT = GRID_HEIGHT * GRID_SIZE

class EnemyType(Enum):
    NORMAL = 1
    FAST = 2
    TANK = 3
    BOSS = 4
    FLYING = 5
    STEALTH = 6
    HEALER = 7
    SWARM = 8

game_state = {
    'towers': [], 'enemies': [], 'current_wave': 0,
    'lives': 30, 'money': 300, 'score': 0,
    'is_running': False, 'selected_tower': None,
    'wave_timer': 0, 'wave_interval': 200,
    'enemy_spawn_timer': 0, 'enemy_spawn_interval': 12,
    'current_wave_enemies': 0, 'wave_enemies_count': 0,
    'enemy_types': [], 'game_over': False
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'tower-defense', 'version': '1.0'})

@app.route('/game_state')
def get_game_state():
    return jsonify(game_state)

@app.route('/start_game', methods=['POST'])
def start_game():
    try:
        game_state['is_running'] = True
        game_state['selected_tower'] = 'ARROW'
        game_state['current_wave'] = 0
        game_state['lives'] = 30
        game_state['money'] = 300
        game_state['score'] = 0
        game_state['towers'] = []
        game_state['enemies'] = []
        game_state['wave_timer'] = 0
        game_state['enemy_spawn_timer'] = 0
        game_state['current_wave_enemies'] = 0
        game_state['wave_enemies_count'] = 0
        game_state['game_over'] = False
        return jsonify({'status': 'success', 'message': 'Game started'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/place_tower', methods=['POST'])
def place_tower():
    data = request.get_json()
    tower_type = data.get('type')
    x = data.get('x')
    y = data.get('y')

    if not is_valid_position(x, y):
        return jsonify({'status': 'error', 'message': 'Invalid position'})

    cost = get_tower_cost(tower_type)
    if game_state['money'] < cost:
        return jsonify({'status': 'error', 'message': 'Not enough money'})

    game_state['towers'].append({
        'type': tower_type, 'x': x, 'y': y,
        'level': 1, 'target': None, 'cooldown': 0,
        'damage': get_tower_damage(tower_type),
        'attack_speed': get_tower_attack_speed(tower_type),
        'range': get_tower_range(tower_type)
    })
    game_state['money'] -= cost

    return jsonify({'status': 'success', 'message': 'Tower placed'})

@app.route('/sell_tower', methods=['POST'])
def sell_tower():
    data = request.get_json()
    x, y = data.get('x'), data.get('y')

    for i, tower in enumerate(game_state['towers']):
        if tower['x'] == x and tower['y'] == y:
            sell_price = int(get_tower_cost(tower['type']) * 0.5 * tower['level'])
            game_state['money'] += sell_price
            game_state['towers'].pop(i)
            return jsonify({'status': 'success', 'message': f'Sold for {sell_price}'})

    return jsonify({'status': 'error', 'message': 'No tower here'})

@app.route('/upgrade_tower', methods=['POST'])
def upgrade_tower():
    data = request.get_json()
    x, y = data.get('x'), data.get('y')

    for tower in game_state['towers']:
        if tower['x'] == x and tower['y'] == y:
            cost = int(get_tower_cost(tower['type']) * 0.6 * tower['level'])
            if game_state['money'] < cost:
                return jsonify({'status': 'error', 'message': f'Need {cost} gold'})
            game_state['money'] -= cost
            tower['level'] += 1
            tower['damage'] = int(tower['damage'] * 1.4)
            tower['range'] = round(tower['range'] * 1.1, 1)
            return jsonify({'status': 'success', 'level': tower['level']})

    return jsonify({'status': 'error', 'message': 'No tower here'})

@app.route('/update_game', methods=['POST'])
def update_game():
    if not game_state['is_running'] or game_state['game_over']:
        return jsonify(game_state)

    game_state['wave_timer'] += 1
    game_state['enemy_spawn_timer'] += 1

    # Start new wave when timer expires
    if game_state['wave_timer'] >= game_state['wave_interval']:
        start_new_wave()
        game_state['wave_timer'] = 0

    # Spawn enemies
    if (game_state['current_wave_enemies'] < game_state['wave_enemies_count'] and
            game_state['enemy_spawn_timer'] >= game_state['enemy_spawn_interval']):
        spawn_enemy()
        game_state['enemy_spawn_timer'] = 0

    update_enemies()
    update_towers()

    if game_state['lives'] <= 0:
        game_state['lives'] = 0
        game_state['is_running'] = False
        game_state['game_over'] = True

    return jsonify(game_state)

@app.route('/get_paths')
def get_paths_api():
    return jsonify(get_paths())

def start_new_wave():
    w = game_state['current_wave'] + 1
    if w <= 5:
        game_state['wave_enemies_count'] = 10 + w
        game_state['enemy_types'] = ['NORMAL', 'FAST']
    elif w <= 10:
        game_state['wave_enemies_count'] = 12 + w
        game_state['enemy_types'] = ['NORMAL', 'FAST', 'FLYING', 'TANK']
    elif w <= 15:
        game_state['wave_enemies_count'] = 15 + w
        game_state['enemy_types'] = ['NORMAL', 'FAST', 'FLYING', 'TANK', 'STEALTH', 'HEALER']
    elif w <= 20:
        game_state['wave_enemies_count'] = 18 + w
        game_state['enemy_types'] = ['NORMAL', 'FAST', 'FLYING', 'TANK', 'STEALTH', 'HEALER', 'BOSS']
    else:
        game_state['wave_enemies_count'] = 20 + w
        game_state['enemy_types'] = [e.name for e in EnemyType]

    game_state['current_wave'] = w
    game_state['current_wave_enemies'] = 0

def spawn_enemy():
    if game_state['current_wave_enemies'] >= game_state['wave_enemies_count']:
        return

    if game_state['current_wave'] > 6 and random.random() < 0.15:
        etype = 'BOSS'
    else:
        etype = random.choice(game_state['enemy_types'])

    starts = [(0, 4), (0, 12), (34, 8), (34, 16), (17, 0), (0, 0), (34, 0)]
    sp = random.choice(starts)
    paths = get_paths()
    enemy = create_enemy(etype, paths[starts.index(sp)])
    enemy['x'] = sp[0] + random.uniform(-0.1, 0.1)
    enemy['y'] = sp[1] + random.uniform(-0.1, 0.1)
    game_state['enemies'].append(enemy)
    game_state['current_wave_enemies'] += 1

    if etype == 'HEALER':
        for _ in range(5):
            sw = create_enemy('SWARM', paths[starts.index(sp)])
            sw['x'] = sp[0] + random.uniform(-0.1, 0.1)
            sw['y'] = sp[1] + random.uniform(-0.1, 0.1)
            game_state['enemies'].append(sw)
            game_state['current_wave_enemies'] += 1

def create_enemy(etype, path):
    base_hp, base_spd, base_rew = 100, 0.05, 10
    table = {
        'NORMAL': (1.0, 1.0, 1.0), 'FAST': (0.7, 1.5, 1.2),
        'TANK': (2.5, 0.7, 1.5), 'BOSS': (5.0, 0.8, 3.0),
        'FLYING': (1.2, 1.2, 1.3), 'STEALTH': (1.5, 1.1, 1.4),
        'HEALER': (1.8, 0.9, 1.6), 'SWARM': (0.5, 1.3, 0.8),
    }
    hm, sm, rm = table.get(etype, (1.0, 1.0, 1.0))
    wm = 1 + (game_state['current_wave'] - 1) * 0.15

    return {
        'type': etype,
        'health': base_hp * hm * wm, 'max_health': base_hp * hm * wm,
        'speed': base_spd * sm, 'reward': int(base_rew * rm * wm),
        'path': path, 'path_index': 0, 'frozen': False,
        'poisoned': False, 'poison_duration': 0, 'poison_damage': 0,
        'stealth_timer': 0, 'stealth': False, 'heal_cooldown': 0
    }

def update_enemies():
    for enemy in game_state['enemies'][:]:
        if enemy['frozen']:
            enemy['frozen'] = False

        if enemy['poisoned']:
            enemy['health'] -= enemy['poison_damage']
            enemy['poison_duration'] -= 1
            if enemy['poison_duration'] <= 0:
                enemy['poisoned'] = False

        # Healer: heal nearby wounded enemies
        if enemy['type'] == 'HEALER' and enemy['heal_cooldown'] <= 0:
            for other in game_state['enemies']:
                if other is not enemy and other['health'] < other['max_health']:
                    other['health'] = min(other['max_health'], other['health'] + 15)
            enemy['heal_cooldown'] = 90
        enemy['heal_cooldown'] = max(0, enemy['heal_cooldown'] - 1)

        # Stealth: toggle every 120 frames (~2s visible, ~2s invisible)
        if enemy['type'] == 'STEALTH':
            enemy['stealth_timer'] += 1
            if enemy['stealth_timer'] >= 120:
                enemy['stealth_timer'] = 0
                enemy['stealth'] = not enemy['stealth']

        if enemy['path_index'] < len(enemy['path']) - 1:
            tx, ty = enemy['path'][enemy['path_index'] + 1]
            dx, dy = tx - enemy['x'], ty - enemy['y']
            dist = math.sqrt(dx * dx + dy * dy)

            if dist < enemy['speed']:
                enemy['path_index'] += 1
                enemy['x'], enemy['y'] = tx, ty
            else:
                spd = enemy['speed'] * (1.0 + random.uniform(-0.1, 0.1))
                enemy['x'] += dx * spd / dist
                enemy['y'] += dy * spd / dist
        else:
            game_state['lives'] -= 1
            if enemy in game_state['enemies']:
                game_state['enemies'].remove(enemy)

def update_towers():
    for tower in game_state['towers']:
        if tower['cooldown'] > 0:
            tower['cooldown'] -= 1
            continue

        if tower['type'] == 'SUPPORT':
            # FIX: Only buff once per cooldown, not every frame (was infinite buff bug)
            for other in game_state['towers']:
                if other is tower:
                    continue
                dx = other['x'] - tower['x']
                dy = other['y'] - tower['y']
                if math.sqrt(dx * dx + dy * dy) <= tower['range']:
                    other['damage'] = int(other['damage'] * 1.25)
            tower['cooldown'] = 120  # Buff every 120 frames (~2 seconds)
            continue

        if not tower['target'] or tower['target'] not in game_state['enemies']:
            tower['target'] = None
            min_d = float('inf')
            for enemy in game_state['enemies']:
                if enemy['stealth'] and tower['type'] != 'SNIPER':
                    continue
                dx = enemy['x'] - tower['x']
                dy = enemy['y'] - tower['y']
                d = math.sqrt(dx * dx + dy * dy)
                if d <= tower['range'] and d < min_d:
                    tower['target'] = enemy
                    min_d = d

        if tower['target']:
            dx = tower['target']['x'] - tower['x']
            dy = tower['target']['y'] - tower['y']
            if math.sqrt(dx * dx + dy * dy) > tower['range']:
                tower['target'] = None
                continue

            dmg = tower['damage']
            if tower['type'] == 'SNIPER':
                dmg = int(dmg * (2 if random.random() < 0.3 else 1))

            if tower['type'] == 'CANNON':
                for enemy in game_state['enemies'][:]:
                    ex = enemy['x'] - tower['x']
                    ey = enemy['y'] - tower['y']
                    if math.sqrt(ex * ex + ey * ey) <= 1.5:
                        enemy['health'] -= dmg
                        if enemy['health'] <= 0:
                            kill_enemy(enemy)
            elif tower['type'] == 'ICE':
                tower['target']['frozen'] = True
                tower['target']['health'] -= dmg
                if tower['target']['health'] <= 0:
                    kill_enemy(tower['target'])
                    tower['target'] = None
            elif tower['type'] == 'POISON':
                tower['target']['poisoned'] = True
                tower['target']['poison_duration'] = 5
                tower['target']['poison_damage'] = dmg
                tower['target']['health'] -= dmg
                if tower['target']['health'] <= 0:
                    kill_enemy(tower['target'])
                    tower['target'] = None
            else:
                tower['target']['health'] -= dmg
                if tower['target']['health'] <= 0:
                    kill_enemy(tower['target'])
                    tower['target'] = None

            tower['cooldown'] = tower['attack_speed']

def kill_enemy(enemy):
    if enemy in game_state['enemies']:
        game_state['money'] += enemy['reward']
        game_state['score'] += enemy['reward']
        game_state['enemies'].remove(enemy)

def get_tower_damage(t):
    return {'ARROW': 30, 'CANNON': 75, 'MAGIC': 25, 'LASER': 45,
            'ICE': 15, 'POISON': 20, 'SNIPER': 100, 'SUPPORT': 0}.get(t, 30)

def get_tower_attack_speed(t):
    return {'ARROW': 20, 'CANNON': 30, 'MAGIC': 15, 'LASER': 25,
            'ICE': 27, 'POISON': 20, 'SNIPER': 40, 'SUPPORT': 120}.get(t, 20)

def get_tower_range(t):
    return {'ARROW': 3, 'CANNON': 2, 'MAGIC': 3, 'LASER': 4,
            'ICE': 3, 'POISON': 3, 'SNIPER': 5, 'SUPPORT': 3}.get(t, 3)

def get_tower_cost(t):
    return {'ARROW': 100, 'CANNON': 200, 'MAGIC': 150, 'LASER': 250,
            'ICE': 175, 'POISON': 225, 'SNIPER': 300, 'SUPPORT': 275}.get(t, 100)

def is_valid_position(x, y):
    if not (0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT):
        return False
    for path in get_paths():
        for px, py in path:
            if abs(px - x) < 1 and abs(py - y) < 1:
                return False
    for tower in game_state['towers']:
        if tower['x'] == x and tower['y'] == y:
            return False
    return True

def get_paths():
    paths = []

    p1 = [(0, 4)] + [(x, 4) for x in range(1, 12)]
    p1 += [(11, y) for y in range(5, 8)]
    p1 += [(x, 7) for x in range(10, -1, -1)]
    p1 += [(0, y) for y in range(6, 3, -1)]
    p1 += [(x, 4) for x in range(1, 20)]
    paths.append(p1)

    p2 = [(0, 12)] + [(x, 12) for x in range(1, 15)]
    p2 += [(14, y) for y in range(11, 7, -1)]
    p2 += [(x, 9) for x in range(15, 25)]
    p2 += [(24, y) for y in range(10, 13)]
    p2 += [(x, 12) for x in range(23, 17, -1)]
    paths.append(p2)

    p3 = [(34, 8)] + [(x, 8) for x in range(33, 27, -1)]
    p3 += [(28, y) for y in range(9, 15)]
    p3 += [(x, 14) for x in range(29, 32)]
    paths.append(p3)

    p4 = [(34, 16)] + [(x, 16) for x in range(33, 27, -1)]
    p4 += [(28, y) for y in range(15, 11, -1)]
    p4 += [(x, 12) for x in range(27, 21, -1)]
    paths.append(p4)

    p5 = [(17, 0)] + [(17, y) for y in range(1, 6)]
    p5 += [(x, 5) for x in range(16, 12, -1)]
    p5 += [(13, y) for y in range(6, 9)]
    p5 += [(x, 8) for x in range(14, 17)]
    paths.append(p5)

    p6 = [(0, 0)] + [(x, x) for x in range(1, 8)]
    p6 += [(x, 7) for x in range(8, 15)]
    p6 += [(14, y) for y in range(8, 15)]
    p6 += [(x, 14) for x in range(15, 22)]
    paths.append(p6)

    p7 = [(34, 0)] + [(x, 34 - x) for x in range(33, 25, -1)]
    p7 += [(x, 8) for x in range(26, 18, -1)]
    p7 += [(19, y) for y in range(9, 16)]
    p7 += [(x, 15) for x in range(18, 10, -1)]
    paths.append(p7)

    return paths

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory('assets', filename)

@app.route('/game_images/<path:filename>')
def serve_game_images(filename):
    return send_from_directory('game_images', filename)

@app.route('/tower_images/<path:filename>')
def serve_tower_images(filename):
    return send_from_directory('tower_images', filename)

if __name__ == '__main__':
    if not os.path.exists('templates'):
        os.makedirs('templates')
    # FIX: Disable debug mode for production safety (was True, exposes debugger)
    app.run(host='0.0.0.0', port=5004, debug=False)


