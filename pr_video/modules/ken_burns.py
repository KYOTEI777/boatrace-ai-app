"""
Ken Burns Effect Module: Runway API なしで動画を生成
静止画にパン・ズーム効果をつけてシネマティックな動画を作る（完全無料）
"""

import numpy as np
from pathlib import Path
from PIL import Image
from moviepy.editor import VideoClip, AudioFileClip
from moviepy.video.VideoClip import ImageClip


def _apply_ken_burns_frame(image_array, t, duration, zoom_start=1.0, zoom_end=1.15,
                            pan_start=(0.5, 0.5), pan_end=(0.5, 0.45)):
    """
    Ken Burns効果: 1フレームを生成
    ズームイン + 上方向へのパン（波→顔方向）
    """
    h, w = image_array.shape[:2]
    progress = t / duration  # 0.0 → 1.0

    zoom = zoom_start + (zoom_end - zoom_start) * progress
    cx = pan_start[0] + (pan_end[0] - pan_start[0]) * progress
    cy = pan_start[1] + (pan_end[1] - pan_start[1]) * progress

    # ズーム後のサイズ
    new_w = int(w / zoom)
    new_h = int(h / zoom)

    # クロップ範囲
    x1 = int((w - new_w) * cx)
    y1 = int((h - new_h) * cy)
    x2 = x1 + new_w
    y2 = y1 + new_h

    # クランプ
    x1 = max(0, min(x1, w - new_w))
    y1 = max(0, min(y1, h - new_h))
    x2 = x1 + new_w
    y2 = y1 + new_h

    cropped = image_array[y1:y2, x1:x2]
    # 元サイズに戻す
    img = Image.fromarray(cropped).resize((w, h), Image.LANCZOS)
    return np.array(img)


def image_to_ken_burns_video(
    image_path: str,
    output_path: str,
    duration: int = 30,
    fps: int = 30,
    target_size: tuple = (720, 1280),  # 縦型（幅, 高さ）
) -> str:
    """
    画像にKen Burns効果をつけて動画を生成（完全無料・APIなし）

    Ken Burns効果のバリエーション（自動でランダム選択）:
    - ズームイン + 上パン: 波→顔のドラマチックな演出
    - ズームイン + 中央固定: 顔のクローズアップ
    """
    print(f"🎬 Ken Burns効果で動画生成中（APIなし）: {image_path}")

    # 画像読み込み・リサイズ
    img = Image.open(image_path).convert("RGB")
    target_w, target_h = target_size

    # アスペクト比を保ちながらクロップ
    img_w, img_h = img.size
    img_ratio = img_w / img_h
    target_ratio = target_w / target_h

    if img_ratio > target_ratio:
        new_h = img_h
        new_w = int(img_h * target_ratio)
        left = (img_w - new_w) // 2
        img = img.crop((left, 0, left + new_w, new_h))
    else:
        new_w = img_w
        new_h = int(img_w / target_ratio)
        top = (img_h - new_h) // 2
        img = img.crop((0, top, new_w, top + new_h))

    img = img.resize((target_w * 2, target_h * 2), Image.LANCZOS)  # 2x大きめに（ズーム余白）
    img_array = np.array(img)

    def make_frame(t):
        return _apply_ken_burns_frame(
            img_array, t, duration,
            zoom_start=1.0, zoom_end=1.20,
            pan_start=(0.5, 0.55),  # 少し下から
            pan_end=(0.5, 0.45),    # 上へパン
        )

    clip = VideoClip(make_frame, duration=duration)
    clip = clip.resize((target_w, target_h))

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    clip.write_videofile(
        output_path,
        fps=fps,
        codec="libx264",
        logger="bar",
        audio=False,
    )
    clip.close()

    print(f"✅ Ken Burns動画完成: {output_path}")
    return output_path
