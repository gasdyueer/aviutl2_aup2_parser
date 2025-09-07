#!/usr/bin/env python3
"""
测试AUP2Parser类的脚本
使用test.aup2作为测试文件
"""
import pathlib
from pathlib import Path
from aup2_parser import AUP2Parser


def main():
    # 指定测试AUP2文件的路径（相对于当前脚本位置）
    test_aup2_path = Path(__file__).parent / "test.aup2"
    test_aup2_path = test_aup2_path.resolve()  # 转换为绝对路径

    print(f"测试AUP2文件路径: {test_aup2_path}")
    if not test_aup2_path.exists():
        print(f"错误: 测试文件不存在: {test_aup2_path}")
        return

    try:
        print("\n开始解析AUP2文件...")
        # 从文件创建解析器
        parser = AUP2Parser.from_file(test_aup2_path)

        # 执行解析
        parsed_data = parser.parse()

        print("解析成功!")

        # 获取并显示摘要信息
        summary = parser.get_summary()
        print("\n解析摘要:")
        print(f"  - 总区块数: {summary['total_sections']}")
        print(f"  - 场景数: {summary['scenes']}")
        print(f"  - 对象数: {summary['objects']}")
        print(f"  - 项目区块: {'存在' if summary['has_project'] else '不存在'}")
        print(f"  - 解析行数: {summary['parsing_line_count']}")
        print(f"  - 图层分布: {summary['layer_distribution']}")

        # 显示警告信息
        metadata = parsed_data.get('_metadata', {})
        warnings = metadata.get('warnings', [])
        if warnings:
            print(f"\n解析警告 ({len(warnings)} 个):")
            for warning in warnings[:10]:  # 只显示前10个警告
                print(f"  - {warning}")
            if len(warnings) > 10:
                print(f"  ... 还有 {len(warnings) - 10} 个警告")
        else:
            print("\n无解析警告")

        # 显示对象阶段分配
        objects = parser.get_objects_by_scene(0)  # 场景0的所有对象
        if objects:
            print(f"\n场景0的对象列表 ({len(objects)} 个对象):")
            for obj in objects[:5]:  # 只显示前5个对象
                print(f"  - {obj['id']}: 图层 {obj['layer']}, 帧 {obj['frame']}, 场景 {obj['scene']}")
            if len(objects) > 5:
                print(f"  ... 还有 {len(objects) - 5} 个对象")

        # 可选: 保存解析数据为JSON（取消注释以下行）
        # json_output_path = test_aup2_path.with_suffix('.json')
        # parser.save_parsed_data(json_output_path)
        # print(f"\n解析数据已保存到: {json_output_path}")

        # 可选: 重建AUP2文件并保存（取消注释以下行）
        # reconstructed_path = test_aup2_path.with_suffix('.reconstructed.aup2')
        # parser.save_to_file(reconstructed_path)
        # print(f"\n重建的AUP2文件已保存到: {reconstructed_path}")

    except Exception as e:
        print(f"\n解析失败: {e}")
        print("可能的原因:")
        print("- 文件编码不正确（应该为UTF-8）")
        print("- 文件格式不符合AUP2规范")
        print("- 文件损坏或不完整")


if __name__ == "__main__":
    main()