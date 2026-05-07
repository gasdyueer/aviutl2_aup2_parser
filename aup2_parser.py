import re
import json
from collections import defaultdict, namedtuple
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path


# 自定义异常类
class AUP2ParseError(Exception):
    """AUP2文件解析错误的基础异常类"""
    pass


class AUP2ValidationError(AUP2ParseError):
    """AUP2数据验证错误"""
    pass


class AUP2ReconstructionError(AUP2ParseError):
    """AUP2文件重建错误"""
    pass


# 行记录用于忠实往返重建
LineRecord = namedtuple('LineRecord', ['type', 'path', 'key', 'parsed', 'raw'])
# type: 'section' | 'kv'
# path: tuple of keys to navigate self.data to the section (e.g. ('project',), ('object.0','effects','effect.0'))
# key: property key (None for 'section')
# parsed: parsed value (None for 'section')
# raw: original line text

class AUP2Parser:
    """
    增强版AviUtl AUP2 文件解析器类。

    用于解析AUP2文件内容为结构化的Python字典，并提供重建、验证等功能。
    支持多场景、多图层对象的完整解析与重建。

    Attributes:
        aup2_content (str): 输入的AUP2文件内容
        data (dict): 解析后的结构化数据
        current_section (str): 当前解析的主区块
        current_subsection (str): 当前解析的子区块
        line_number (int): 当前解析的行号（用于错误定位）
        warnings (List[str]): 解析过程中的警告信息
    """

    def __init__(self, aup2_content: str):
        """
        初始化解析器。

        Args:
            aup2_content (str): AUP2 文件的内容。

        Raises:
            AUP2ParseError: 如果输入内容无效
        """
        if not isinstance(aup2_content, str):
            raise AUP2ParseError("AUP2内容必须是字符串")
        if not aup2_content.strip():
            raise AUP2ParseError("AUP2内容不能为空")

        self.aup2_content = aup2_content
        self._init_fields()

    def _init_fields(self) -> None:
        """初始化所有实例字段为默认值。"""
        self.data = defaultdict(dict)
        self.current_section = None
        self.current_subsection = None
        self.line_number = 0
        self.warnings: List[str] = []
        self._line_records: List[LineRecord] = []
        self._current_path: Optional[Tuple[str, ...]] = None
        self._line_ending: str = '\n'
        self._trailing_newline: bool = True
    def _reset_state(self) -> None:
        """重置当前状态。"""
        self.current_section = None
        self.current_subsection = None
        self.line_number = 0
        self._current_path = None
        self._line_records = []
        self._trailing_newline = True

    def _parse_value(self, value: str) -> Union[int, float, List[Union[int, float]], str]:
        """
        增强的类型解析方法。

        Args:
            value (str): 要解析的值。

        Returns:
            Union[int, float, List[Union[int, float]], str]: 解析后的值。

        Raises:
            AUP2ParseError: 如果值格式无效
        """
        value = value.strip()

        # 整数
        if re.fullmatch(r'\d+', value):
            return int(value)

        # 浮点数（支持负数和更多格式）
        if re.fullmatch(r'-?\d+\.\d+', value):
            return float(value)

        # 数字列表（支持整数和浮点数用逗号分隔）
        if ',' in value:
            parts = [part.strip() for part in value.split(',')]
            try:
                parsed_numbers = []
                for part in parts:
                    if re.fullmatch(r'\d+', part):
                        parsed_numbers.append(int(part))
                    elif re.fullmatch(r'-?\d+\.\d+', part):
                        parsed_numbers.append(float(part))
                    else:
                        raise ValueError(f"Invalid number format: {part}")
                # 如果全都是整数，返回 int 列表；否则返回 float 列表
                if all(isinstance(n, int) for n in parsed_numbers):
                    return parsed_numbers
                else:
                    return [float(n) if isinstance(n, int) else n for n in parsed_numbers]
            except ValueError:
                self.warnings.append(f"行 {self.line_number}: 发现可能无效的数字列表: {value}")

        # 处理特殊值（空值、布尔值等）
        if value == '':
            return ''

        # 默认返回字符串
        return value

    def _parse_section(self, line: str) -> None:
        """
        解析主区块（增强版）。

        Args:
            line (str): 要解析的行。

        Raises:
            AUP2ParseError: 如果区块格式无效
        """
        section_match = re.match(r'^\[(project|scene\.(\d+)|(\d+))\]$', line)
        if section_match:
            section_type = section_match.group(1)

            if section_type == 'project':
                current_section_name = 'project'
            elif section_type.startswith('scene.'):
                scene_id = section_match.group(2)
                current_section_name = f'scene.{scene_id}'
                # 验证场景ID
                if not scene_id.isdigit():
                    raise AUP2ParseError(f"行 {self.line_number}: 无效的场景ID: {scene_id}")
            elif section_match.group(3):  # 对象ID
                obj_id = section_match.group(3)
                current_section_name = f'object.{obj_id}'
                # 验证对象ID
                if not obj_id.isdigit():
                    raise AUP2ParseError(f"行 {self.line_number}: 无效的对象ID: {obj_id}")

            self.data[current_section_name] = {}
            self.current_section = self.data[current_section_name]
            self.current_subsection = None
            self._current_path = (current_section_name,)
            self._line_records.append(LineRecord('section', self._current_path, None, None, line))
        else:
            # Unknown section type — preserve as generic section for round-trip
            inner = line[1:-1].strip()
            if inner:
                self.data[inner] = {}
                self.current_section = self.data[inner]
                self.current_subsection = None
                self._current_path = (inner,)
                self._line_records.append(LineRecord('section', self._current_path, None, None, line))
            else:
                self.warnings.append(f"行 {self.line_number}: 无法识别的区块: {line}")
    def _parse_subsection(self, line: str) -> None:
        """
        解析子区块（效果区块）（增强版）。

        Args:
            line (str): 要解析的行。

        Raises:
            AUP2ParseError: 如果子区块格式无效
        """
        subsection_match = re.match(r'^\[(\d+)\.(\d+)\]$', line)
        if subsection_match:
            obj_id = int(subsection_match.group(1))
            effect_id = int(subsection_match.group(2))

            obj_section_name = f'object.{obj_id}'
            effect_section_name = f'effect.{effect_id}'

            # 检查父对象是否存在
            if obj_section_name not in self.data:
                self.warnings.append(f"行 {self.line_number}: 效果区块 {line} 的父对象 {obj_section_name} 不存在，已自动创建")
                self.data[obj_section_name] = {}

            # 初始化effects字典（如果不存在）
            if 'effects' not in self.data[obj_section_name]:
                self.data[obj_section_name]['effects'] = {}

            # 创建效果数据结构
            self.data[obj_section_name]['effects'][effect_section_name] = {}
            self.current_subsection = self.data[obj_section_name]['effects'][effect_section_name]
            self.current_section = None
            self._current_path = (obj_section_name, 'effects', effect_section_name)
            self._line_records.append(LineRecord('section', self._current_path, None, None, line))
        else:
            self.warnings.append(f"行 {self.line_number}: 无法识别的子区块: {line}")

    def _parse_key_value(self, line: str) -> None:
        """
        解析键值对（增强版）。

        Args:
            line (str): 要解析的行。
        """
        if '=' in line:
            try:
                key, value = line.split('=', 1)
                key = key.strip()
                parsed_value = self._parse_value(value)

                if self.current_subsection is not None:
                    self.current_subsection[key] = parsed_value
                elif self.current_section is not None:
                    self.current_section[key] = parsed_value
                else:
                    self.warnings.append(f"行 {self.line_number}: 键值对在无效位置被忽略: {line}")

                # 记录原始行用于往返重建
                self._line_records.append(LineRecord('kv', self._current_path, key, parsed_value, line))
            except ValueError as e:
                self.warnings.append(f"行 {self.line_number}: 解析键值对失败: {line} - {e}")
                self._line_records.append(LineRecord('kv', self._current_path, line, None, line))
        else:
            self.warnings.append(f"行 {self.line_number}: 发现不包含等号的行: {line}")
            self._line_records.append(LineRecord('kv', self._current_path, line, None, line))

    def parse(self) -> Dict[str, Any]:
        """
        执行增强版解析并返回结构化结果字典。

        Returns:
            Dict[str, Any]: 解析后包含元数据的字典。

        Raises:
            AUP2ParseError: 如果解析过程中发生严重错误
        """
        try:
            self._reset_state()
            # Detect line ending for exact round-trip
            content = self.aup2_content
            if '\r\n' in content:
                self._line_ending = '\r\n'
            elif '\r' in content:
                self._line_ending = '\r'
            else:
                self._line_ending = '\n'
            # Track whether original content had trailing newline
            self._trailing_newline = content.endswith('\n') or content.endswith('\r')
            # 使用检测到的换行符分割，避免 content.strip() 丢弃前导空行
            lines = content.split(self._line_ending)
            # 移除末尾分隔符产生的空串
            if lines and lines[-1] == '':
                lines.pop()

            for self.line_number, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue

                # 按优先级尝试解析不同类型的行
                if re.match(r'^\[.*\]$', line):
                    # 检查是否是效果区块 [Y.Z]
                    if re.match(r'^\[\d+\.\d+\]$', line):
                        self._parse_subsection(line)
                    # 检查是否是场景区块 [scene.X]
                    elif re.match(r'^\[scene\.\d+\]$', line):
                        self._parse_section(line)
                    # 检查是否是对象区块 [Y] 或项目区块 [project]
                    else:
                        self._parse_section(line)
                else:
                    # 键值对
                    if self.current_section is not None or self.current_subsection is not None:
                        self._parse_key_value(line)

            # 验证基本结构
            if 'project' not in self.data:
                self.warnings.append("警告: 未发现project区块")
            if not any(k.startswith('object.') for k in self.data):
                self.warnings.append("警告: 未发现任何对象")

            result = dict(self.data)
            result['_metadata'] = {
                'warnings': self.warnings,
                'line_count': self.line_number,
                'sections_count': len([k for k in result if not k.startswith('_')]),
                'objects_count': len([k for k in result if k.startswith('object.')])
            }

            return result

        except Exception as e:
            raise AUP2ParseError(f"解析第{self.line_number}行时出现错误: {e}") from e

    def _convert_value_to_aup2_string(self, value: Any) -> str:
        """
        增强版的值转字符串方法。

        Args:
            value: 要转换的值

        Returns:
            str: 转换后的AUP2字符串
        """
        if isinstance(value, int):
            return str(value)
        elif isinstance(value, float):
            if value.is_integer():
                return str(int(value))
            else:
                return f"{value:.3f}".rstrip('0').rstrip('.')
        elif isinstance(value, list) and all(isinstance(i, (int, float)) for i in value):
            return ",".join(self._convert_value_to_aup2_string(v) for v in value)
        elif isinstance(value, bool):
            return "1" if value else "0"
        elif value is None or value == '':
            return ""
        else:
            return str(value)

    def validate_data_structure(self, data: Dict[str, Any]) -> List[str]:
        """
        验证数据结构的完整性。

        Args:
            data (Dict[str, Any]): 要验证的数据

        Returns:
            List[str]: 验证错误列表
        """
        errors = []

        # 检查基本结构
        if 'project' not in data:
            errors.append("缺少project区块")

        # 检查对象完整性
        objects = [k for k in data if k.startswith('object.')]
        if not objects:
            errors.append("没有找到任何对象")
        else:
            for obj_key in objects:
                obj = data[obj_key]
                if 'layer' not in obj:
                    errors.append(f"对象 {obj_key} 缺少layer属性")
                if 'frame' not in obj:
                    errors.append(f"对象 {obj_key} 缺少frame属性")

                # 检查效果结构
                if 'effects' in obj:
                    effects = obj['effects']
                    if not isinstance(effects, dict):
                        errors.append(f"对象 {obj_key} 的effects应为字典")
                    else:
                        for effect_key, effect_data in effects.items():
                            if not isinstance(effect_data, dict):
                                errors.append(f"对象 {obj_key} 的效果 {effect_key} 数据应为字典")

        return errors

    def reconstruct(self) -> str:
        """
        从解析后的字典重建 AUP2 格式的字符串（增强版）。

        Returns:
            str: 重建的 AUP2 字符串。

        Raises:
            AUP2ReconstructionError: 如果重建过程中发生错误
        """
        try:
            # 如果数据还没有解析，先解析
            if not self.data:
                self.parse()

            # 验证数据结构 (skip for exact round-trip since line records guarantee structure)
            clean_data = dict(self.data)
            if '_metadata' in clean_data:
                del clean_data['_metadata']

            if not self._line_records:
                errors = self.validate_data_structure(clean_data)
                if errors:
                    raise AUP2ReconstructionError(f"数据结构验证失败: {'; '.join(errors)}")

            aup2_lines = []
            parsed_data = clean_data

            # 生成 AUP2 行
            self._build_aup2_lines(aup2_lines, parsed_data)
            result = self._line_ending.join(aup2_lines)
            if self._trailing_newline:
                result += self._line_ending
            return result

        except Exception as e:
            raise AUP2ReconstructionError(f"重建失败: {e}") from e

    def _build_aup2_lines(self, aup2_lines, parsed_data):
        """Build AUP2 lines from parsed data.
        
        Uses original line records for exact round-trip when available.
        Falls back to logical reconstruction when reconstructing from dict/JSON.
        """
        if self._line_records:
            self._build_aup2_lines_from_records(aup2_lines)
        else:
            self._build_aup2_lines_legacy(aup2_lines, parsed_data)

    def _build_aup2_lines_from_records(self, aup2_lines):
        """Reconstruct AUP2 output from original line records for exact round-trip."""
        for record in self._line_records:
            if record.type == 'section':
                aup2_lines.append(record.raw)
            elif record.type == 'kv':
                # Navigate to current value in self.data
                section = self.data
                try:
                    for part in record.path:
                        section = section[part]
                    current_value = section.get(record.key)
                except (KeyError, TypeError):
                    current_value = None
                
                if record.parsed is None:
                    # Value was not parseable, preserve original raw text
                    aup2_lines.append(record.raw)
                elif current_value is not None and current_value != record.parsed:
                    # Value was modified, format with converter
                    aup2_lines.append("{}={}".format(record.key,
                        self._convert_value_to_aup2_string(current_value)))
                else:
                    # Value unchanged, use original text for exact reproduction
                    aup2_lines.append(record.raw)

    def _build_aup2_lines_legacy(self, aup2_lines, parsed_data):
        """Legacy logical reconstruction used when no line records available.
        
        Rebuilds AUP2 structure from the flat parsed data dictionary.
        Sections are sorted by type then ID; values use canonical formatting.
        """
        # 1. [project] block — output all properties as-is
        if "project" in parsed_data:
            aup2_lines.append("[project]")
            for key, value in parsed_data["project"].items():
                aup2_lines.append("{}={}".format(key, self._convert_value_to_aup2_string(value)))

        # 2. [scene.X] blocks sorted numerically by scene ID
        def _scene_sort_key(k):
            return int(k.split('.')[1])
        scene_keys = sorted(
            [k for k in parsed_data if k.startswith("scene.")],
            key=_scene_sort_key
        )
        for scene_key in scene_keys:
            aup2_lines.append("[{}]".format(scene_key))
            for key, value in parsed_data[scene_key].items():
                aup2_lines.append("{}={}".format(key, self._convert_value_to_aup2_string(value)))

            scene_id = int(scene_key.split('.')[1])

            # Find objects belonging to this scene
            scene_objects = []
            for obj_key in [k for k in parsed_data if k.startswith("object.")]:
                obj_id = int(obj_key.split('.')[1])
                obj_data = parsed_data[obj_key]
                obj_scene = obj_data.get('scene', 0)
                if obj_scene == scene_id:
                    scene_objects.append((obj_id, obj_key, obj_data))

            for obj_id, obj_key, obj_data in sorted(scene_objects):
                aup2_lines.append("[{}]".format(obj_id))
                for key in ["layer", "frame", "focus"]:
                    if key in obj_data:
                        aup2_lines.append("{}={}".format(key,
                            self._convert_value_to_aup2_string(obj_data[key])))
                for key, value in obj_data.items():
                    if key not in ["layer", "frame", "focus", "effects"]:
                        aup2_lines.append("{}={}".format(key,
                            self._convert_value_to_aup2_string(value)))

                if "effects" in obj_data:
                    effect_ids = sorted(
                        [int(k.split('.')[1]) for k in obj_data["effects"]]
                    )
                    for effect_id in effect_ids:
                        effect_key = "effect.{}".format(effect_id)
                        effect_data = obj_data["effects"][effect_key]
                        aup2_lines.append("[{}.{}]".format(obj_id, effect_id))
                        for key, value in effect_data.items():
                            aup2_lines.append("{}={}".format(key,
                                self._convert_value_to_aup2_string(value)))

    @classmethod
    def from_file(cls, filepath: Union[str, Path], encoding: str = 'utf-8') -> 'AUP2Parser':
        """
        从文件创建AUP2解析器实例。

        Args:
            filepath (Union[str, Path]): AUP2文件路径
            encoding (str): 文件编码

        Returns:
            AUP2Parser: 初始化后的解析器实例

        Raises:
            FileNotFoundError: 如果文件不存在
            AUP2ParseError: 如果读取失败
        """
        filepath = Path(filepath)
        try:
            # Read as binary first to detect line endings for exact round-trip
            with open(filepath, 'rb') as f:
                raw_bytes = f.read()
            content = raw_bytes.decode(encoding)
        except UnicodeDecodeError as e:
            raise AUP2ParseError(f"文件编码错误: {e}") from e

        parser = cls(content)
        # Pass line ending info to parser for exact round-trip
        if b'\r\n' in raw_bytes:
            parser._line_ending = '\r\n'
        elif b'\r' in raw_bytes:
            parser._line_ending = '\r'
        return parser

    def save_to_file(self, filepath: Union[str, Path], encoding: str = 'utf-8') -> None:
        """
        将重建的AUP2内容保存到文件。

        Args:
            filepath (Union[str, Path]): 输出文件路径
            encoding (str): 文件编码

        Raises:
            AUP2ReconstructionError: 如果保存失败
        """
        try:
            reconstructed_content = self.reconstruct()
            filepath = Path(filepath)
            filepath.parent.mkdir(parents=True, exist_ok=True)

            with open(filepath, 'w', encoding=encoding, newline='') as f:
                f.write(reconstructed_content)
        except Exception as e:
            raise AUP2ReconstructionError(f"保存失败: {e}") from e

    def to_dict(self, include_records: bool = False) -> Dict[str, Any]:
        """将解析器完整状态导出为字典。

        Args:
            include_records: 是否包含 _line_records 以实现字节级往返。

        Returns:
            包含 data、换行信息、可选行记录的完整状态字典。
        """
        state: Dict[str, Any] = {
            "data": dict(self.data),
            "_line_ending": self._line_ending,
            "_trailing_newline": self._trailing_newline,
        }
        if include_records and self._line_records:
            state["_line_records"] = [
                {
                    "type": r.type,
                    "path": list(r.path),
                    "key": r.key,
                    "parsed": r.parsed,
                    "raw": r.raw,
                }
                for r in self._line_records
            ]
        return state
    def save_parsed_data(self, filepath: Union[str, Path], encoding: str = 'utf-8',
                         include_records: bool = False) -> None:
        """
        将解析后的数据保存为JSON文件。

        Args:
            filepath (Union[str, Path]): JSON输出文件路径
            encoding (str): 文件编码
            include_records: 是否包含 _line_records 以实现字节级往返
        """
        try:
            filepath = Path(filepath)
            filepath.parent.mkdir(parents=True, exist_ok=True)

            state = self.to_dict(include_records=include_records)
            with open(filepath, 'w', encoding=encoding) as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise AUP2ParseError(f"保存解析数据失败: {e}") from e

    def get_summary(self) -> Dict[str, Any]:
        """
        获取解析数据的摘要信息。

        Returns:
            Dict[str, Any]: 包含统计和摘要信息的字典
        """
        data = dict(self.data)
        metadata = data.get('_metadata', {})

        summary = {
            'total_sections': len([k for k in data if not k.startswith('_')]),
            'scenes': len([k for k in data if k.startswith('scene.')]),
            'objects': len([k for k in data if k.startswith('object.') and not k.startswith('object.effects')]),
            'warnings_count': len(metadata.get('warnings', [])),
            'has_project': 'project' in data,
            'parsing_line_count': metadata.get('line_count', 0)
        }

        # 统计图层分布
        layer_dist = {}
        for obj_key in [k for k in data if k.startswith('object.')]:
            layer = data[obj_key].get('layer')
            if layer is not None:
                layer_dist[layer] = layer_dist.get(layer, 0) + 1
        summary['layer_distribution'] = layer_dist

        return summary

    @classmethod
    def reconstruct_from_dict(cls, parsed_data: Dict[str, Any]) -> str:
        """
        从字典重建 AUP2 字符串 (类方法，增强版)。

        Args:
            parsed_data (Dict[str, Any]): 解析后的字典。

        Returns:
            str: 重建的 AUP2 字符串。

        Raises:
            AUP2ReconstructionError: 如果重建失败
        """
        if not isinstance(parsed_data, dict):
            raise AUP2ReconstructionError("输入数据必须是字典类型")

        temp_parser = cls.__new__(cls)
        temp_parser.aup2_content = None
        temp_parser._init_fields()
        temp_parser.data = defaultdict(dict, parsed_data)
        return temp_parser.reconstruct()

    @classmethod
    def reconstruct_from_json(cls, json_filepath: Union[str, Path],
                             encoding: str = 'utf-8') -> str:
        """
        从 JSON 文件读取并重建 AUP2 字符串（增强版）。

        Args:
            json_filepath (Union[str, Path]): JSON 文件路径。
            encoding (str): 文件编码。

        Returns:
            str: 重建的 AUP2 字符串。

        Raises:
            FileNotFoundError: 如果JSON文件不存在
            AUP2ParseError: 如果JSON解析失败
        """
        try:
            with open(json_filepath, 'r', encoding=encoding) as f:
                parsed_data = json.load(f)

            # 过滤元数据
            if '_metadata' in parsed_data:
                del parsed_data['_metadata']

            return cls.reconstruct_from_dict(parsed_data)
        except json.JSONDecodeError as e:
            raise AUP2ParseError(f"JSON解析失败: {e}") from e

    @classmethod
    def from_state(cls, state: Dict[str, Any]) -> 'AUP2Parser':
        """从完整状态字典恢复解析器实例（含 _line_records 以支持字节级往返）。

        Args:
            state: to_dict(include_records=True) 产出的完整状态字典。

        Returns:
            已恢复状态的 AUP2Parser 实例，可直接调用 reconstruct()。
        """
        parser = cls.__new__(cls)
        parser.aup2_content = None
        parser._init_fields()

        data = state.get("data", {})
        parser.data = defaultdict(dict)
        parser.data.update(data)

        records_data = state.get("_line_records", [])
        parser._line_records = [
            LineRecord(
                type=r["type"],
                path=tuple(r["path"]),
                key=r.get("key"),
                parsed=r.get("parsed"),
                raw=r["raw"],
            )
            for r in records_data
        ]

        parser._line_ending = state.get("_line_ending", "\n")
        parser._trailing_newline = state.get("_trailing_newline", True)
        return parser

    @classmethod
    def load_state(cls, filepath: Union[str, Path], encoding: str = 'utf-8') -> 'AUP2Parser':
        """从 JSON 文件加载完整解析器状态。

        Args:
            filepath: 由 save_parsed_data(include_records=True) 或
                      save_state() 写入的 JSON 文件路径。
            encoding: 文件编码。

        Returns:
            已恢复状态的 AUP2Parser 实例。
        """
        with open(filepath, 'r', encoding=encoding) as f:
            state = json.load(f)
        return cls.from_state(state)

    @classmethod
    def save_reconstructed_aup2(cls, json_filepath: Union[str, Path],
                               output_filepath: Union[str, Path],
                               encoding: str = 'utf-8') -> None:
        """
        从 JSON 文件重建 AUP2 并保存（增强版）。

        Args:
            json_filepath (Union[str, Path]): JSON 输入文件路径。
            output_filepath (Union[str, Path]): AUP2 输出文件路径。
            encoding (str): 文件编码。

        Raises:
            AUP2ParseError: 如果重建过程中出现错误
        """
        try:
            reconstructed_aup2_content = cls.reconstruct_from_json(json_filepath, encoding)

            output_path = Path(output_filepath)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_filepath, 'w', encoding=encoding) as f:
                f.write(reconstructed_aup2_content)

            print(f"成功重建 AUP2 到 '{output_filepath}' (编码: {encoding})")
        except Exception as e:
            raise AUP2ParseError(f"重建保存失败: {e}") from e

    def get_objects_by_scene(self, scene_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取指定场景的所有对象信息。

        Args:
            scene_id (Optional[int]): 场景ID，None表示所有场景

        Returns:
            List[Dict[str, Any]]: 对象信息列表
        """
        objects = []
        data = dict(self.data)

        for obj_key in [k for k in data if k.startswith('object.')]:
            obj = data[obj_key]
            obj_scene = obj.get('scene', 0)  # 如果未指定scene，默认为0

            if scene_id is None or obj_scene == scene_id:
                objects.append({
                    'id': obj_key,
                    'scene': obj_scene,
                    'layer': obj.get('layer'),
                    'frame': obj.get('frame'),
                    'has_effects': 'effects' in obj
                })

        return objects


# 兼容性函数和便利函数
def parse_aviutl_aup2_to_dict(aup2_content: str) -> Dict[str, Any]:
    """
    解析 AviUtl AUP2 文件的内容为 Python 字典（保留原函数接口）。
    """
    parser = AUP2Parser(aup2_content)
    return parser.parse()


def parse_aup2_file(filepath: Union[str, Path], encoding: str = 'utf-8') -> Dict[str, Any]:
    """
    从文件解析AUP2并返回字典。

    Args:
        filepath (Union[str, Path]): AUP2文件路径
        encoding (str): 文件编码

    Returns:
        Dict[str, Any]: 解析后的字典数据
    """
    parser = AUP2Parser.from_file(filepath, encoding)
    return parser.parse()


def reconstruct_aup2_dict(parsed_data: Dict[str, Any]) -> str:
    """
    从字典重建AUP2字符串的便利函数。

    Args:
        parsed_data (Dict[str, Any]): 解析后的字典数据

    Returns:
        str: 重建的AUP2字符串
    """
    return AUP2Parser.reconstruct_from_dict(parsed_data)


def convert_aup2_file(input_file: Union[str, Path],
                     output_file: Union[str, Path],
                     encoding: str = 'utf-8') -> None:
    """
    读取AUP2文件并重新保存（用于验证或格式化）。

    Args:
        input_file (Union[str, Path]): 输入AUP2文件路径
        output_file (Union[str, Path]): 输出AUP2文件路径
        encoding (str): 文件编码
    """
    parser = AUP2Parser.from_file(input_file, encoding)
    parser.save_to_file(output_file, encoding)


def validate_aup2_file(filepath: Union[str, Path], encoding: str = 'utf-8') -> Tuple[bool, List[str]]:
    """
    验证AUP2文件并返回验证结果。

    Args:
        filepath (Union[str, Path]): AUP2文件路径
        encoding (str): 文件编码

    Returns:
        Tuple[bool, List[str]]: (是否有效, 错误/警告列表)
    """
    try:
        parser = AUP2Parser.from_file(filepath, encoding)
        parsed_data = parser.parse()

        # 执行全面验证
        clean_data = dict(parsed_data)
        if '_metadata' in clean_data:
            del clean_data['_metadata']

        errors = parser.validate_data_structure(clean_data)
        warnings = parsed_data.get('_metadata', {}).get('warnings', [])

        is_valid = len(errors) == 0
        messages = errors + warnings

        return is_valid, messages

    except Exception as e:
        return False, [f"解析失败: {e}"]


def save_aup2_state(filepath: Union[str, Path],
                    output_filepath: Union[str, Path],
                    encoding: str = 'utf-8') -> None:
    """解析AUP2文件并将完整状态（含行记录）保存为JSON。

    Args:
        filepath: AUP2文件路径
        output_filepath: JSON输出文件路径
        encoding: 文件编码
    """
    parser = AUP2Parser.from_file(filepath, encoding)
    parser.parse()
    parser.save_parsed_data(output_filepath, encoding, include_records=True)


def load_aup2_state(filepath: Union[str, Path], encoding: str = 'utf-8') -> AUP2Parser:
    """从完整状态JSON文件加载AUP2Parser实例（支持字节级往返重建）。

    Args:
        filepath: JSON文件路径
        encoding: 文件编码

    Returns:
        已恢复状态的AUP2Parser实例
    """
    return AUP2Parser.load_state(filepath, encoding)

# 示例用法
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        input_file = sys.argv[1]

        try:
            # 解析文件
            parser = AUP2Parser.from_file(input_file)
            data = parser.parse()

            # 显示摘要
            summary = parser.get_summary()
            print("解析摘要:")
            print(f"- 总区块数: {summary['total_sections']}")
            print(f"- 场景数: {summary['scenes']}")
            print(f"- 对象数: {summary['objects']}")
            print(f"- 图层分布: {summary['layer_distribution']}")

            # 显示警告
            warnings = data.get('_metadata', {}).get('warnings', [])
            if warnings:
                print(f"\n解析警告 ({len(warnings)} 个):")
                for warning in warnings:
                    print(f"  - {warning}")

        except Exception as e:
            print(f"错误: {e}")
            sys.exit(1)
    else:
        print("用法: python aup2_parser.py <aup2_file_path>")
