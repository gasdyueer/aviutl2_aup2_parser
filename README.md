# AviUtl2 AUP2 Parser

[![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-orange.svg)]()

一个功能强大的Python库，用于解析、处理和重建AviUtl (AviUtl2) AUP2项目文件。支持完整的数据结构解析、多场景管理、对象效果分析等高级功能，为AviUtl工作流提供便捷的程序接口。

## 🎯 特性亮点

- **完整解析**: 支持AUP2文件的全格式解析，包括项目设置、场景、对象、效果等所有区块
- **智能重建**: 从解析数据精确重建AUP2文件，保持格式兼容性
- **数据验证**: 内置验证机制，检查AUP2文件的结构完整性和数据有效性
- **丰富功能**:
  - 文件读取/保存接口
  - JSON格式导出解析结果
  - 解析摘要和统计信息
  - 按场景分组的对象查询
  - 多编码支持 (UTF-8, Shift_JIS等)
- **易于使用**: 提供面向对象的类接口和简化的函数接口
- **错误处理**: 完善的异常体系和详细的错误信息
- **性能优化**: 高效的解析算法，支持大文件处理

## 📋 系统要求

- **Python**: 3.7 或更高版本
- **操作系统**: Windows、macOS、Linux
- **依赖**: 仅标准库，无外部依赖（可选 json 更美化输出）

## 🔧 安装

### 方法1: Pip安装 (推荐)

```bash
# 克隆项目
git clone https://github.com/gasdyueer/aviutl2_aup2_parser.git
cd aviutl2_aup2_parser

# 安装为可编辑包
pip install -e .
```

### 方法2: 手动安装

```bash
# 复制项目文件到Python包路径
cp -r aviutl2_aup2_parser /path/to/python/packages/

# 或添加到PYTHONPATH
export PYTHONPATH="$PYTHONPATH:/path/to/aviutl2_aup2_parser"
```

### 方法3: 临时导入

如果需要临时使用：

```python
import sys
sys.path.append('/path/to/aviutl2_aup2_parser')
from aup2_parser import AUP2Parser
```

## 💡 快速开始

```python
from aup2_parser import AUP2Parser, parse, parse_file

# 基本用法：解析字符串
aup2_content = """
[project]
width=1920
height=1080

[0]
layer=1
frame=0:900
"""

parser = AUP2Parser(aup2_content)
data = parser.parse()

# 使用简化接口
data = parse(aup2_content)

# 解析文件
data = parse_file('path/to/file.aup2')

print(f"解析成功！包含 {len(data)} 个区块")
```

## 📖 详细使用方法

### 1. 初始化和基本解析

```python
from aup2_parser import AUP2Parser

# 从字符串创建解析器
parser = AUP2Parser(aup2_content)

# 从文件创建解析器
parser = AUP2Parser.from_file('project.aup2')

# 执行解析
data = parser.parse()

# 获取解析摘要
summary = parser.get_summary()
print(f"场景数: {summary['scenes']}, 对象数: {summary['objects']}")
```

### 2. 数据重建

```python
# 重建AUP2字符串
reconstructed = parser.reconstruct()

# 保存到文件
parser.save_to_file('output.aup2')

# 从字典重建 (不实例化类)
from aup2_parser import reconstruct_from_dict
aup2_string = reconstruct_from_dict(data)
```

### 3. 数据验证

```python
from aup2_parser import validate_aup2_file

is_valid, messages = validate_aup2_file('project.aup2')
if not is_valid:
    print("验证错误:", messages)
else:
    print("文件有效")
```

### 4. 高级查询

```python
# 获取特定场景的所有对象
objects = parser.get_objects_by_scene(0)

# 获取解析警告
warnings = data.get('_metadata', {}).get('warnings', [])

# 保存解析结果为JSON
parser.save_parsed_data('parsed.json')

# 从JSON重建AUP2
from aup2_parser import reconstruct_from_json
aup2_content = reconstruct_from_json('parsed.json')
```

### 5. 处理复杂项目

```python
# 多场景项目解析
parser = AUP2Parser.from_file('complex_project.aup2')
data = parser.parse()

# 遍历所有场景
for scene_key, scene_data in data.items():
    if scene_key.startswith('scene.'):
        print(f"场景 {scene_key}: {scene_data}")

# 分析效果分布
effects_count = 0
for obj_key, obj_data in data.items():
    if obj_key.startswith('object.'):
        if 'effects' in obj_data:
            effects_count += len(obj_data['effects'])

print(f"总效果数量: {effects_count}")
```

## 🔍 API 参考

### AUP2Parser类

#### 方法

- `__init__(aup2_content: str)` - 初始化解析器
- `parse() -> Dict[str, Any]` - 执行增强版解析，返回结构化字典
- `reconstruct() -> str` - 从解析数据重建AUP2格式字符串
- `validate_data_structure(data: Dict[str, Any]) -> List[str]` - 验证数据结构完整性
- `get_summary() -> Dict[str, Any]` - 获取解析摘要统计信息
- `get_objects_by_scene(scene_id: Optional[int] = None) -> List[Dict[str, Any]]` - 获取指定场景对象
- `save_to_file(filepath: Union[str, Path], encoding: str = 'utf-8') -> None` - 保存重建内容到文件
- `save_parsed_data(filepath: Union[str, Path], encoding: str = 'utf-8') -> None` - 保存解析数据为JSON

