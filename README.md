# AviUtl2 AUP2 Parser

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

解析、处理和重建 AviUtl (AviUtl2) AUP2 项目文件的 Python 库。零外部依赖，支持字节级精确往返。

## 特性

- **忠实往返**: 解析 → 重建 → 保存，与原始文件 **SHA256 完全一致**。保留原始数值格式（如 `100.00` 不变成 `100`）、区块顺序、换行符类型
- **完整解析**: 项目设置、多场景、对象、效果链、图层分组（`[layer.X]`）等全部区块
- **智能重建**: 修改解析数据中的值后重建，已修改属性使用新值，未修改部分精确回放原文
- **状态持久化**: `to_dict(include_records=True)` 导出含行记录的完整状态，`from_state()` 恢复后仍可字节精确往返
- **数据验证**: 检查结构完整性（缺少 project / layer / frame 等）
- **序列化支持**: 解析结果导出 JSON，从 JSON 反向重建 AUP2。含行记录时可字节精确
- **多编码**: UTF-8、Shift_JIS 等
- **无外部依赖**: 仅 Python 标准库

## AI Agent 使用

**以下命令在项目根目录执行，无需 pip install。**

### 公共约定

- 所有子命令支持 `-e, --encoding ENC` 指定编码（默认 `utf-8`）
- 退出码 `0` = 成功，`1` = 失败，`2` = 参数错误
- 正常输出到 stdout，错误/警告输出到 stderr

### parse — 解析 AUP2 为 JSON

```
python main.py parse <file> [-e ENC] [-o OUTPUT] [--no-pretty] [--include-records]
python -m aviutl2_aup2_parser parse <file> [...]
```

| 选项 | 说明 |
|---|---|
| `file` | AUP2 文件路径 |
| `-o OUTPUT` | 写入文件，默认 stdout |
| `--no-pretty` | 紧凑 JSON（无缩进） |
| `--include-records` | 包含 `_line_records`，输出格式变为 `{"data":{...},"_line_records":[...]}` |

### info — 结构摘要

```
python main.py info <file> [-e ENC] [--json]
```

| 选项 | 说明 |
|---|---|
| `--json` | 机器可读 JSON，否则人类可读表格 |

### validate — 完整性验证

```
python main.py validate <file> [-e ENC] [--quiet]
```

| 选项 | 说明 |
|---|---|
| `--quiet` | 不输出，仅退出码 |

### convert — AUP2 ↔ JSON

```
python main.py convert <input> <output> [-e ENC]
```

根据扩展名判断方向：`.aup2` → `.json` / `.json` → `.aup2` / `.aup2` → `.aup2`（逻辑重建）。JSON → AUP2 走逻辑重建，非字节精确。

### rebuild — 往返 SHA256 对比

```
python main.py rebuild <file> [-e ENC] [-o OUTPUT]
```

解析 → 重建 → 对比 SHA256。`-o` 同时写入重建文件。不匹配时退出码 1。

## 系统要求

- **Python**: 3.11 或更高版本
- **操作系统**: Windows / macOS / Linux
- **依赖**: 无

## 安装

```bash
git clone https://github.com/gasdyueer/aviutl2_aup2_parser.git
cd aviutl2_aup2_parser
pip install -e .
```

或直接复制 `aup2_parser.py` 到项目中导入使用。

## CLI 使用

`pip install -e .` 后即可使用 `aup2` 命令。零外部依赖，仅需 Python 3.11+。

### 子命令一览

| 子命令 | 功能 | 典型用法 |
|---|---|---|
| `parse` | 解析 AUP2 为 JSON | `aup2 parse project.aup2` |
| `info` | 查看文件结构摘要 | `aup2 info project.aup2` |
| `validate` | 验证文件完整性 | `aup2 validate project.aup2` |
| `convert` | AUP2 ↔ JSON 互转 | `aup2 convert in.aup2 out.json` |
| `rebuild` | 往返重建校验 | `aup2 rebuild project.aup2` |

### parse — 解析为 JSON

```
aup2 parse <file> [-e ENC] [-o OUTPUT] [--no-pretty] [--include-records]
```

