from flask import Flask, render_template, send_from_directory, jsonify, request
import os
import json
import random
import math
from enum import Enum

app = Flask(__name__)

# 游戏常量
GRID_SIZE = 30
GRID_WIDTH = 35
GRID_HEIGHT = 18
CANVAS_WIDTH = GRID_WIDTH * GRID_SIZE
CANVAS_HEIGHT = GRID_HEIGHT * GRID_SIZE

class EnemyType(Enum):
    NORMAL = 1    # 普通敌人：基础属性
    FAST = 2      # 快速敌人：移动速度快
    TANK = 3      # 坦克敌人：生命值高
    BOSS = 4      # Boss敌人：全属性高
    FLYING = 5    # 飞行敌人：无视地形
    STEALTH = 6   # 隐身敌人：周期性隐身
    HEALER = 7    # 治疗者：治疗其他敌人
    SWARM = 8     # 集群敌人：数量多

# 游戏状态
game_state = {
    'towers': [],
    'enemies': [],
    'current_wave': 0,
    'lives': 30,
    'money': 300,
    'score': 0,
    'is_running': False,
    'selected_tower': None,
    'wave_timer': 0,
    'wave_interval': 200,
    'enemy_spawn_timer': 0,
    'enemy_spawn_interval': 12,
    'current_wave_enemies': 0,
    'wave_enemies_count': 0,
    'enemy_types': []
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/game_state')
def get_game_state():
    return jsonify(game_state)

@app.route('/start_game')
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
        return {'status': 'success', 'message': '游戏已启动'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

@app.route('/place_tower', methods=['POST'])
def place_tower():
    data = request.get_json()
    tower_type = data.get('type')
    x = data.get('x')
    y = data.get('y')
    
    # 检查位置是否有效
    if not is_valid_position(x, y):
        return {'status': 'error', 'message': '无效的位置'}
    
    # 检查金钱是否足够
    cost = get_tower_cost(tower_type)
    if game_state['money'] < cost:
        return {'status': 'error', 'message': '金钱不足'}
    
    # 添加塔
    game_state['towers'].append({
        'type': tower_type,
        'x': x,
        'y': y,
        'level': 1,
        'target': None,
        'cooldown': 0,
        'damage': get_tower_damage(tower_type),
        'attack_speed': get_tower_attack_speed(tower_type),
        'range': get_tower_range(tower_type)
    })
    game_state['money'] -= cost
    
    return {'status': 'success', 'message': '塔已放置'}

@app.route('/update_game', methods=['POST'])
def update_game():
    if not game_state['is_running']:
        return jsonify({'status': 'error', 'message': '游戏未开始'})
    
    # 更新波次计时器
    game_state['wave_timer'] += 1
    game_state['enemy_spawn_timer'] += 1
    
    # 检查是否需要开始新的波次
    if game_state['wave_timer'] >= game_state['wave_interval'] and not game_state['enemies']:
        start_new_wave()
        game_state['wave_timer'] = 0
    
    # 在当前波次中生成敌人
    if (game_state['current_wave_enemies'] < game_state['wave_enemies_count'] and 
        game_state['enemy_spawn_timer'] >= game_state['enemy_spawn_interval']):
        spawn_enemy()
        game_state['enemy_spawn_timer'] = 0
    
    # 更新敌人位置和状态
    update_enemies()
    
    # 更新塔的攻击
    update_towers()
    
    return jsonify(game_state)

def start_new_wave():
    game_state['current_wave'] += 1
    
    # 根据波数设置敌人数量和类型
    if game_state['current_wave'] <= 5:
        game_state['wave_enemies_count'] = 10 + game_state['current_wave']
        game_state['enemy_types'] = ['NORMAL', 'FAST']
    elif game_state['current_wave'] <= 10:
        game_state['wave_enemies_count'] = 12 + game_state['current_wave']
        game_state['enemy_types'] = ['NORMAL', 'FAST', 'FLYING', 'TANK']
    elif game_state['current_wave'] <= 15:
        game_state['wave_enemies_count'] = 15 + game_state['current_wave']
        game_state['enemy_types'] = ['NORMAL', 'FAST', 'FLYING', 'TANK', 'STEALTH', 'HEALER']
    elif game_state['current_wave'] <= 20:
        game_state['wave_enemies_count'] = 18 + game_state['current_wave']
        game_state['enemy_types'] = ['NORMAL', 'FAST', 'FLYING', 'TANK', 'STEALTH', 'HEALER', 'BOSS']
    else:
        game_state['wave_enemies_count'] = 20 + game_state['current_wave']
        game_state['enemy_types'] = [e.name for e in EnemyType]
    
    game_state['current_wave_enemies'] = 0

def spawn_enemy():
    if game_state['current_wave_enemies'] < game_state['wave_enemies_count']:
        # 选择敌人类型
        if game_state['current_wave'] > 6 and random.random() < 0.5:
            enemy_type = 'BOSS'
        else:
            enemy_type = random.choice(game_state['enemy_types'])
        
        # 随机选择起点和对应的路径
        start_points = [
            (0, 4),    # 左上
            (0, 12),   # 左下
            (34, 8),   # 右边中间
            (34, 16),  # 右边下方
            (17, 0),   # 上方
            (0, 0),    # 左上方
            (34, 0)    # 右上方
        ]
        start_point = random.choice(start_points)
        
        # 根据起点选择对应的路径
        path_index = start_points.index(start_point)
        enemy_path = get_paths()[path_index]
        
        # 创建敌人
        enemy = create_enemy(enemy_type, enemy_path)
        enemy['x'] = start_point[0] + random.uniform(-0.1, 0.1)
        enemy['y'] = start_point[1] + random.uniform(-0.1, 0.1)
        game_state['enemies'].append(enemy)
        game_state['current_wave_enemies'] += 1
        
        # 如果是治疗者，额外生成集群敌人
        if enemy_type == 'HEALER':
            for _ in range(8):
                swarm = create_enemy('SWARM', enemy_path)
                swarm['x'] = start_point[0] + random.uniform(-0.1, 0.1)
                swarm['y'] = start_point[1] + random.uniform(-0.1, 0.1)
                game_state['enemies'].append(swarm)
                game_state['current_wave_enemies'] += 1

def create_enemy(enemy_type, path):
    # 基础属性
    base_health = 100
    base_speed = 0.05
    base_reward = 10
    
    # 根据类型调整属性
    if enemy_type == 'NORMAL':
        health = base_health
        speed = base_speed
        reward = base_reward
    elif enemy_type == 'FAST':
        health = base_health * 0.7
        speed = base_speed * 1.5
        reward = base_reward * 1.2
    elif enemy_type == 'TANK':
        health = base_health * 2.5
        speed = base_speed * 0.7
        reward = base_reward * 1.5
    elif enemy_type == 'BOSS':
        health = base_health * 5
        speed = base_speed * 0.8
        reward = base_reward * 3
    elif enemy_type == 'FLYING':
        health = base_health * 1.2
        speed = base_speed * 1.2
        reward = base_reward * 1.3
    elif enemy_type == 'STEALTH':
        health = base_health * 1.5
        speed = base_speed * 1.1
        reward = base_reward * 1.4
    elif enemy_type == 'HEALER':
        health = base_health * 1.8
        speed = base_speed * 0.9
        reward = base_reward * 1.6
    else:  # SWARM
        health = base_health * 0.5
        speed = base_speed * 1.3
        reward = base_reward * 0.8
    
    # 根据波数增加属性
    wave_multiplier = 1 + (game_state['current_wave'] - 1) * 0.15
    health *= wave_multiplier
    reward *= wave_multiplier
    
    return {
        'type': enemy_type,
        'health': health,
        'max_health': health,
        'speed': speed,
        'reward': reward,
        'path': path,
        'path_index': 0,
        'frozen': False,
        'poisoned': False,
        'poison_duration': 0,
        'poison_damage': 0,
        'stealth': False,
        'heal_cooldown': 0
    }

def update_enemies():
    for enemy in game_state['enemies'][:]:
        # 处理特殊状态
        if enemy['frozen']:
            enemy['speed'] = 0
            enemy['frozen'] = False
        if enemy['poisoned']:
            enemy['health'] -= enemy['poison_damage']
            enemy['poison_duration'] -= 1
            if enemy['poison_duration'] <= 0:
                enemy['poisoned'] = False
        
        # 处理治疗者
        if enemy['type'] == 'HEALER' and enemy['heal_cooldown'] <= 0:
            for other_enemy in game_state['enemies']:
                if other_enemy != enemy and other_enemy['health'] < other_enemy['max_health']:
                    other_enemy['health'] = min(other_enemy['max_health'], other_enemy['health'] + 10)
            enemy['heal_cooldown'] = 60
        enemy['heal_cooldown'] = max(0, enemy['heal_cooldown'] - 1)
        
        # 处理隐身敌人
        if enemy['type'] == 'STEALTH':
            enemy['stealth'] = not enemy['stealth']
        
        # 更新位置
        if enemy['path_index'] < len(enemy['path']) - 1:
            target_x, target_y = enemy['path'][enemy['path_index'] + 1]
            dx = target_x - enemy['x']
            dy = target_y - enemy['y']
            distance = math.sqrt(dx * dx + dy * dy)
            
            if distance < enemy['speed']:
                enemy['path_index'] += 1
                enemy['x'] = target_x
                enemy['y'] = target_y
            else:
                move_speed = enemy['speed'] * (1.0 + random.uniform(-0.1, 0.1))
                enemy['x'] += dx * move_speed / distance
                enemy['y'] += dy * move_speed / distance
        else:
            game_state['lives'] -= 1
            game_state['enemies'].remove(enemy)
            if game_state['lives'] <= 0:
                game_state['is_running'] = False

def update_towers():
    for tower in game_state['towers']:
        if tower['cooldown'] > 0:
            tower['cooldown'] -= 1
            continue
        
        # 支援塔效果
        if tower['type'] == 'SUPPORT':
            for other_tower in game_state['towers']:
                if other_tower != tower:
                    dx = other_tower['x'] - tower['x']
                    dy = other_tower['y'] - tower['y']
                    distance = math.sqrt(dx * dx + dy * dy)
                    if distance <= tower['range']:
                        other_tower['damage'] *= 1.2
            continue
        
        # 寻找目标
        if not tower['target'] or tower['target'] not in game_state['enemies']:
            tower['target'] = None
            min_distance = float('inf')
            for enemy in game_state['enemies']:
                if enemy['stealth'] and tower['type'] != 'SNIPER':
                    continue
                dx = enemy['x'] - tower['x']
                dy = enemy['y'] - tower['y']
                distance = math.sqrt(dx * dx + dy * dy)
                if distance <= tower['range'] and distance < min_distance:
                    tower['target'] = enemy
                    min_distance = distance
        
        # 攻击目标
        if tower['target']:
            dx = tower['target']['x'] - tower['x']
            dy = tower['target']['y'] - tower['y']
            distance = math.sqrt(dx * dx + dy * dy)
            
            if distance <= tower['range']:
                if tower['type'] == 'CANNON':
                    for enemy in game_state['enemies'][:]:
                        ex = enemy['x'] - tower['x']
                        ey = enemy['y'] - tower['y']
                        if math.sqrt(ex * ex + ey * ey) <= 1:
                            enemy['health'] -= tower['damage']
                            if enemy['health'] <= 0:
                                game_state['money'] += enemy['reward']
                                game_state['score'] += enemy['reward']
                                game_state['enemies'].remove(enemy)
                elif tower['type'] == 'SNIPER':
                    damage = tower['damage'] * (2 if random.random() < 0.3 else 1)
                    tower['target']['health'] -= damage
                    if tower['target']['health'] <= 0:
                        game_state['money'] += tower['target']['reward']
                        game_state['score'] += tower['target']['reward']
                        game_state['enemies'].remove(tower['target'])
                        tower['target'] = None
                elif tower['type'] == 'ICE':
                    tower['target']['frozen'] = True
                    tower['target']['health'] -= tower['damage']
                    if tower['target']['health'] <= 0:
                        game_state['money'] += tower['target']['reward']
                        game_state['score'] += tower['target']['reward']
                        game_state['enemies'].remove(tower['target'])
                        tower['target'] = None
                elif tower['type'] == 'POISON':
                    tower['target']['poisoned'] = True
                    tower['target']['poison_duration'] = 5
                    tower['target']['poison_damage'] = tower['damage']
                    tower['target']['health'] -= tower['damage']
                    if tower['target']['health'] <= 0:
                        game_state['money'] += tower['target']['reward']
                        game_state['score'] += tower['target']['reward']
                        game_state['enemies'].remove(tower['target'])
                        tower['target'] = None
                else:
                    tower['target']['health'] -= tower['damage']
                    if tower['target']['health'] <= 0:
                        game_state['money'] += tower['target']['reward']
                        game_state['score'] += tower['target']['reward']
                        game_state['enemies'].remove(tower['target'])
                        tower['target'] = None
                
                tower['cooldown'] = tower['attack_speed']

def get_tower_damage(tower_type):
    damages = {
        'ARROW': 30,
        'CANNON': 75,
        'MAGIC': 25,
        'LASER': 45,
        'ICE': 15,
        'POISON': 20,
        'SNIPER': 100,
        'SUPPORT': 0
    }
    return damages.get(tower_type, 30)

def get_tower_attack_speed(tower_type):
    speeds = {
        'ARROW': 20,
        'CANNON': 30,
        'MAGIC': 15,
        'LASER': 25,
        'ICE': 27,
        'POISON': 20,
        'SNIPER': 40,
        'SUPPORT': 0
    }
    return speeds.get(tower_type, 20)

def get_tower_range(tower_type):
    ranges = {
        'ARROW': 3,
        'CANNON': 2,
        'MAGIC': 3,
        'LASER': 4,
        'ICE': 3,
        'POISON': 3,
        'SNIPER': 5,
        'SUPPORT': 3
    }
    return ranges.get(tower_type, 3)

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory('assets', filename)

@app.route('/game_images/<path:filename>')
def serve_game_images(filename):
    return send_from_directory('game_images', filename)

@app.route('/tower_images/<path:filename>')
def serve_tower_images(filename):
    return send_from_directory('tower_images', filename)

def is_valid_position(x, y):
    # 检查是否在网格范围内
    if not (0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT):
        return False
    
    # 检查是否在路径上
    for path in get_paths():
        for px, py in path:
            if abs(px - x) < 1 and abs(py - y) < 1:
                return False
    
    # 检查是否已有塔
    for tower in game_state['towers']:
        if tower['x'] == x and tower['y'] == y:
            return False
    
    return True

def get_tower_cost(tower_type):
    costs = {
        'ARROW': 100,
        'CANNON': 200,
        'MAGIC': 150,
        'LASER': 250,
        'ICE': 175,
        'POISON': 225,
        'SNIPER': 300,
        'SUPPORT': 275
    }
    return costs.get(tower_type, 100)

def get_paths():
    paths = []
    
    # 第一条路径（左上到右中）
    path1 = []
    path1.append((0, 4))
    for x in range(1, 12):
        path1.append((x, 4))
    for y in range(5, 8):
        path1.append((11, y))
    for x in range(10, -1, -1):
        path1.append((x, 7))
    for y in range(6, 3, -1):
        path1.append((0, y))
    for x in range(1, 20):
        path1.append((x, 4))
    paths.append(path1)
    
    # 第二条路径（左下到右上）
    path2 = []
    path2.append((0, 12))
    for x in range(1, 15):
        path2.append((x, 12))
    for y in range(11, 8, -1):
        path2.append((14, y))
    for x in range(15, 25):
        path2.append((x, 9))
    for y in range(10, 13):
        path2.append((24, y))
    for x in range(23, 18, -1):
        path2.append((x, 12))
    paths.append(path2)
    
    # 第三条路径（右边到中间）
    path3 = []
    path3.append((34, 8))
    for x in range(33, 28, -1):
        path3.append((x, 8))
    for y in range(9, 15):
        path3.append((28, y))
    for x in range(29, 32):
        path3.append((x, 14))
    paths.append(path3)
    
    # 第四条路径（右边到左下）
    path4 = []
    path4.append((34, 16))
    for x in range(33, 28, -1):
        path4.append((x, 16))
    for y in range(15, 12, -1):
        path4.append((28, y))
    for x in range(27, 22, -1):
        path4.append((x, 12))
    paths.append(path4)
    
    # 第五条路径（上方到中间）
    path5 = []
    path5.append((17, 0))
    for y in range(1, 6):
        path5.append((17, y))
    for x in range(16, 13, -1):
        path5.append((x, 5))
    for y in range(6, 9):
        path5.append((13, y))
    for x in range(14, 17):
        path5.append((x, 8))
    paths.append(path5)
    
    # 第六条路径（左上方到右下方）
    path6 = []
    path6.append((0, 0))
    for x in range(1, 8):
        path6.append((x, x))
    for x in range(8, 15):
        path6.append((x, 7))
    for y in range(8, 15):
        path6.append((14, y))
    for x in range(15, 22):
        path6.append((x, 14))
    paths.append(path6)
    
    # 第七条路径（右上方到左下方）
    path7 = []
    path7.append((34, 0))
    for x in range(33, 26, -1):
        path7.append((x, 34-x))
    for x in range(26, 19, -1):
        path7.append((x, 8))
    for y in range(9, 16):
        path7.append((19, y))
    for x in range(18, 11, -1):
        path7.append((x, 15))
    paths.append(path7)
    
    return paths

if __name__ == '__main__':
    # 确保templates目录存在
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # 创建index.html模板
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write('''
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>塔防游戏</title>
    <style>
        body {
            font-family: 'Arial', sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background: linear-gradient(135deg, #1a1a1a, #2a2a2a);
            color: #ffffff;
        }
        .container {
            text-align: center;
            padding: 2rem;
            background: rgba(0, 0, 0, 0.7);
            border-radius: 15px;
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.5);
        }
        h1 {
            font-size: 2.5rem;
            margin-bottom: 1.5rem;
            color: #ffd700;
        }
        .game-container {
            position: relative;
            margin: 20px auto;
        }
        canvas {
            border: 2px solid #ffd700;
            background: #1a1a1a;
        }
        .controls {
            margin-top: 20px;
            display: flex;
            justify-content: center;
            gap: 10px;
        }
        .tower-button {
            background: #ffd700;
            color: #000000;
            border: none;
            padding: 0.5rem 1rem;
            font-size: 1rem;
            border-radius: 5px;
            cursor: pointer;
            transition: transform 0.2s, background 0.2s;
        }
        .tower-button:hover {
            transform: scale(1.05);
            background: #ffed4a;
        }
        .tower-button.selected {
            background: #ffed4a;
            transform: scale(1.05);
        }
        .game-info {
            margin-top: 20px;
            display: flex;
            justify-content: space-around;
            font-size: 1.2rem;
        }
        .instructions {
            margin-top: 2rem;
            text-align: left;
            padding: 1rem;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>塔防游戏</h1>
        <div class="game-container">
            <canvas id="gameCanvas" width="1050" height="540"></canvas>
        </div>
        <div class="controls">
            <button class="tower-button" data-tower="ARROW">箭塔 (100)</button>
            <button class="tower-button" data-tower="CANNON">炮塔 (200)</button>
            <button class="tower-button" data-tower="MAGIC">魔法塔 (150)</button>
            <button class="tower-button" data-tower="LASER">激光塔 (250)</button>
            <button class="tower-button" data-tower="ICE">冰塔 (175)</button>
            <button class="tower-button" data-tower="POISON">毒塔 (225)</button>
            <button class="tower-button" data-tower="SNIPER">狙击塔 (300)</button>
            <button class="tower-button" data-tower="SUPPORT">支援塔 (275)</button>
        </div>
        <div class="game-info">
            <div>生命值: <span id="lives">30</span></div>
            <div>金钱: <span id="money">300</span></div>
            <div>分数: <span id="score">0</span></div>
            <div>波数: <span id="wave">0</span></div>
        </div>
        <div class="instructions">
            <h3>游戏说明：</h3>
            <p>1. 点击塔按钮选择要建造的塔</p>
            <p>2. 点击地图上的空地放置塔</p>
            <p>3. 阻止敌人到达终点</p>
            <p>4. 合理使用不同类型的防御塔来获得胜利</p>
        </div>
    </div>

    <script>
        // 游戏常量
        const GRID_SIZE = 30;
        const GRID_WIDTH = 35;
        const GRID_HEIGHT = 18;
        const CANVAS_WIDTH = GRID_WIDTH * GRID_SIZE;
        const CANVAS_HEIGHT = GRID_HEIGHT * GRID_SIZE;

        // 游戏状态
        let gameState = {
            towers: [],
            enemies: [],
            current_wave: 0,
            lives: 30,
            money: 300,
            score: 0,
            is_running: false,
            selected_tower: null,
            wave_timer: 0,
            wave_interval: 200,
            enemy_spawn_timer: 0,
            enemy_spawn_interval: 12,
            current_wave_enemies: 0,
            wave_enemies_count: 0
        };

        // 获取Canvas上下文
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');

        // 加载图片资源
        const towerImages = {};
        const enemyImages = {};
        const imageTypes = {
            'ARROW': '#3498db',
            'CANNON': '#e74c3c',
            'MAGIC': '#9b59b6',
            'LASER': '#f1c40f',
            'ICE': '#00bfff',
            'POISON': '#32cd32',
            'SNIPER': '#8b4513',
            'SUPPORT': '#ffd700'
        };

        // 初始化游戏
        function initGame() {
            // 加载图片资源
            loadImages();
            
            // 绑定事件监听器
            bindEvents();
            
            // 开始游戏循环
            gameLoop();
        }

        // 加载图片资源
        function loadImages() {
            // 这里可以加载实际的图片资源
            // 暂时使用颜色块代替
            Object.entries(imageTypes).forEach(([type, color]) => {
                towerImages[type] = createTowerImage(color);
            });
        }

        // 创建塔的图片
        function createTowerImage(color) {
            const img = document.createElement('canvas');
            img.width = GRID_SIZE;
            img.height = GRID_SIZE;
            const imgCtx = img.getContext('2d');
            
            // 绘制塔的形状
            imgCtx.fillStyle = color;
            imgCtx.beginPath();
            imgCtx.arc(GRID_SIZE/2, GRID_SIZE/2, GRID_SIZE/3, 0, Math.PI * 2);
            imgCtx.fill();
            
            return img;
        }

        // 绑定事件监听器
        function bindEvents() {
            // 塔按钮点击事件
            document.querySelectorAll('.tower-button').forEach(button => {
                button.addEventListener('click', () => {
                    const towerType = button.dataset.tower;
                    selectTower(towerType);
                });
            });

            // 画布点击事件
            canvas.addEventListener('click', (event) => {
                const rect = canvas.getBoundingClientRect();
                const x = Math.floor((event.clientX - rect.left) / GRID_SIZE);
                const y = Math.floor((event.clientY - rect.top) / GRID_SIZE);
                placeTower(x, y);
            });
        }

        // 选择塔
        function selectTower(towerType) {
            gameState.selected_tower = towerType;
            document.querySelectorAll('.tower-button').forEach(button => {
                button.classList.toggle('selected', button.dataset.tower === towerType);
            });
        }

        // 放置塔
        function placeTower(x, y) {
            if (!gameState.is_running || !gameState.selected_tower) return;

            fetch('/place_tower', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    type: gameState.selected_tower,
                    x: x,
                    y: y
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    updateGameState();
                } else {
                    alert(data.message);
                }
            });
        }

        // 更新游戏状态
        function updateGameState() {
            fetch('/update_game', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'error') {
                    console.error(data.message);
                    return;
                }
                gameState = data;
                updateUI();
            })
            .catch(error => {
                console.error('Error updating game state:', error);
            });
        }

        // 更新UI显示
        function updateUI() {
            document.getElementById('lives').textContent = gameState.lives;
            document.getElementById('money').textContent = gameState.money;
            document.getElementById('score').textContent = gameState.score;
            document.getElementById('wave').textContent = gameState.current_wave;
        }

        // 游戏主循环
        function gameLoop() {
            // 清空画布
            ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
            
            // 绘制游戏元素
            drawGrid();
            drawPaths();
            drawTowers();
            drawEnemies();
            
            // 更新游戏状态
            if (gameState.is_running) {
                updateGameState();
            }
            
            // 继续游戏循环
            requestAnimationFrame(gameLoop);
        }

        // 绘制网格
        function drawGrid() {
            ctx.strokeStyle = '#e0e0e0';
            ctx.lineWidth = 1;
            
            for (let x = 0; x < GRID_WIDTH; x++) {
                for (let y = 0; y < GRID_HEIGHT; y++) {
                    ctx.strokeRect(
                        x * GRID_SIZE,
                        y * GRID_SIZE,
                        GRID_SIZE,
                        GRID_SIZE
                    );
                }
            }
        }

        // 绘制路径
        function drawPaths() {
            ctx.strokeStyle = '#95a5a6';
            ctx.lineWidth = 3;
            
            // 获取路径数据
            const paths = getPaths();
            
            paths.forEach(path => {
                for (let i = 0; i < path.length - 1; i++) {
                    const [x1, y1] = path[i];
                    const [x2, y2] = path[i + 1];
                    
                    ctx.beginPath();
                    ctx.moveTo(
                        x1 * GRID_SIZE + GRID_SIZE/2,
                        y1 * GRID_SIZE + GRID_SIZE/2
                    );
                    ctx.lineTo(
                        x2 * GRID_SIZE + GRID_SIZE/2,
                        y2 * GRID_SIZE + GRID_SIZE/2
                    );
                    ctx.stroke();
                }
            });
        }

        // 获取路径数据
        function getPaths() {
            // 这里应该从服务器获取路径数据
            // 暂时使用示例路径
            return [
                [(0, 4), (1, 4), (2, 4), (3, 4), (4, 4)],
                [(0, 12), (1, 12), (2, 12), (3, 12), (4, 12)]
            ];
        }

        // 绘制塔
        function drawTowers() {
            gameState.towers.forEach(tower => {
                const x = tower.x * GRID_SIZE + GRID_SIZE/2;
                const y = tower.y * GRID_SIZE + GRID_SIZE/2;
                
                // 绘制塔的图片
                ctx.drawImage(
                    towerImages[tower.type],
                    tower.x * GRID_SIZE,
                    tower.y * GRID_SIZE
                );
                
                // 绘制塔等级
                if (tower.level > 1) {
                    ctx.fillStyle = 'white';
                    ctx.font = 'bold 10px Arial';
                    ctx.textAlign = 'center';
                    ctx.fillText(
                        tower.level.toString(),
                        x,
                        y + 15
                    );
                }
                
                // 绘制攻击范围（当有目标时）
                if (tower.target) {
                    ctx.strokeStyle = towerImages[tower.type].color;
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.arc(
                        x,
                        y,
                        tower.range * GRID_SIZE,
                        0,
                        Math.PI * 2
                    );
                    ctx.stroke();
                    
                    // 绘制攻击轨迹
                    if (tower.target) {
                        ctx.strokeStyle = towerImages[tower.type].color;
                        ctx.lineWidth = 2;
                        ctx.setLineDash([4, 4]);
                        ctx.beginPath();
                        ctx.moveTo(x, y);
                        ctx.lineTo(
                            tower.target.x * GRID_SIZE + GRID_SIZE/2,
                            tower.target.y * GRID_SIZE + GRID_SIZE/2
                        );
                        ctx.stroke();
                        ctx.setLineDash([]);
                    }
                }
            });
        }

        // 绘制敌人
        function drawEnemies() {
            gameState.enemies.forEach(enemy => {
                const x = enemy.x * GRID_SIZE + GRID_SIZE/2;
                const y = enemy.y * GRID_SIZE + GRID_SIZE/2;
                
                // 绘制敌人
                if (enemy.stealth) {
                    // 隐身敌人半透明
                    ctx.globalAlpha = 0.5;
                }
                
                ctx.fillStyle = getEnemyColor(enemy.type);
                ctx.beginPath();
                ctx.arc(x, y, GRID_SIZE/3, 0, Math.PI * 2);
                ctx.fill();
                
                // 恢复透明度
                ctx.globalAlpha = 1.0;
                
                // 绘制血条背景
                ctx.fillStyle = '#e74c3c';
                ctx.fillRect(
                    x - 15,
                    y - 20,
                    30,
                    5
                );
                
                // 绘制血条
                const healthRatio = enemy.health / enemy.max_health;
                ctx.fillStyle = '#2ecc71';
                ctx.fillRect(
                    x - 15,
                    y - 20,
                    30 * healthRatio,
                    5
                );
                
                // 绘制特殊状态效果
                if (enemy.frozen) {
                    ctx.strokeStyle = '#00bfff';
                    ctx.lineWidth = 2;
                    ctx.beginPath();
                    ctx.arc(x, y, GRID_SIZE/3 + 2, 0, Math.PI * 2);
                    ctx.stroke();
                }
                
                if (enemy.poisoned) {
                    ctx.strokeStyle = '#32cd32';
                    ctx.lineWidth = 2;
                    ctx.beginPath();
                    ctx.arc(x, y, GRID_SIZE/3 + 2, 0, Math.PI * 2);
                    ctx.stroke();
                }
            });
        }

        // 获取敌人颜色
        function getEnemyColor(type) {
            const colors = {
                'NORMAL': '#95a5a6',
                'FAST': '#2ecc71',
                'TANK': '#e67e22',
                'BOSS': '#c0392b',
                'FLYING': '#9b59b6',
                'STEALTH': '#34495e',
                'HEALER': '#1abc9c',
                'SWARM': '#e74c3c'
            };
            return colors[type] || '#95a5a6';
        }

        // 开始游戏
        function startGame() {
            fetch('/start_game')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        gameState.is_running = true;
                        updateGameState();
                    } else {
                        alert(data.message);
                    }
                });
        }

        // 初始化游戏
        initGame();
    </script>
</body>
</html>
        ''')
    
    app.run(host='0.0.0.0', port=5004, debug=True) 