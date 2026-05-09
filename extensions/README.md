# Extensions

基于 `AUP2Parser` 的领域专用扩展脚本，完成特定的 AUP2 结构变换，无需修改核心库。

## 编写扩展

扩展脚本需确保能从项目根目录导入 `aup2_parser`。推荐模板：

```python
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 上
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from aup2_parser import AUP2Parser
```

核心工作流：

1. `AUP2Parser.from_file()` 解析源文件
2. 操作 `data` 字典（`parser.parse()` 的返回值）构建新的数据结构
3. `AUP2Parser.reconstruct_from_dict()` 生成 AUP2 文本
4. 写入输出文件，使用 `newline=''` 保留所需换行格式

如需 `\r\n` 换行（AviUtl 默认），手动构造 `AUP2Parser` 实例并设置 `_line_ending`：

```python
from collections import defaultdict

parser = AUP2Parser.__new__(AUP2Parser)
parser._init_fields()
parser._line_ending = '\r\n'
parser._trailing_newline = True
parser.data = defaultdict(dict, output_dict)
result = parser.reconstruct()
```

## 可用扩展

| 扩展 | 功能 |
|------|------|
| `convert_flat_to_scene.py` | 将扁平 AUP2（1 场景，N 个对象全在 Layer 0）转换为场景引用 + 分层架构（1+N 场景，3N 对象） |

### convert_flat_to_scene.py

```bash
python extensions/convert_flat_to_scene.py test2.aup2 -o output.aup2
```

**变换规则**（对每个输入片段，共 N 个）：

1. 子场景 `scene.{i+1}` — 含 1 个 `動画ファイル` 对象（frame=[0, dur]，完整复制源对象的效果参数）
2. 主合成 Layer 0 — `シーン`（场景引用）对象（frame=[start, end]，引用子场景，复制源对象的 `映像再生` 参数，添加 `シーン=scene_id` 和 `ループ再生=0`）
3. 主合成 Layer (i+1) — `動画ファイル` 对象（frame=[start, end]，完整复制源对象）
