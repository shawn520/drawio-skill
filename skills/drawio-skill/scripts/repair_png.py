#!/usr/bin/env python3
"""修复 draw.io -e PNG 导出中截断的 IEND 块（issue #8）。

draw.io 的 CLI 在输出 -e PNG 时只写入了 4 字节的 IEND 长度字段，
但缺失了 8 字节的 "IEND" 类型 + CRC。严格的 PNG 解码器和 vision API
（包括 Anthropic）会以 400 "Could not process image" 拒绝该文件。
SVG/PDF 不受影响。

用法: python3 repair_png.py <path/to/diagram.drawio.png>

幂等性: endswith(IEND) guard 使其在 draw.io 在上游修复 bug 后成为空操作，
所以可以在每次 -e PNG 导出后无条件安全运行。
"""
import sys

# IEND 块的完整结构: 4字节长度(0) + "IEND" + CRC
# draw.io 的 -e PNG 缺少末尾 8 字节（IEND + CRC），只有长度字段
IEND = b"\x00\x00\x00\x00IEND\xaeB`\x82"


def repair(path: str) -> bool:
    """检查并修复 PNG 文件末尾的 IEND 截断问题。

    Args:
        path: PNG 文件路径

    Returns:
        True = 已修复（文件被修改）
        False = 无需修复（文件正常或已修复过）
    """
    with open(path, "rb") as f:
        data = f.read()

    # 如果已经以完整 IEND 结尾，无需修复
    if data.endswith(IEND):
        return False

    # draw.io 截断时，文件以 4 字节 0 结尾（长度字段）
    # 去掉这 4 字节，然后补上完整的 IEND
    if data.endswith(b"\x00\x00\x00\x00"):
        data = data[:-4]

    with open(path, "wb") as f:
        f.write(data + IEND)
    return True


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: repair_png.py <path>", file=sys.stderr)
        sys.exit(2)
    if repair(sys.argv[1]):
        print(f"repaired {sys.argv[1]}")
