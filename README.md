# Tower Defense Game

一个基于 Flask + 原生 HTML/CSS/JavaScript 的网页塔防游戏。后端负责游戏状态和规则接口，前端使用 Canvas 绘制战场，适合学习全栈游戏状态同步、敌人寻路和塔防数值设计。

## 当前特性

- 多种敌人：普通、快速、坦克、Boss、飞行、隐形、治疗与集群单位
- 多种防御塔、升级、目标选择与范围增益
- 波次、生命、金币、分数和游戏结束状态
- 自适应 Canvas、鼠标放置和浏览器端交互
- Flask API 与前端解耦，便于继续扩展排行榜或存档

## 快速开始

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows PowerShell
# source .venv/bin/activate      # macOS/Linux
pip install -r requirements.txt
python app.py
```

打开 `http://127.0.0.1:5000`。停止服务可按 `Ctrl+C`。

## 开发说明

- 入口：`app.py`
- 页面：`templates/index.html`
- 依赖：`requirements.txt`
- 游戏状态当前保存在进程内存中，重启服务会重置对局
- 生产部署时请关闭 Flask debug，并使用 Gunicorn/Waitress 等 WSGI 服务

## Roadmap

- [ ] 将游戏状态拆分为独立的领域模块
- [ ] 增加关卡配置 JSON 与难度选择
- [ ] 增加测试覆盖和排行榜存储
- [ ] 增加音效、键盘快捷键和触屏操作

## License

MIT License
