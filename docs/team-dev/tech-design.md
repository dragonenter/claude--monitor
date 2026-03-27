# 炉石传说酒馆战棋 AI 自动打牌插件 - 技术设计文档

## 1. 整体架构

### 1.1 架构概览

采用**管道式事件驱动架构**，数据单向流动：

```
日志/截图 -> 解析层 -> GameState -> AI决策 -> 操作队列 -> 鼠标执行
                                      ^
                                      |
                                  用户控制层
```

### 1.2 组件图

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户控制层 (UserControl)                   │
│  启停控制 · 快捷键 · 手动接管 · 状态面板                            │
└──────────────┬──────────────────────────────────┬───────────────┘
               │ 控制信号                          │ 状态查询
┌──────────────▼──────────────────────────────────▼───────────────┐
│                       核心协调器 (Orchestrator)                   │
│  回合生命周期管理 · 模块调度 · 全局错误处理                         │
└──┬──────────┬──────────────┬──────────────┬──────────────┬──────┘
   │          │              │              │              │
   ▼          ▼              ▼              ▼              ▼
┌──────┐ ┌────────┐  ┌────────────┐ ┌──────────┐ ┌────────────┐
│日志  │ │截图    │  │ GameState  │ │ AI决策   │ │ 操作执行   │
│监听  │ │识别    │  │ 管理器     │ │ 引擎     │ │ 引擎       │
│引擎  │ │(备用)  │  │            │ │          │ │            │
└──┬───┘ └───┬────┘  └────────────┘ └──────────┘ └────────────┘
   │         │              ▲              │              │
   │         │              │              │              ▼
   ▼         ▼              │              │       ┌────────────┐
┌──────────────────┐        │              │       │ 鼠标模拟   │
│  日志解析模块    │────────┘              │       │ 驱动       │
│  (7个插件式解析器)│                       │       └────────────┘
└──────────────────┘                       │
                                           ▼
                                    ┌────────────┐
                                    │ AI策略模块 │
                                    │ (11个策略)  │
                                    └────────────┘
```

### 1.3 数据流

```
1. LogWatcher tail -f output_log.txt
       ↓ 原始行
2. LogParser 分发到各解析器插件
       ↓ 结构化事件 (LogEvent)
3. GameStateManager 聚合事件，更新状态
       ↓ GameState 快照
4. AIEngine 评估状态，生成决策
       ↓ ActionPlan (操作序列)
5. ActionExecutor 排队执行，鼠标模拟
       ↓ 鼠标操作 + 等待
6. Orchestrator 监控执行结果，更新状态
```

---

## 2. 技术栈

| 类别 | 选型 | 理由 |
|------|------|------|
| **语言** | Python 3.11+ | 游戏工具领域主流，丰富的自动化库生态 |
| **日志监听** | `watchdog` + 自定义 tail | 跨平台文件监听，比纯轮询高效 |
| **截图** | `mss` (屏幕捕获) + `Pillow` | mss 比 pyautogui 截图快 10x |
| **OCR/识别** | `paddleocr` 或 `easyocr` | 中文支持好，本地运行无需网络 |
| **鼠标模拟** | `pynput` + `ctypes`(win32api) | pynput 跨平台，ctypes 调 win32 做底层操作更可靠 |
| **快捷键** | `keyboard` | 全局热键监听，不依赖窗口焦点 |
| **窗口管理** | `pywin32` (`win32gui`) | Windows 窗口查找、前台切换 |
| **配置** | `pydantic` + YAML | pydantic 做数据校验，YAML 用户友好 |
| **日志** | `loguru` | 比标准 logging 更易用，支持结构化日志 |
| **测试** | `pytest` + `pytest-asyncio` | 标准测试框架 |
| **UI面板** | `rich` (终端UI) | 轻量，无需 GUI 框架，终端内实时刷新 |
| **异步** | `asyncio` | 核心循环异步驱动，避免阻塞 |

---

## 3. 项目目录结构

```
hs-battlegrounds-ai/
├── pyproject.toml                    # 项目配置、依赖
├── config.yaml                       # 用户配置文件
├── README.md
├── docs/
│   └── team-dev/
│       ├── prd.md
│       └── tech-design.md
├── src/
│   └── hs_bg_ai/
│       ├── __init__.py
│       ├── main.py                   # 入口点
│       ├── config.py                 # 配置加载与校验
│       │
│       ├── core/                     # 核心协调
│       │   ├── __init__.py
│       │   ├── orchestrator.py       # 主协调器
│       │   ├── events.py             # 事件总线
│       │   └── errors.py             # 全局错误处理
│       │
│       ├── models/                   # 数据模型（共享类型）
│       │   ├── __init__.py
│       │   ├── game_state.py         # GameState 及所有子结构
│       │   ├── actions.py            # Action 类型定义
│       │   ├── cards.py              # 卡牌数据结构
│       │   ├── heroes.py             # 英雄数据结构
│       │   └── enums.py              # 枚举常量
│       │
│       ├── log_engine/               # 日志监听引擎
│       │   ├── __init__.py
│       │   ├── watcher.py            # 文件监听 (F-01)
│       │   └── dispatcher.py         # 行分发器
│       │
│       ├── log_parsers/              # 日志解析模块
│       │   ├── __init__.py
│       │   ├── base.py               # 解析器基类
│       │   ├── shop_parser.py        # 商店解析 (F-02)
│       │   ├── hand_parser.py        # 手牌解析 (F-03)
│       │   ├── board_parser.py       # 战场解析 (F-04)
│       │   ├── resource_parser.py    # 资源解析 (F-05)
│       │   ├── hero_parser.py        # 英雄解析 (F-06)
│       │   ├── turn_parser.py        # 回合解析 (F-07)
│       │   └── opponent_parser.py    # 对手解析 (F-08)
│       │
│       ├── screen/                   # 截图识别（备用）
│       │   ├── __init__.py
│       │   ├── capturer.py           # 截屏 (F-09)
│       │   ├── recognizer.py         # 图像识别
│       │   └── regions.py            # 屏幕区域坐标定义
│       │
│       ├── state/                    # GameState 管理
│       │   ├── __init__.py
│       │   ├── manager.py            # 状态管理器 (F-10)
│       │   └── fusion.py             # 日志+截图数据融合
│       │
│       ├── ai/                       # AI 决策引擎
│       │   ├── __init__.py
│       │   ├── engine.py             # 决策引擎入口 (F-12)
│       │   ├── evaluator.py          # 局面评估器
│       │   ├── strategies/
│       │   │   ├── __init__.py
│       │   │   ├── buy.py            # 购买策略 (F-13)
│       │   │   ├── sell.py           # 卖出策略 (F-14)
│       │   │   ├── refresh.py        # 刷新策略 (F-15)
│       │   │   ├── upgrade.py        # 升本策略 (F-16)
│       │   │   ├── position.py       # 站位策略 (F-17)
│       │   │   ├── hero_power.py     # 英雄技能 (F-18)
│       │   │   ├── comp_plan.py      # 阵容规划 (F-19)
│       │   │   ├── triple.py         # 三连策略 (F-20)
│       │   │   ├── hero_select.py    # 英雄选择 (F-21)
│       │   │   └── quest_select.py   # 任务选择 (F-22)
│       │   └── turn_planner.py       # 回合编排器 (F-12的子模块)
│       │
│       ├── executor/                 # 操作执行引擎
│       │   ├── __init__.py
│       │   ├── mouse.py              # 鼠标模拟 (F-23)
│       │   ├── queue.py              # 操作队列 (F-24)
│       │   ├── timing.py             # 时序控制 (F-25)
│       │   └── time_manager.py       # 时间管理/自计时 (F-26)
│       │
│       ├── control/                  # 用户控制
│       │   ├── __init__.py
│       │   ├── controller.py         # 启停控制 (F-27)
│       │   ├── hotkeys.py            # 快捷键 (F-28)
│       │   └── takeover.py           # 手动接管 (F-29)
│       │
│       ├── recovery/                 # 错误恢复
│       │   ├── __init__.py
│       │   ├── log_recovery.py       # 日志读取失败恢复 (F-30)
│       │   ├── exec_recovery.py      # 执行失败恢复 (F-31)
│       │   ├── window_recovery.py    # 窗口丢失恢复 (F-32)
│       │   └── disconnect_recovery.py # 断线恢复 (F-33)
│       │
│       └── ui/                       # 状态面板
│           ├── __init__.py
│           ├── dashboard.py          # 状态面板 (F-34)
│           └── logger_ui.py          # 日志展示 (F-35)
│
├── tests/                            # 测试 (F-36, F-37)
│   ├── conftest.py                   # 共享 fixtures
│   ├── fixtures/                     # 测试数据
│   │   ├── sample_logs/              # 真实日志样本
│   │   └── sample_states/            # GameState JSON 快照
│   ├── unit/
│   │   ├── test_log_parsers/
│   │   ├── test_state/
│   │   ├── test_ai/
│   │   ├── test_executor/
│   │   └── test_recovery/
│   └── integration/
│       ├── test_log_to_state.py
│       ├── test_state_to_ai.py
│       └── test_ai_to_executor.py
│
└── data/                             # 静态数据
    ├── cards.json                    # 卡牌数据库
    ├── heroes.json                   # 英雄数据库
    └── minion_types.json             # 随从种族数据
