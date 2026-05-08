#!/usr/bin/env python3
"""将 .drawio XML 文件编码为 diagrams.net 查看器 URL。

用作 draw.io 桌面 CLI 不可用时的浏览器后备。
生成客户端侧 URL — 图表 XML 被编码在 URL 片段（# 之后），
所以没有任何内容上传到任何服务器。

用法: python3 encode_drawio_url.py <path/to/input.drawio>
"""
import base64
import sys
import urllib.parse
import zlib


def encode(xml: str) -> str:
    """将 XML 内容编码为 diagrams.net 查看器 URL。

    Args:
        xml: .drawio 文件的 XML 内容（字符串）

    Returns:
        完整的 viewer.diagrams.net URL，可直接在浏览器中打开
    """
    # 原始 deflate（无 zlib 头）— diagrams.net 使用 mxGraph 的原始 inflate
    # zlib.MAX_WBITS 负值表示原始 deflate 格式（不带头/校验）
    c = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS)
    compressed = c.compress(xml.encode("utf-8")) + c.flush()

    # 标准 base64（atob 拒绝 url-safe 的 -/_）；去掉换行符
    encoded = base64.b64encode(compressed).decode("utf-8").replace("\n", "")

    # 拼接 URL:
    # - /?tags=%7B%7D&lightbox=1&edit=_blank = 查看器参数
    # - #R = mxGraph 客户端渲染模式
    # - quote(encoded) = URL 安全编码的压缩数据
    return (
        "https://viewer.diagrams.net/?tags=%7B%7D&lightbox=1&edit=_blank#R"
        + urllib.parse.quote(encoded, safe="")
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: encode_drawio_url.py <path>", file=sys.stderr)
        sys.exit(2)
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        print(encode(f.read()))
