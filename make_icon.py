"""生成应用图标 assets/app.ico（粉色主题 + 手柄剪影）。"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 512
OUT_DIR = Path(__file__).resolve().parent / "assets"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TOP = (255, 123, 168)
BOTTOM = (232, 68, 111)
WHITE = (255, 255, 255, 255)
PINK = (255, 92, 138, 255)


def gradient(size: int) -> Image.Image:
    img = Image.new("RGB", (1, size))
    px = img.load()
    for y in range(size):
        k = y / max(1, size - 1)
        px[0, y] = tuple(int(TOP[i] + (BOTTOM[i] - TOP[i]) * k) for i in range(3))
    return img.resize((size, size), Image.BILINEAR)


def build() -> Image.Image:
    base = gradient(SIZE).convert("RGBA")

    # 圆角方形遮罩
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle((10, 10, SIZE - 10, SIZE - 10), radius=104, fill=255)
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    canvas.paste(base, (0, 0), mask)

    layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    # 手柄本体
    d.rounded_rectangle((98, 206, 414, 338), radius=58, fill=WHITE)
    # 两侧握把
    d.ellipse((76, 248, 198, 398), fill=WHITE)
    d.ellipse((314, 248, 436, 398), fill=WHITE)

    # 十字键
    d.rounded_rectangle((152, 252, 250, 292), radius=10, fill=PINK)
    d.rounded_rectangle((181, 223, 221, 321), radius=10, fill=PINK)

    # AB 按钮
    d.ellipse((304, 234, 342, 272), fill=PINK)
    d.ellipse((350, 272, 388, 310), fill=PINK)

    # 两侧的震动波纹
    for i, (cx, r) in enumerate(((58, 26), (24, 40))):
        w = 11
        d.arc((cx - r, 256 - r, cx + r, 256 + r), start=-52, end=52, fill=WHITE, width=w)
        cxr = SIZE - cx
        d.arc((cxr - r, 256 - r, cxr + r, 256 + r), start=128, end=232, fill=WHITE, width=w)

    canvas = Image.alpha_composite(canvas, layer)
    return canvas


def main() -> None:
    icon = build()
    png_path = OUT_DIR / "app.png"
    ico_path = OUT_DIR / "app.ico"
    icon.save(png_path)
    icon.save(
        ico_path,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"[ok] {png_path}")
    print(f"[ok] {ico_path}")


if __name__ == "__main__":
    main()