```

---

## 4. 数据模型定义（`src/hs_bg_ai/models/`）

### 4.1 核心枚举 (`enums.py`)

```python
from enum import Enum, IntEnum

class Phase(str, Enum):
    HERO_SELECT = "hero_select"       # 英雄选择阶段
    RECRUIT = "recruit"               # 招募阶段（酒馆回合）
    COMBAT = "combat"                 # 战斗阶段
    GAME_OVER = "game_over"

class MinionType(str, Enum):
    BEAST = "beast"
    DEMON = "demon"
    DRAGON = "dragon"
    ELEMENTAL = "elemental"
    MECH = "mech"
    MURLOC = "murloc"
    NAGA = "naga"
    PIRATE = "pirate"
    QUILBOAR = "quilboar"
    UNDEAD = "undead"
    ALL = "all"
    NONE = "none"

class TavernTier(IntEnum):
    TIER_1 = 1
    TIER_2 = 2
    TIER_3 = 3
    TIER_4 = 4
    TIER_5 = 5
    TIER_6 = 6

class ActionType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    REFRESH = "refresh"
    UPGRADE = "upgrade"
    PLAY = "play"                     # 从手牌放到场上
    MOVE = "move"                     # 调整站位
    HERO_POWER = "hero_power"
    FREEZE = "freeze"
    END_TURN = "end_turn"
    SELECT_HERO = "select_hero"
    SELECT_QUEST = "select_quest"
    TRIPLE_DISCOVER = "triple_discover"
```

### 4.2 卡牌模型 (`cards.py`)

```python
from dataclasses import dataclass, field
from typing import Optional
from .enums import MinionType, TavernTier

@dataclass
class Minion:
    """场上或手牌中的一个随从实例"""
    card_id: str                      # 炉石内部卡牌ID
    name: str                         # 中文名
    attack: int
    health: int
    tavern_tier: TavernTier
    minion_type: MinionType
    is_golden: bool = False
    taunt: bool = False
    divine_shield: bool = False
    poisonous: bool = False
    windfury: bool = False
    reborn: bool = False
    deathrattle: bool = False
    enchantments: list[str] = field(default_factory=list)
    position: int = -1                # 场上位置 0-6，-1 表示手牌

@dataclass
class ShopMinion:
    """商店中待购买的随从"""
    card_id: str
    name: str
    attack: int
    health: int
    tavern_tier: TavernTier
    minion_type: MinionType
    is_golden: bool = False
    slot_index: int = 0               # 商店槽位 0-6
    cost: int = 3                     # 购买费用（通常3）
```

### 4.3 英雄模型 (`heroes.py`)

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class HeroPower:
    power_id: str
    name: str
    cost: int
    is_passive: bool
    is_available: bool = True         # 本回合是否可用

@dataclass
class Hero:
    hero_id: str
    name: str
    health: int
    armor: int
    hero_power: HeroPower
    is_dead: bool = False
```

### 4.4 GameState (`game_state.py`)

```python
from dataclasses import dataclass, field
from typing import Optional
from .cards import Minion, ShopMinion
from .heroes import Hero
from .enums import Phase, TavernTier

@dataclass
class ResourceState:
    """资源状态"""
    gold: int = 0
    max_gold: int = 0                 # 本回合最大金币
    tavern_tier: TavernTier = TavernTier.TIER_1
    upgrade_cost: int = 5             # 升本费用

@dataclass
class OpponentInfo:
    """对手信息"""
    player_id: str
    hero_name: str
    health: int
    tavern_tier: TavernTier
    last_board_known: list[Minion] = field(default_factory=list)
    damage_taken_history: list[int] = field(default_factory=list)
    is_dead: bool = False

@dataclass
class TurnInfo:
    """回合信息"""
    turn_number: int = 0
    phase: Phase = Phase.HERO_SELECT
    time_remaining_estimate: float = 0.0  # 自计时估算剩余秒数
    recruit_start_time: float = 0.0       # 招募阶段开始时间戳

@dataclass
class GameState:
    """
    完整游戏状态 — 所有模块的唯一数据源。
    由 StateManager 维护，AI 引擎只读访问。
    """
    # 我方英雄
    hero: Optional[Hero] = None

    # 资源
    resources: ResourceState = field(default_factory=ResourceState)

    # 场上随从（按位置排序，最多7个）
    board: list[Minion] = field(default_factory=list)

    # 手牌（最多10个）
    hand: list[Minion] = field(default_factory=list)

    # 商店
    shop: list[ShopMinion] = field(default_factory=list)
    is_shop_frozen: bool = False

    # 回合信息
    turn: TurnInfo = field(default_factory=TurnInfo)

    # 对手信息
    opponents: list[OpponentInfo] = field(default_factory=list)
    next_opponent_id: Optional[str] = None

    # 元数据
    game_id: str = ""
    is_game_active: bool = False

    # 英雄选择阶段的候选英雄
    hero_choices: list[Hero] = field(default_factory=list)

    # 任务选择
    quest_choices: list[dict] = field(default_factory=list)

    # 三连发现选项
    discover_choices: list[Minion] = field(default_factory=list)

    def board_count(self) -> int:
        return len(self.board)

    def hand_count(self) -> int:
        return len(self.hand)

    def available_gold(self) -> int:
        return self.resources.gold

    def board_space(self) -> int:
        return 7 - len(self.board)
```