| 选项 | 说明 |
|---|---|
| `file` | 必填，AUP2 文件路径 |
| `-e, --encoding` | 文件编码，默认 `utf-8` |
| `-o, --output` | 写入 JSON 到文件，默认输出到 stdout |
| `--no-pretty` | 紧凑 JSON，不带缩进 |
| `--include-records` | 包含 `_line_records`，用于往返状态持久化 |

```bash
# 输出到终端
aup2 parse project.aup2

# 紧凑输出，写入文件
aup2 parse project.aup2 --no-pretty -o parsed.json

# 持久化完整状态（含行记录，可后续精确重建）
aup2 parse project.aup2 --include-records -o state.json
```

### info — 结构摘要

```
aup2 info <file> [-e ENC] [--json]
```

| 选项 | 说明 |
|---|---|
| `file` | 必填，AUP2 文件路径 |
| `--json` | 输出机器可读 JSON，默认人类可读表格 |

```bash
aup2 info project.aup2
# File:         project.aup2
# Scenes:       17
# Objects:      247
# ...

aup2 info project.aup2 --json
# {"total_sections": 268, "scenes": 17, ...}
```

### validate — 完整性验证

```
aup2 validate <file> [-e ENC] [--quiet]
```

| 选项 | 说明 |
|---|---|
| `file` | 必填，AUP2 文件路径 |
| `--quiet` | 不输出错误信息，仅通过退出码区分结果 |

退出码：`0` = 有效，`1` = 无效（含解析失败或结构错误）。错误信息输出到 stderr。

```bash
aup2 validate project.aup2 && echo "有效"
aup2 validate broken.aup2 --quiet || echo "损坏"
```

### convert — 格式互转

```
aup2 convert <input> <output> [-e ENC]
```

根据扩展名自动判断转换方向：

| 输入 | 输出 | 方向 |
|---|---|---|
| `.aup2` | `.json` | AUP2 → JSON |
| `.json` | `.aup2` | JSON → AUP2 |
| `.aup2` | `.aup2` | 重建（逻辑重建，非字节精确） |

```bash
# AUP2 → JSON
aup2 convert project.aup2 project.json

# JSON → AUP2
aup2 convert project.json rebuilt.aup2
```

**注意**：JSON → AUP2 为逻辑重建（结构正确但数值格式可能略有差异）。如需字节精确往返，使用 `save_parsed_data(include_records=True)` + `load_state()` Python API。

### rebuild — 往返验证

```
aup2 rebuild <file> [-e ENC] [-o OUTPUT]
```

解析 → 重建，对比原始文件与重建文件的 SHA256。输出对比结果到 stdout。

| 选项 | 说明 |
|---|---|
| `file` | 必填，AUP2 文件路径 |
| `-o, --output` | 将重建结果写入指定文件 |

```bash
aup2 rebuild project.aup2
# Original file:   project.aup2
# Original SHA256: 499a52c2...
# Rebuilt  SHA256: 499a52c2...
# Round-trip:      YES

# 写入重建文件
aup2 rebuild project.aup2 -o verified.aup2
```

### 公共选项与退出码

- **`-e, --encoding`**：所有子命令均支持，指定文件编码（默认 `utf-8`）.
- **退出码**：`0` = 成功，`1` = 解析/验证/重建失败或文件未找到，`2` = 参数错误.

### 模块调用

未安装时可直接通过 Python 运行：

```bash
python main.py parse project.aup2
python -m aviutl2_aup2_parser info project.aup2
```
## 快速开始

```python
from aup2_parser import AUP2Parser, parse_file

# 解析文件
data = parse_file("project.aup2")
print(f"场景数: {len([k for k in data if k.startswith('scene.')])}")
print(f"对象数: {len([k for k in data if k.startswith('object.')])}")

# 解析 → 修改 → 重建 → 保存
parser = AUP2Parser.from_file("project.aup2")
data = parser.parse()
data["object.0"]["layer"] = 5       # 修改
parser.reconstruct()                 # 重建（已修改属性用新值，其余精确回放）
parser.save_to_file("modified.aup2") # 保存
```

## 数据格式

解析后的字典结构：