#### 类方法

- `AUP2Parser.from_file(filepath: Union[str, Path], encoding: str = 'utf-8') -> 'AUP2Parser'` - 从文件创建实例
- `AUP2Parser.reconstruct_from_dict(parsed_data: Dict[str, Any]) -> str` - 从字典重建AUP2字符串
- `AUP2Parser.reconstruct_from_json(json_filepath: Union[str, Path], encoding: str = 'utf-8') -> str` - 从JSON文件重建

### 便利函数

- `parse(content: str) -> Dict[str, Any]` - 简化接口：解析AUP2字符串
- `parse_file(filepath: Union[str, Path], encoding: str = 'utf-8') -> Dict[str, Any]` - 解析AUP2文件
- `validate_aup2_file(filepath: Union[str, Path], encoding: str = 'utf-8') -> Tuple[bool, List[str]]` - 验证AUP2文件并返回结果
- `reconstruct_from_dict(parsed_data: Dict[str, Any]) -> str` - 从字典重建AUP2字符串
- `convert_aup2_file(input_file: Union[str, Path], output_file: Union[str, Path], encoding: str = 'utf-8') -> None` - 转换AUP2文件格式

### 异常类

- `AUP2ParseError` - 解析过程的基础异常
- `AUP2ValidationError` - 数据验证失败异常
- `AUP2ReconstructionError` - 重建过程失败异常

## 📊 数据格式说明

解析后的数据以字典形式组织：

```python
{
    # 项目全局设置
    "project": {
        "width": 1920,
        "height": 1080,
        "framerate": 30
    },

    # 场景定义
    "scene.0": {
        "name": "Main Scene",
        "start": 0,
        "end": 900
    },

    # 对象定义 (按对象ID编号)
    "object.0": {
        "layer": 1,
        "frame": "0:900",
        "scene": 0,
        "effects": {
            "effect.0": {
                "_type": 1,
                "name": "Sample Effect",
                "param1": 100
            }
        }
    },

    # 元数据
    "_metadata": {
        "warnings": [],
        "line_count": 25,
        "sections_count": 5,
        "objects_count": 1
    }
}
```

## 🧪 运行示例

项目包含完整的使用示例：

```bash
# 克隆项目后
cd aviutl2_aup2_parser

# 运行基本示例
python example.py

# 运行测试脚本 (需要test.aup2文件)
python test_aup2_parser.py

# 命令行使用
python -m aup2_parser your_project.aup2
```

### 示例输出

```
=== AUP2 Parser 使用示例 ===

1. 解析AUP2字符串:
解析成功！包含 4 个区块
对象数量: 1

2. 使用便利函数:
简易接口 parse() 成功！

3. 读取AUP2文件:
从文件 parse() 成功！

4. 重建AUP2字符串:
重建成功！前几行:
[project]
width=1920
height=1080
framerate=30

5. 保存解析结果为JSON:
已保存到 parsed_data.json
```

## 📁 项目结构

```
aviutl2_aup2_parser/
├── __init__.py              # 包入口，导出主要接口
├── aup2_parser.py           # 核心解析器实现
├── example.py               # 使用示例脚本
├── test_aup2_parser.py      # 测试脚本
├── main.py                  # 命令行入口
├── README.md                # 项目文档（本文件）
├── test.aup2               # 测试文件示例
├── .gitignore              # Git忽略规则
└── .python-version         # Python版本指定
```

## 🐛 故障排除

### 常见问题

1. **编码错误 (UnicodeDecodeError)**
   ```python
   # 指定编码方式
   parser = AUP2Parser.from_file('file.aup2', encoding='shift_jis')
   ```

2. **文件格式不支持**
   - 确认是有效的AUP2文件
   - 检查文件是否损坏

3. **内存不足**
   - 大型项目建议分块处理
   - 使用 `get_summary()` 获取概览信息

4. **重建格式差异**
   - 重建后的格式可能与原文件略有差异
   - 功能上完全兼容，不会影响AviUtl读取

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

### 开发环境设置

```bash
git clone https://github.com/gasdyueer/aviutl2_aup2_parser.git
cd aviutl2_aup2_parser

# 创建虚拟环境 (推荐)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装开发依赖
pip install pytest pytest-cov  # 如有的话

# 运行测试
python test_aup2_parser.py
```

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙋‍♂️ 支持与反馈

遇到问题或有疑问？请：

- 查看[Issues](../../issues)页面提交Bug报告
- 发起[Pull Request](../../pulls)贡献代码
- 联系维护者获取支持

## ⚡ 更新日志

### v1.0.0
- 初始版本发布
- 支持完整的AUP2解析和重建
- 提供便捷的API接口
- 包含完整的使用示例和文档

---

*"让AviUtl项目文件解析变得简单而强大"*