### 4.5 Action 模型 (`actions.py`)

```python
from dataclasses import dataclass
from typing import Optional, Union
from .enums import ActionType

@dataclass
class GameAction:
    """AI 引擎输出的单个操作"""
    action_type: ActionType
    source_index: int = -1            # 来源位置（商店槽位/手牌位置/场上位置）
    target_index: int = -1            # 目标位置
    card_id: Optional[str] = None     # 可选：目标卡牌 ID
    priority: int = 0                 # 执行优先级
    reason: str = ""                  # AI 决策理由（调试用）

@dataclass
class ActionPlan:
    """一个回合的完整操作计划"""
    actions: list[GameAction]
    estimated_time_seconds: float     # 预估执行耗时
    confidence: float                 # AI 置信度 0.0-1.0
    turn_number: int
```

---

## 5. 模块详细设计

### 模块 M-01: 核心协调器 (`core/`)

**职责：** 管理游戏主循环，协调各模块生命周期，分发事件，统一错误处理。

**文件：**
- `src/hs_bg_ai/core/__init__.py`
- `src/hs_bg_ai/core/orchestrator.py`
- `src/hs_bg_ai/core/events.py`
- `src/hs_bg_ai/core/errors.py`

**接口：**

```python
# orchestrator.py
class Orchestrator:
    """主协调器，驱动整个 AI 流程"""

    def __init__(self, config: AppConfig) -> None: ...

    async def start(self) -> None:
        """启动所有子系统，开始主循环"""

    async def stop(self) -> None:
        """优雅关闭所有子系统"""

    async def pause(self) -> None:
        """暂停 AI 决策，保持日志监听"""

    async def resume(self) -> None:
        """恢复 AI 决策"""

    @property
    def is_running(self) -> bool: ...

    @property
    def is_paused(self) -> bool: ...

# events.py
from typing import Callable, Any
from enum import Enum

class EventType(str, Enum):
    LOG_LINE = "log_line"
    STATE_UPDATED = "state_updated"
    TURN_START = "turn_start"
    TURN_END = "turn_end"
    GAME_START = "game_start"
    GAME_OVER = "game_over"
    ACTION_COMPLETED = "action_completed"
    ACTION_FAILED = "action_failed"
    ERROR = "error"
    PAUSE_REQUESTED = "pause_requested"
    RESUME_REQUESTED = "resume_requested"

class EventBus:
    """简单的发布-订阅事件总线"""

    def subscribe(self, event_type: EventType, callback: Callable) -> None: ...
    def unsubscribe(self, event_type: EventType, callback: Callable) -> None: ...
    async def publish(self, event_type: EventType, data: Any = None) -> None: ...

# errors.py
class HSBGError(Exception):
    """基础异常"""
    pass

class LogReadError(HSBGError): ...
class StateError(HSBGError): ...
class ExecutionError(HSBGError): ...
class WindowNotFoundError(HSBGError): ...
class DisconnectError(HSBGError): ...
```

**依赖：** config, events (自身), 所有其他模块（通过事件总线松耦合）

---

### 模块 M-02: 数据模型 (`models/`)

**职责：** 定义所有共享数据结构，不含业务逻辑。

**文件：**
- `src/hs_bg_ai/models/__init__.py`
- `src/hs_bg_ai/models/game_state.py`
- `src/hs_bg_ai/models/actions.py`
- `src/hs_bg_ai/models/cards.py`
- `src/hs_bg_ai/models/heroes.py`
- `src/hs_bg_ai/models/enums.py`

**接口：** 见第 4 节的完整定义。纯数据结构，无方法依赖。

**依赖：** 无（叶子模块）

---

### 模块 M-03: 日志监听引擎 (`log_engine/`)

**职责：** 持续监听 `output_log.txt` 文件变化，将新增行发送到事件总线。

**文件：**
- `src/hs_bg_ai/log_engine/__init__.py`
- `src/hs_bg_ai/log_engine/watcher.py`
- `src/hs_bg_ai/log_engine/dispatcher.py`

**接口：**

```python
# watcher.py
class LogWatcher:
    """tail -f 风格的日志文件监听器"""

    def __init__(self, log_path: str, event_bus: EventBus) -> None: ...

    async def start(self) -> None:
        """开始监听，新行通过 EventBus 发布 LOG_LINE 事件"""

    async def stop(self) -> None:
        """停止监听"""

    def seek_to_end(self) -> None:
        """跳到文件末尾（启动时忽略历史日志）"""

# dispatcher.py
class LogDispatcher:
    """将原始日志行分发到注册的解析器"""

    def register_parser(self, parser: "BaseLogParser") -> None: ...

    async def dispatch(self, line: str) -> list["LogEvent"]:
        """将一行日志分发给所有注册解析器，返回产生的事件列表"""
```

**依赖：** `core/events`, `log_parsers/base`

---

### 模块 M-04: 日志解析器 (`log_parsers/`)

**职责：** 将原始日志行解析为结构化的 `LogEvent`，每个解析器负责一类游戏数据。

**文件：**
- `src/hs_bg_ai/log_parsers/__init__.py`
- `src/hs_bg_ai/log_parsers/base.py`
- `src/hs_bg_ai/log_parsers/shop_parser.py` (F-02)
- `src/hs_bg_ai/log_parsers/hand_parser.py` (F-03)
- `src/hs_bg_ai/log_parsers/board_parser.py` (F-04)
- `src/hs_bg_ai/log_parsers/resource_parser.py` (F-05)
- `src/hs_bg_ai/log_parsers/hero_parser.py` (F-06)
- `src/hs_bg_ai/log_parsers/turn_parser.py` (F-07)
- `src/hs_bg_ai/log_parsers/opponent_parser.py` (F-08)