```python
{
    "project": {
        "file": "C:\\path\\to\\project.aup2",
        "display.scene": 0
    },
    "scene.0": {
        "scene": 0,
        "name": "Root",
        "video.width": 1920,
        "video.height": 1080,
        "video.rate": 30,
        "video.scale": 1,
        "audio.rate": 48000,
        "cursor.frame": 30,
        "display.frame": 0,
        "display.layer": 0,
        "display.zoom": 100000,
        "display.order": 0,
        "display.camera": ""
    },
    "object.0": {
        "layer": 0,
        "frame": [0, 411],
        "effects": {
            "effect.0": {
                "effect.name": "音声ファイル",
                "再生位置": [0.0, 13.723, "再生範囲", 0],
                "再生速度": 100.0,
                "ファイル": "E:\\audio.mp3"
            },
            "effect.1": {
                "effect.name": "音声再生",
                "音量": 100.0
            }
        }
    },
    "_metadata": {
        "warnings": [...],
        "line_count": 8609,
        "sections_count": 265,
        "objects_count": 247
    }
}
```

### 值类型自动推断

| 原始值 | 解析结果 |
|--------|----------|
| `1920` | `int` |
| `100.00` | `float` |
| `0,411` | `[0, 411]` (int list) |
| `0.000,13.723` | `[0.0, 13.723]` (float list) |
| `直線移動,0\|1,0,1,0` | `str` (混合类型，保持字符串) |
| `` (空) | `""` |

## API 参考

### AUP2Parser 类

#### 实例方法

| 方法 | 说明 |
|------|------|
| `parse() -> dict` | 解析并返回结构化字典（含 `_metadata`） |
| `reconstruct() -> str` | 从当前数据重建 AUP2 字符串。有原始记录时字节精确，无记录时走逻辑重建 |
| `save_to_file(path, encoding='utf-8')` | 重建并写入文件，保留原始换行格式 |
| `save_parsed_data(path, encoding='utf-8', include_records=False)` | 解析结果导出为 JSON；`include_records=True` 时含行记录以支持字节精确恢复 |
| `to_dict(include_records=False) -> dict` | 导出完整解析器状态字典（data + 换行信息 + 可选行记录） |
| `get_summary() -> dict` | 返回统计信息：场景数、对象数、图层分布、警告数 |
| `get_objects_by_scene(scene_id=None) -> list` | 按场景查询对象（id / layer / frame / has_effects） |
| `validate_data_structure(data) -> list` | 验证结构完整性，返回错误列表 |

#### 类方法

| 方法 | 说明 |
|------|------|
| `from_file(path, encoding='utf-8')` | 从文件创建解析器实例（二进制读取以检测换行符） |
| `reconstruct_from_dict(data) -> str` | 从字典重建 AUP2（走逻辑重建路径） |
| `reconstruct_from_json(path, encoding='utf-8') -> str` | 从 JSON 文件读取并重建 |
| `save_reconstructed_aup2(json_in, aup2_out, encoding='utf-8')` | JSON → AUP2 文件 |
| `from_state(state) -> AUP2Parser` | 从 `to_dict(include_records=True)` 产出的状态字典恢复解析器，保留字节精确往返能力 |
| `load_state(filepath, encoding='utf-8') -> AUP2Parser` | 从 JSON 文件加载完整解析器状态 |

### 模块级便捷函数

```python
from aup2_parser import parse, parse_file
from aup2_parser import validate_aup2_file, convert_aup2_file
from aup2_parser import save_aup2_state, load_aup2_state

parse(content)                       # 字符串 → dict
parse_file(path, encoding)           # 文件 → dict
validate_aup2_file(path)             # → (bool, [errors...])
convert_aup2_file(in, out)           # 读取 + 解析 + 重建 + 写入（格式化）
save_aup2_state(in, out, encoding)   # 解析AUP2并保存完整状态JSON（含行记录）
load_aup2_state(path, encoding)      # 从状态JSON加载AUP2Parser（支持字节精确往返）
```

### 异常类

- `AUP2ParseError` — 解析失败
- `AUP2ValidationError` — 数据验证失败
- `AUP2ReconstructionError` — 重建失败

## 往返保证

`AUP2Parser.from_file()` → `.parse()` → `.reconstruct()` → `.save_to_file()` 产生与原始文件 **SHA256 完全一致** 的输出，前提是解析后未修改数据。

已验证文件：

