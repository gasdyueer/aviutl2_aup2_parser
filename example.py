#!/usr/bin/env python3
"""
AUP2 Parser 使用示例
"""

from pathlib import Path
import json
from .aup2_parser import AUP2Parser

def main():
    """主函数：展示各种使用场景"""

    # 示例AUP2内容
    sample_aup2 = """[project]
width=1920
height=1080
framerate=30

[scene.0]
name=Main Scene
start=0
end=900

[0]
layer=1
frame=0:900

[0.0]
_type=1
name=Sample Effect
param1=100
"""

    print("=== AUP2 Parser 使用示例 ===\n")

    # 1. 解析AUP2字符串
    print("1. 解析AUP2字符串:")
    parser = AUP2Parser(sample_aup2)
    data = parser.parse()
    print(f"解析成功！包含 {len(data)} 个区块")
    print(f"对象数量: {len([k for k in data if k.startswith('object.')])}")
    print()

    # 2. 使用便利函数
    print("2. 使用便利函数:")
    from . import parse, parse_file
    data2 = parse(sample_aup2)
    print("简易接口 parse() 成功！")
    print()

    # 3. 读取文件（如果有实际文件）
    print("3. 读取AUP2文件:")
    # 假设有一个test.aup2文件
    test_file = Path("tests/fixtures/test.aup2")
    if test_file.exists():
        file_data = parse_file(str(test_file))
        print("从文件 parse() 成功！")
    else:
        print("没有找到测试文件，跳过文件读取示例")
    print()

    # 4. 重建AUP2
    print("4. 重建AUP2字符串:")
    reconstructed = parser.reconstruct()
    print("重建成功！前几行:")
    print("\n".join(reconstructed.split("\n")[:5]))
    print("...")
    print()

    # 5. 保存数据
    print("5. 保存解析结果为JSON:")
    with open("parsed_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("已保存到 parsed_data.json")

if __name__ == "__main__":
    main()