**接口：**

```python
# base.py
from dataclasses import dataclass
from typing import Optional
from ..models.enums import Phase

@dataclass
class LogEvent:
    """解析器输出的结构化事件"""
    event_type: str                   # 如 "shop_update", "turn_start"
    data: dict                        # 事件数据
    timestamp: float                  # 日志行时间戳
    raw_line: str                     # 原始日志行

class BaseLogParser:
    """解析器基类"""

    # 子类必须设置
    PARSER_NAME: str = ""
    # 正则模式列表，用于快速判断该行是否相关
    LINE_PATTERNS: list[str] = []

    def can_parse(self, line: str) -> bool:
        """快速判断：该行是否属于本解析器的职责范围"""

    def parse(self, line: str) -> Optional[LogEvent]:
        """解析一行日志，返回 LogEvent 或 None"""

# shop_parser.py
class ShopParser(BaseLogParser):
    PARSER_NAME = "shop"

    def parse(self, line: str) -> Optional[LogEvent]:
        """
        输出 LogEvent:
          event_type: "shop_update"
          data: {"minions": list[dict], "is_frozen": bool}
        """

# hand_parser.py
class HandParser(BaseLogParser):
    PARSER_NAME = "hand"

    def parse(self, line: str) -> Optional[LogEvent]:
        """
        输出 LogEvent:
          event_type: "hand_update"
          data: {"minions": list[dict]}
        """

# board_parser.py
class BoardParser(BaseLogParser):
    PARSER_NAME = "board"

    def parse(self, line: str) -> Optional[LogEvent]:
        """
        输出 LogEvent:
          event_type: "board_update"
          data: {"minions": list[dict], "zone": str}
        """

# resource_parser.py
class ResourceParser(BaseLogParser):
    PARSER_NAME = "resource"

    def parse(self, line: str) -> Optional[LogEvent]:
        """
        输出 LogEvent:
          event_type: "resource_update"
          data: {"gold": int, "max_gold": int, "tavern_tier": int, "upgrade_cost": int}
        """

# hero_parser.py
class HeroParser(BaseLogParser):
    PARSER_NAME = "hero"

    def parse(self, line: str) -> Optional[LogEvent]:
        """
        输出 LogEvent:
          event_type: "hero_update" | "hero_choices"
          data: {"hero_id": str, "health": int, "armor": int, ...}
        """

# turn_parser.py
class TurnParser(BaseLogParser):
    PARSER_NAME = "turn"

    def parse(self, line: str) -> Optional[LogEvent]:
        """
        输出 LogEvent:
          event_type: "turn_start" | "turn_end" | "phase_change"
          data: {"turn_number": int, "phase": str}
        """

# opponent_parser.py
class OpponentParser(BaseLogParser):
    PARSER_NAME = "opponent"

    def parse(self, line: str) -> Optional[LogEvent]:
        """
        输出 LogEvent:
          event_type: "opponent_update"
          data: {"player_id": str, "hero_name": str, "health": int, ...}
        """
```

**依赖：** `models/`

---

### 模块 M-05: 截图识别 (`screen/`)

**职责：** 备用数据源，通过截图+OCR/模板匹配识别游戏画面，用于日志不可用时的降级方案。

**文件：**
- `src/hs_bg_ai/screen/__init__.py`
- `src/hs_bg_ai/screen/capturer.py`
- `src/hs_bg_ai/screen/recognizer.py`
- `src/hs_bg_ai/screen/regions.py`

**接口：**

```python
# capturer.py
from PIL import Image

class ScreenCapturer:
    """游戏窗口截屏"""

    def __init__(self, window_title: str = "炉石传说") -> None: ...

    def capture_full(self) -> Image.Image:
        """截取完整游戏窗口"""

    def capture_region(self, region_name: str) -> Image.Image:
        """截取指定区域（如 'shop', 'board', 'gold'）"""

    def find_game_window(self) -> bool:
        """查找游戏窗口，返回是否找到"""

# recognizer.py
from ..models.game_state import GameState

class ScreenRecognizer:
    """从截图中识别游戏状态"""

    def recognize(self, screenshot: Image.Image) -> dict:
        """
        返回可合并到 GameState 的部分状态字典
        keys: "shop", "board", "hand", "gold", "tavern_tier", "hero_health"
        """

# regions.py
from dataclasses import dataclass

@dataclass
class ScreenRegion:
    """屏幕区域定义（相对坐标 0.0-1.0）"""
    name: str
    x: float      # 左上角 x (相对)
    y: float      # 左上角 y (相对)
    w: float      # 宽度 (相对)
    h: float      # 高度 (相对)

# 预定义区域常量
REGION_SHOP: ScreenRegion
REGION_BOARD: ScreenRegion
REGION_HAND: ScreenRegion
REGION_GOLD: ScreenRegion
REGION_HERO_POWER: ScreenRegion
REGION_TAVERN_TIER: ScreenRegion
```

**依赖：** `models/`, `Pillow`, `mss`, OCR 库

---

### 模块 M-06: GameState 管理器 (`state/`)

**职责：** 聚合来自日志解析和截图识别的事件，维护并更新唯一的 `GameState` 实例。

**文件：**
- `src/hs_bg_ai/state/__init__.py`
- `src/hs_bg_ai/state/manager.py`
- `src/hs_bg_ai/state/fusion.py`

**接口：**

```python
# manager.py
from ..models.game_state import GameState
from ..log_parsers.base import LogEvent

class StateManager:
    """游戏状态管理器 — GameState 的唯一写入者"""

    def __init__(self, event_bus: "EventBus") -> None: ...

    def get_state(self) -> GameState:
        """返回当前 GameState 的深拷贝（只读快照）"""

    async def apply_event(self, event: LogEvent) -> None:
        """将解析事件应用到 GameState，更新后发布 STATE_UPDATED"""

    def reset(self) -> None:
        """新游戏开始时重置状态"""

# fusion.py
from ..models.game_state import GameState

class DataFusion:
    """融合日志数据和截图数据"""

    def fuse(self, log_state: GameState, screen_data: dict) -> GameState:
        """
        融合策略：
        - 日志数据优先（更精确）
        - 截图数据补充缺失字段
        - 冲突时以日志为准
        """
```

**依赖：** `models/`, `core/events`, `log_parsers/base`

---

### 模块 M-07: AI 决策引擎 (`ai/`)

**职责：** 接收 GameState 快照，通过策略组合生成最优操作计划。