| 文件 | 大小 | 行数 | 往返 |
|------|------|------|------|
| `test.aup2` | 2.8 KB | 173 | SHA256 一致 |
| `simple.aup2` | 41 KB | 2,244 | SHA256 一致 |
| `complex.aup2` | 156 KB | 8,609 | SHA256 一致 |

工作原理：解析时同步记录每一行的原始文本和结构化路径（`LineRecord`），重建时优先回放原始记录；修改过的属性自动检测并使用新值格式化输出。

### 跨文件往返（状态持久化）

通过 `to_dict(include_records=True)` 将行记录一起导出，经 JSON 文件或数据库存储后，用 `from_state()` 恢复，仍可继续字节精确往返：

```python
parser = AUP2Parser.from_file("project.aup2")
parser.parse()

# 导出完整状态（含行记录）
state_json_path = "project_state.json"
parser.save_parsed_data(state_json_path, include_records=True)

# 从状态恢复并字节精确重建
restored = AUP2Parser.load_state(state_json_path)
restored.reconstruct()  # → SHA256 与原始文件一致
```
## 修改数据后重建

```python
parser = AUP2Parser.from_file("project.aup2")
data = parser.parse()

# 修改已有属性 → 重建时用新值
data["object.5"]["layer"] = 10

# 新增属性 → 不会出现在输出中（没有对应的 LineRecord）
# 如需新增，需在 data 和 parser._line_records 中同步添加

reconstructed = parser.reconstruct()  # layer=5 变成 layer=10，其余不变
```

## 项目结构

```
aviutl2_aup2_parser/
├── aup2_parser.py          # 核心实现（~920 行）
├── __init__.py              # 包导出 + 便捷函数
├── example.py               # 使用示例
├── test_aup2_parser.py      # 基础测试脚本
├── test_roundtrip_state.py  # 往返持久化验证测试
├── main.py                  # 命令行入口
├── pyproject.toml           # 项目配置
├── README.md
├── test.aup2                # 测试文件（173 行）
├── simple.aup2              # 中等复杂度（2244 行，4 场景，94 对象）
└── complex.aup2             # 复杂项目（8609 行，17 场景，247 对象）
```

## 故障排除

**编码错误**
```python
parser = AUP2Parser.from_file("file.aup2", encoding="shift_jis")
```

**修改后新增属性不生效**
修改数据后重建走 `_line_records` 路径。已存在属性的值变更会被检测并应用；新增属性需同时向 `parser._line_records` 追加对应的 `LineRecord`。

**从 JSON/字典重建**
`reconstruct_from_dict()` 和 `reconstruct_from_json()` 不含行记录时走逻辑重建路径（结构正确但数值格式可能不同）。
如需字节精确，使用 `save_parsed_data(include_records=True)` + `load_state()` 代替。

## 许可证

MIT License

## 更新日志

### v1.3.0
- 新增：CLI 命令行工具 — `parse`、`info`、`validate`、`convert`、`rebuild` 五个子命令
- 新增：`python main.py` 和 `python -m aviutl2_aup2_parser` 两种入口方式
- 新增：`pyproject.toml` 注册 `aup2` 命令入口点
- 新增：`__main__.py` 模块入口

### v1.2.0
- 新增：往返状态持久化 — `to_dict(include_records=True)` / `from_state()` / `load_state()`
- 新增：`save_parsed_data(include_records=True)` 导出含行记录的完整状态 JSON
- 新增：模块级 `save_aup2_state()` / `load_aup2_state()` 便捷函数
- 修复：`parse()` 中 `content.strip()` 改用检测到的换行符分割，避免丢失前导空行
- 修复：`reconstruct_from_dict()` 消除 `cls("dummy")` hack，改用 `__new__` + `_init_fields()`

### v1.1.0
- 实现忠实往返：解析 → 重建 → 保存字节级完全一致
- 新增 `LineRecord` 行记录机制
- 修复：场景排序从字典序改为数字序
- 修复：`[project]` 中 `display.scene` 不再丢失
- 修复：`[layer.X]` 等非标准区块正确保留
- 修复：`save_to_file` 换行符处理
- 修复：浮点数值格式保留（`100.00` 不变成 `100`）

### v1.0.0
- 初始发布
- AUP2 解析、重建、验证
- JSON 序列化支持