**文件：**
- `src/hs_bg_ai/ai/__init__.py`
- `src/hs_bg_ai/ai/engine.py`
- `src/hs_bg_ai/ai/evaluator.py`
- `src/hs_bg_ai/ai/turn_planner.py`
- `src/hs_bg_ai/ai/strategies/__init__.py`
- `src/hs_bg_ai/ai/strategies/buy.py`
- `src/hs_bg_ai/ai/strategies/sell.py`
- `src/hs_bg_ai/ai/strategies/refresh.py`
- `src/hs_bg_ai/ai/strategies/upgrade.py`
- `src/hs_bg_ai/ai/strategies/position.py`
- `src/hs_bg_ai/ai/strategies/hero_power.py`
- `src/hs_bg_ai/ai/strategies/comp_plan.py`
- `src/hs_bg_ai/ai/strategies/triple.py`
- `src/hs_bg_ai/ai/strategies/hero_select.py`
- `src/hs_bg_ai/ai/strategies/quest_select.py`

**接口：**

```python
# engine.py
from ..models.game_state import GameState
from ..models.actions import ActionPlan

class AIEngine:
    """AI 决策引擎入口"""

    def __init__(self, config: "AIConfig") -> None: ...

    def decide(self, state: GameState) -> ActionPlan:
        """
        根据当前 GameState 生成操作计划。
        不同阶段调用不同策略组合：
        - hero_select 阶段 -> HeroSelectStrategy
        - recruit 阶段 -> TurnPlanner 编排各策略
        - quest 选择 -> QuestSelectStrategy
        - discover 选择 -> TripleStrategy
        """

# evaluator.py
from ..models.game_state import GameState
from ..models.cards import Minion, ShopMinion

class BoardEvaluator:
    """局面评估器"""

    def evaluate_board(self, state: GameState) -> float:
        """评估当前场面强度，返回分数"""

    def evaluate_minion(self, minion: Minion, state: GameState) -> float:
        """评估单个随从的价值"""

    def evaluate_shop_minion(self, minion: ShopMinion, state: GameState) -> float:
        """评估商店随从对当前阵容的价值"""

    def evaluate_comp_direction(self, state: GameState) -> dict[str, float]:
        """评估各阵容方向的得分 {"murloc": 0.7, "mech": 0.5, ...}"""

# turn_planner.py
from ..models.game_state import GameState
from ..models.actions import ActionPlan

class TurnPlanner:
    """回合编排器 — 协调多个策略产生最优回合操作序列"""

    def plan_turn(self, state: GameState) -> ActionPlan:
        """
        编排一个完整回合的操作顺序：
        1. 是否升本？(UpgradeStrategy)
        2. 是否使用英雄技能？(HeroPowerStrategy)
        3. 购买哪些？(BuyStrategy)
        4. 卖出哪些？(SellStrategy)
        5. 是否刷新？(RefreshStrategy)
        6. 三连发现选择？(TripleStrategy)
        7. 最终站位 (PositionStrategy)
        8. 剩余时间再考虑
        """

# strategies/buy.py (其他策略同模式)
from ...models.game_state import GameState
from ...models.actions import GameAction

class BuyStrategy:
    """购买决策策略"""

    def suggest(self, state: GameState) -> list[GameAction]:
        """返回建议购买的操作列表（按优先级排序）"""

# strategies/comp_plan.py
class CompPlanStrategy:
    """阵容规划策略"""

    def get_current_comp(self, state: GameState) -> str:
        """识别当前阵容类型"""

    def get_target_comp(self, state: GameState) -> str:
        """确定目标阵容方向"""

    def is_pivot_needed(self, state: GameState) -> bool:
        """是否需要转型"""

# strategies/hero_select.py
class HeroSelectStrategy:
    """英雄选择策略"""

    def select(self, heroes: list["Hero"]) -> int:
        """返回选择的英雄索引"""

    def get_hero_tier(self, hero_id: str) -> float:
        """查询英雄强度评分"""
```

**依赖：** `models/`（只读 GameState）, `data/`（卡牌/英雄数据库）

---

### 模块 M-08: 操作执行引擎 (`executor/`)

**职责：** 将 AI 的 ActionPlan 转换为鼠标操作序列并执行，包含时序控制和时间管理。

**文件：**
- `src/hs_bg_ai/executor/__init__.py`
- `src/hs_bg_ai/executor/mouse.py`
- `src/hs_bg_ai/executor/queue.py`
- `src/hs_bg_ai/executor/timing.py`
- `src/hs_bg_ai/executor/time_manager.py`

**接口：**

```python
# mouse.py
class MouseController:
    """鼠标操作模拟器 — 贝塞尔曲线 + 随机延迟"""

    def __init__(self, config: "MouseConfig") -> None: ...

    async def move_to(self, x: int, y: int) -> None:
        """移动到目标坐标（贝塞尔曲线路径）"""

    async def click(self, x: int, y: int) -> None:
        """移动并点击"""

    async def drag(self, from_x: int, from_y: int, to_x: int, to_y: int) -> None:
        """拖拽操作"""

    async def right_click(self, x: int, y: int) -> None:
        """右键点击"""

    def set_speed(self, speed_factor: float) -> None:
        """调整操作速度 (0.5 = 慢, 1.0 = 正常, 2.0 = 快)"""

# queue.py
from ..models.actions import ActionPlan, GameAction

class ActionQueue:
    """操作队列 — FIFO 执行，支持中断"""

    def __init__(self, mouse: MouseController, coord_mapper: "CoordMapper") -> None: ...

    async def execute_plan(self, plan: ActionPlan) -> list[dict]:
        """
        执行操作计划，返回每个操作的执行结果
        [{"action": GameAction, "success": bool, "error": str | None}]
        """

    async def execute_single(self, action: GameAction) -> bool:
        """执行单个操作"""

    def cancel_remaining(self) -> None:
        """取消队列中剩余操作"""

    @property
    def pending_count(self) -> int: ...

# timing.py
import random

class TimingController:
    """时序控制 — 随机延迟，模拟人类操作节奏"""

    def __init__(self, config: "TimingConfig") -> None: ...

    async def delay_between_actions(self) -> None:
        """操作间随机延迟 (200-500ms)"""

    async def delay_think(self) -> None:
        """模拟"思考"延迟 (500-1500ms)"""

    async def delay_click(self) -> None:
        """点击前微延迟 (50-150ms)"""

    def generate_bezier_points(
        self, start: tuple[int, int], end: tuple[int, int], num_points: int = 20
    ) -> list[tuple[int, int]]:
        """生成贝塞尔曲线路径点"""

# time_manager.py
import time

class TimeManager:
    """自计时管理器 — 跟踪回合时间，决定何时结束"""

    def __init__(self, config: "TimeConfig") -> None: ...

    def on_turn_start(self) -> None:
        """回合开始，重置计时"""

    def elapsed(self) -> float:
        """已用秒数"""

    def remaining_estimate(self) -> float:
        """估算剩余秒数"""

    def should_end_turn(self) -> bool:
        """是否应该立即结束回合（时间不够了）"""

    def can_fit_action(self, estimated_seconds: float) -> bool:
        """剩余时间是否够执行一个操作"""
```

**依赖：** `models/actions`, `core/events`

---

### 模块 M-09: 用户控制 (`control/`)

**职责：** 管理启停、全局快捷键、手动接管机制。

**文件：**
- `src/hs_bg_ai/control/__init__.py`
- `src/hs_bg_ai/control/controller.py`
- `src/hs_bg_ai/control/hotkeys.py`
- `src/hs_bg_ai/control/takeover.py`

**接口：**

```python
# controller.py
class AppController:
    """应用层控制器"""

    def __init__(self, orchestrator: "Orchestrator", event_bus: "EventBus") -> None: ...

    async def start_bot(self) -> None:
        """启动 AI"""

    async def stop_bot(self) -> None:
        """停止 AI"""

    async def toggle_pause(self) -> None:
        """切换暂停/恢复"""

    def get_status(self) -> dict:
        """返回当前状态 {"running": bool, "paused": bool, "game_active": bool, ...}"""

# hotkeys.py
class HotkeyManager:
    """全局快捷键管理"""

    def __init__(self, controller: AppController, config: "HotkeyConfig") -> None: ...

    def register_defaults(self) -> None:
        """注册默认快捷键:
        F9 = 启动/停止
        F10 = 暂停/恢复
        F11 = 手动接管切换
        F12 = 紧急停止
        """

    def start_listening(self) -> None: ...
    def stop_listening(self) -> None: ...

# takeover.py
class TakeoverManager:
    """手动接管管理器"""

    def __init__(self, event_bus: "EventBus") -> None: ...

    def enable_manual_mode(self) -> None:
        """切换到手动模式：AI 暂停决策，但继续监听状态"""

    def disable_manual_mode(self) -> None:
        """恢复 AI 模式"""

    @property
    def is_manual(self) -> bool: ...
```

**依赖：** `core/orchestrator`, `core/events`

---

### 模块 M-10: 错误恢复 (`recovery/`)

**职责：** 处理各类异常场景的自动恢复逻辑。

**文件：**
- `src/hs_bg_ai/recovery/__init__.py`
- `src/hs_bg_ai/recovery/log_recovery.py` (F-30)
- `src/hs_bg_ai/recovery/exec_recovery.py` (F-31)
- `src/hs_bg_ai/recovery/window_recovery.py` (F-32)
- `src/hs_bg_ai/recovery/disconnect_recovery.py` (F-33)

**接口：**

```python
# 所有恢复器共同接口
class BaseRecovery:
    """恢复器基类"""

    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0

    async def detect(self) -> bool:
        """检测是否需要恢复"""

    async def recover(self) -> bool:
        """执行恢复，返回是否成功"""

# log_recovery.py
class LogRecovery(BaseRecovery):
    """日志读取失败恢复 — 文件被轮转/删除/锁定"""

    async def recover(self) -> bool:
        """重新定位日志文件，重新打开监听"""

# exec_recovery.py
class ExecRecovery(BaseRecovery):
    """执行失败恢复 — 点击无响应/操作超时"""

    async def recover(self) -> bool:
        """重试操作或跳过当前操作"""

# window_recovery.py
class WindowRecovery(BaseRecovery):
    """窗口丢失恢复 — 游戏最小化/遮挡"""

    async def recover(self) -> bool:
        """查找窗口，激活前台"""

# disconnect_recovery.py
class DisconnectRecovery(BaseRecovery):
    """断线恢复 — 检测断线状态，等待重连"""

    async def recover(self) -> bool:
        """等待游戏重连，重新同步状态"""
```

**依赖：** `core/events`, `core/errors`, `log_engine/`, `screen/capturer`

---

### 模块 M-11: UI 面板 (`ui/`)

**职责：** 在终端显示实时状态面板和日志。

**文件：**
- `src/hs_bg_ai/ui/__init__.py`
- `src/hs_bg_ai/ui/dashboard.py` (F-34)
- `src/hs_bg_ai/ui/logger_ui.py` (F-35)

**接口：**

```python
# dashboard.py
class Dashboard:
    """终端实时状态面板 (rich)"""

    def __init__(self, event_bus: "EventBus") -> None: ...

    async def start(self) -> None:
        """开始渲染面板"""

    async def stop(self) -> None: ...

    def update_state(self, state: "GameState") -> None:
        """更新显示的游戏状态"""

    def update_ai_decision(self, plan: "ActionPlan") -> None:
        """显示当前 AI 决策"""

    def update_status(self, status: dict) -> None:
        """更新运行状态"""

# logger_ui.py
class LoggerUI:
    """日志输出管理 — 文件 + 终端双输出"""

    def __init__(self, config: "LogConfig") -> None: ...

    def setup(self) -> None:
        """配置 loguru 输出"""
```

**依赖：** `core/events`, `models/game_state`, `rich`

---

### 模块 M-12: 配置 (`config.py`)

**职责：** 加载、校验、管理所有配置项。

**文件：**
- `src/hs_bg_ai/config.py`
- `config.yaml`（项目根目录）

**接口：**

```python
# config.py
from pydantic import BaseModel
from pathlib import Path

class MouseConfig(BaseModel):
    speed_factor: float = 1.0
    bezier_deviation: float = 0.3     # 曲线随机偏移
    click_delay_min: float = 0.05
    click_delay_max: float = 0.15

class TimingConfig(BaseModel):
    action_delay_min: float = 0.2
    action_delay_max: float = 0.5
    think_delay_min: float = 0.5
    think_delay_max: float = 1.5

class TimeConfig(BaseModel):
    turn_duration: float = 75.0       # 招募阶段默认秒数
    safety_margin: float = 5.0        # 提前结束的安全余量
    first_turn_duration: float = 45.0 # 第一回合时间

class HotkeyConfig(BaseModel):
    start_stop: str = "f9"
    pause_resume: str = "f10"
    manual_takeover: str = "f11"
    emergency_stop: str = "f12"

class AIConfig(BaseModel):
    aggression: float = 0.5           # 0=保守, 1=激进
    upgrade_bias: float = 0.5         # 升本倾向
    refresh_limit: int = 3            # 单回合最大刷新次数

class LogConfig(BaseModel):
    log_path: str = ""                # 自动检测
    log_level: str = "INFO"
    log_file: str = "hs_bg_ai.log"

class AppConfig(BaseModel):
    mouse: MouseConfig = MouseConfig()
    timing: TimingConfig = TimingConfig()
    time: TimeConfig = TimeConfig()
    hotkeys: HotkeyConfig = HotkeyConfig()
    ai: AIConfig = AIConfig()
    log: LogConfig = LogConfig()
    game_window_title: str = "炉石传说"

def load_config(config_path: Path = Path("config.yaml")) -> AppConfig:
    """加载配置文件，缺失项用默认值"""
```

**依赖：** 无（叶子模块）

---

### 模块 M-13: 入口 (`main.py`)

**职责：** 程序入口，组装依赖，启动主循环。

**文件：**
- `src/hs_bg_ai/main.py`
- `src/hs_bg_ai/__init__.py`

**接口：**

```python
# main.py
import asyncio
from .config import load_config, AppConfig

async def run(config: AppConfig) -> None:
    """组装所有模块，启动主循环"""

def main() -> None:
    """CLI 入口点"""
    config = load_config()
    asyncio.run(run(config))
```

**依赖：** 所有模块（组装点）

---

## 6. PRD 功能 -> 模块映射表

| PRD 功能 | 功能ID | 所属模块 | 文件 |
|---------|--------|---------|------|
| 日志监听引擎 | F-01 | M-03 log_engine | watcher.py, dispatcher.py |
| 商店解析 | F-02 | M-04 log_parsers | shop_parser.py |
| 手牌解析 | F-03 | M-04 log_parsers | hand_parser.py |
| 战场解析 | F-04 | M-04 log_parsers | board_parser.py |
| 资源解析 | F-05 | M-04 log_parsers | resource_parser.py |
| 英雄解析 | F-06 | M-04 log_parsers | hero_parser.py |
| 回合解析 | F-07 | M-04 log_parsers | turn_parser.py |
| 对手解析 | F-08 | M-04 log_parsers | opponent_parser.py |
| 截图识别 | F-09 | M-05 screen | capturer.py, recognizer.py, regions.py |
| GameState 统一结构 | F-10 | M-06 state + M-02 models | game_state.py, manager.py, fusion.py |
| AI 决策引擎 | F-12 | M-07 ai | engine.py, turn_planner.py |
| 购买策略 | F-13 | M-07 ai | strategies/buy.py |
| 卖出策略 | F-14 | M-07 ai | strategies/sell.py |
| 刷新策略 | F-15 | M-07 ai | strategies/refresh.py |
| 升本策略 | F-16 | M-07 ai | strategies/upgrade.py |
| 站位策略 | F-17 | M-07 ai | strategies/position.py |
| 英雄技能 | F-18 | M-07 ai | strategies/hero_power.py |
| 阵容规划 | F-19 | M-07 ai | strategies/comp_plan.py |
| 三连策略 | F-20 | M-07 ai | strategies/triple.py |
| 英雄选择 | F-21 | M-07 ai | strategies/hero_select.py |
| 任务选择 | F-22 | M-07 ai | strategies/quest_select.py |
| 鼠标模拟 | F-23 | M-08 executor | mouse.py |
| 操作队列 | F-24 | M-08 executor | queue.py |
| 时序控制 | F-25 | M-08 executor | timing.py |
| 时间管理 | F-26 | M-08 executor | time_manager.py |
| 启停控制 | F-27 | M-09 control | controller.py |
| 快捷键 | F-28 | M-09 control | hotkeys.py |
| 手动接管 | F-29 | M-09 control | takeover.py |
| 日志读取恢复 | F-30 | M-10 recovery | log_recovery.py |
| 执行失败恢复 | F-31 | M-10 recovery | exec_recovery.py |
| 窗口丢失恢复 | F-32 | M-10 recovery | window_recovery.py |
| 断线恢复 | F-33 | M-10 recovery | disconnect_recovery.py |
| 状态面板 | F-34 | M-11 ui | dashboard.py |
| 日志展示 | F-35 | M-11 ui | logger_ui.py |
| 测试基础设施 | F-36 | 测试目录 | tests/ |
| 回放测试 | F-37 | 测试目录 | tests/integration/ |

---

## 7. 任务分配方案

### Task 0: 共享基础设施（Lead Dev 先完成）

| 内容 | 文件 |
|------|------|
| 项目脚手架 | `pyproject.toml`, `config.yaml`, `src/hs_bg_ai/__init__.py` |
| 配置系统 | `src/hs_bg_ai/config.py` |
| 数据模型 | `src/hs_bg_ai/models/*.py` (全部) |
| 事件总线 | `src/hs_bg_ai/core/events.py` |
| 错误定义 | `src/hs_bg_ai/core/errors.py` |
| 测试 fixtures | `tests/conftest.py`, `tests/fixtures/` |
| 静态数据 | `data/*.json` |

Task 0 完成后，两个开发者可以独立工作。

### Lead Dev 任务（核心/复杂模块）

| 任务 | 模块 | 文件 | 理由 |
|------|------|------|------|
| **T-L1: 核心协调器** | M-01 | `core/orchestrator.py` | 系统核心，掌控全局生命周期 |
| **T-L2: 日志监听引擎** | M-03 | `log_engine/*.py` | 数据入口，需要精确处理文件IO和并发 |
| **T-L3: 日志解析器** | M-04 | `log_parsers/*.py` | 需要逆向分析炉石日志格式，技术难度高 |
| **T-L4: GameState 管理** | M-06 | `state/*.py` | 核心状态管理，正确性要求极高 |
| **T-L5: AI 决策引擎** | M-07 | `ai/engine.py`, `ai/evaluator.py`, `ai/turn_planner.py`, `ai/strategies/*.py` | 最复杂模块，需要游戏理解 + 算法设计 |
| **T-L6: 入口组装** | M-13 | `main.py` | 全模块依赖注入 |
| **T-L7: 集成测试** | 测试 | `tests/integration/*.py` | 需要理解完整数据流 |

### Assistant Dev 任务（辅助/直接模块）

| 任务 | 模块 | 文件 | 理由 |
|------|------|------|------|
| **T-A1: 操作执行引擎** | M-08 | `executor/*.py` | 接口明确，独立性强 |
| **T-A2: 截图识别** | M-05 | `screen/*.py` | 备用方案，接口清晰 |
| **T-A3: 用户控制** | M-09 | `control/*.py` | 功能独立，逻辑简单 |
| **T-A4: 错误恢复** | M-10 | `recovery/*.py` | 模式统一，各恢复器独立 |
| **T-A5: UI 面板** | M-11 | `ui/*.py` | 纯展示层，无复杂逻辑 |
| **T-A6: 单元测试** | 测试 | `tests/unit/test_executor/`, `tests/unit/test_recovery/` | 测试自己开发的模块 |

### 文件所有权清单

```
Lead Dev 独占文件:
  src/hs_bg_ai/main.py
  src/hs_bg_ai/__init__.py
  src/hs_bg_ai/config.py
  src/hs_bg_ai/models/**
  src/hs_bg_ai/core/**
  src/hs_bg_ai/log_engine/**
  src/hs_bg_ai/log_parsers/**
  src/hs_bg_ai/state/**
  src/hs_bg_ai/ai/**
  tests/conftest.py
  tests/fixtures/**
  tests/integration/**
  tests/unit/test_log_parsers/**
  tests/unit/test_state/**
  tests/unit/test_ai/**
  data/**
  pyproject.toml
  config.yaml

Assistant Dev 独占文件:
  src/hs_bg_ai/executor/**
  src/hs_bg_ai/screen/**
  src/hs_bg_ai/control/**
  src/hs_bg_ai/recovery/**
  src/hs_bg_ai/ui/**
  tests/unit/test_executor/**
  tests/unit/test_recovery/**
```

**零重叠验证：** 两个文件列表无交集，可并行开发无合并冲突。

---

## 8. 跨模块接口契约

### 契约 C-01: LogWatcher -> LogDispatcher -> StateManager

```
数据流: 原始行 (str) -> LogEvent -> GameState 更新

LogWatcher 发布:
  EventBus.publish(EventType.LOG_LINE, data={"line": str, "timestamp": float})

LogDispatcher 消费 LOG_LINE，调用各 Parser，发布:
  EventBus.publish(EventType.STATE_UPDATED, data=LogEvent)

StateManager 消费 STATE_UPDATED，内部调用 apply_event(event)
```

### 契约 C-02: StateManager -> AIEngine

```python
# AI 引擎从 StateManager 获取只读快照
state: GameState = state_manager.get_state()  # 深拷贝，AI 可安全读取

# AI 引擎返回操作计划
plan: ActionPlan = ai_engine.decide(state)
```

**关键约束：** AI 引擎**绝不修改** GameState，只消费快照。

### 契约 C-03: AIEngine -> ActionQueue

```python
# Orchestrator 将 AI 的 ActionPlan 传给执行器
results: list[dict] = await action_queue.execute_plan(plan)

# 执行结果格式
result = {
    "action": GameAction,         # 原始操作
    "success": True/False,
    "error": "msg" | None,
    "duration_ms": int            # 实际耗时
}
```

### 契约 C-04: ActionQueue -> MouseController

```python
# ActionQueue 将 GameAction 转换为坐标操作
# 需要 CoordMapper 将游戏逻辑位置映射为屏幕坐标

class CoordMapper:
    """游戏逻辑位置 -> 屏幕像素坐标"""

    def shop_slot(self, index: int) -> tuple[int, int]:
        """商店第 N 个槽位的中心坐标"""

    def board_slot(self, index: int) -> tuple[int, int]:
        """场上第 N 个位置的中心坐标"""

    def hand_slot(self, index: int) -> tuple[int, int]:
        """手牌第 N 个位置的中心坐标"""

    def hero_power_button(self) -> tuple[int, int]: ...
    def refresh_button(self) -> tuple[int, int]: ...
    def upgrade_button(self) -> tuple[int, int]: ...
    def freeze_button(self) -> tuple[int, int]: ...
    def end_turn_button(self) -> tuple[int, int]: ...

# CoordMapper 属于 executor 模块（Assistant Dev），
# 放在 src/hs_bg_ai/executor/coords.py
```

**补充文件：** `src/hs_bg_ai/executor/coords.py` 归 Assistant Dev 所有。

### 契约 C-05: ScreenRecognizer -> DataFusion -> StateManager

```python
# 截图识别结果格式（dict，可合并到 GameState）
screen_data = {
    "shop": [{"name": str, "attack": int, "health": int}, ...],
    "board": [{"name": str, "attack": int, "health": int}, ...],
    "gold": int,
    "tavern_tier": int,
    "hero_health": int,
    "confidence": float,  # 识别置信度
}

# DataFusion 融合到 StateManager
fused_state = data_fusion.fuse(current_state, screen_data)
```

### 契约 C-06: Orchestrator <-> 所有模块（事件总线）

```python
# 所有模块间通信通过 EventBus，不直接调用
# 事件类型和数据格式：

EventType.LOG_LINE:       {"line": str, "timestamp": float}
EventType.STATE_UPDATED:  LogEvent 实例
EventType.TURN_START:     {"turn_number": int, "phase": str}
EventType.TURN_END:       {"turn_number": int}
EventType.GAME_START:     {"game_id": str}
EventType.GAME_OVER:      {"placement": int, "mmr_change": int}
EventType.ACTION_COMPLETED: {"action": GameAction, "success": bool}
EventType.ACTION_FAILED:  {"action": GameAction, "error": str}
EventType.ERROR:          {"error_type": str, "message": str, "recoverable": bool}
EventType.PAUSE_REQUESTED: {}
EventType.RESUME_REQUESTED: {}
```

### 契约 C-07: Recovery 模块 <-> Orchestrator

```python
# 恢复器由 Orchestrator 注册和调度
# 每个恢复器实现统一接口：

class BaseRecovery:
    async def detect(self) -> bool:     # 周期性调用
    async def recover(self) -> bool:    # detect=True 时调用

# Orchestrator 恢复流程：
# 1. 捕获异常 -> 判断类型 -> 选择对应 Recovery
# 2. 调用 recover()
# 3. 成功 -> 恢复正常流程
# 4. 失败且重试未超限 -> 重试
# 5. 失败且超限 -> 暂停 AI，通知用户
```

---

## 9. 关键设计决策

### 9.1 为什么用事件总线而非直接调用

模块间通过 EventBus 松耦合：
- 日志引擎不需要知道谁消费事件
- AI 引擎不关心数据来自日志还是截图
- 新增模块只需订阅/发布事件，不改现有代码
- **最重要：Lead Dev 和 Assistant Dev 的代码完全不直接 import 对方的模块**

### 9.2 为什么 GameState 用深拷贝快照

- AI 引擎在决策期间，GameState 可能被新的日志事件更新
- 深拷贝保证 AI 看到的是一致快照
- 避免竞态条件

### 9.3 为什么自计时而非读取游戏倒计时

- 日志中不可靠地输出倒计时
- OCR 读倒计时延迟太大
- 自计时 + 回合开始事件触发，精度足够（误差 < 2秒）

### 9.4 为什么 AI 策略用策略模式

- 每个策略独立开发和测试
- 可以逐个替换/升级策略
- TurnPlanner 编排策略顺序，不需要改策略内部逻辑

---

**Status:** DONE
**What I did:** 完成了完整的技术设计文档，包含 13 个模块的架构、接口、文件所有权和 7 个跨模块接口契约
**Files changed:** `docs/team-dev/tech-design.md` (新建)
**Concerns:** 日志解析器的具体正则模式需要实际分析炉石 output_log.txt 日志格式后才能确定，当前只定义了接口框架
