"""
Video Editor Module: moviepy による最終PR動画の組み立て
タイトル、字幕、BGM、エンディングを追加して本格PR動画に仕上げる
"""

import os
from pathlib import Path
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips,
    ColorClip,
    CompositeAudioClip,
)
from moviepy.config import change_settings


# フォント設定（日本語対応）
JAPANESE_FONT = "Noto-Sans-CJK-JP-Bold"
FALLBACK_FONT = "DejaVu-Sans-Bold"


# 字幕テキストと表示タイミング（秒）
SUBTITLES = [
    (0.0,  3.0,  "水面を制する者が、勝利を制す。"),
    (3.5,  6.0,  "俺の名は…水ノ上玄舟。"),
    (7.0,  12.0, "勝者と敗者を分けるのは、運ではない。\nデータだ。"),
    (13.0, 20.0, "展示タイム、モーター勝率、風と波。\nすべてを読み解いた者だけが\n水面の真実を知る。"),
    (21.0, 25.0, "そのために、AIが生まれた。"),
    (26.0, 33.0, "ボートレースAI予測システム。"),
    (34.0, 42.0, "機械学習が、レースを分析する。"),
    (43.0, 50.0, "データは、嘘をつかない。"),
]

# エンディングテキスト
ENDING_TITLE = "ボートレースAI予測システム"
ENDING_SUBTITLE = "水ノ上玄舟伝"
ENDING_DURATION = 4.0


def _get_font() -> str:
    """利用可能な日本語フォントを返す"""
    import subprocess
    result = subprocess.run(
        ["fc-list", ":lang=ja", "--format=%{file}\n"],
        capture_output=True, text=True
    )
    if result.returncode == 0 and result.stdout.strip():
        fonts = result.stdout.strip().split("\n")
        for font in fonts:
            if "Bold" in font or "bold" in font:
                return font
        return fonts[0]
    return FALLBACK_FONT


def add_subtitles(
    video_clip: VideoFileClip,
    subtitles: list = None,
    font_size: int = 36,
) -> CompositeVideoClip:
    """字幕を動画に追加"""
    if subtitles is None:
        subtitles = SUBTITLES

    font = _get_font()
    subtitle_clips = []

    for start, end, text in subtitles:
        if start >= video_clip.duration:
            continue
        end = min(end, video_clip.duration)

        txt_clip = (
            TextClip(
                text,
                fontsize=font_size,
                font=font,
                color="white",
                stroke_color="black",
                stroke_width=2,
                method="caption",
                size=(int(video_clip.w * 0.85), None),
                align="center",
            )
            .set_start(start)
            .set_end(end)
            .set_position(("center", 0.80), relative=True)
        )
        subtitle_clips.append(txt_clip)

    return CompositeVideoClip([video_clip] + subtitle_clips)


def create_title_card(
    width: int,
    height: int,
    title: str = "MIZUMONO",
    subtitle: str = "水ノ上玄舟伝",
    duration: float = 3.0,
) -> CompositeVideoClip:
    """タイトルカードを生成（イントロ用）"""
    font = _get_font()

    bg = ColorClip(size=(width, height), color=(5, 15, 30), duration=duration)

    title_clip = (
        TextClip(title, fontsize=80, font=font, color="#5BB8D4", method="label")
        .set_position(("center", 0.30), relative=True)
        .set_duration(duration)
    )

    sub_clip = (
        TextClip(f"— {subtitle} —", fontsize=40, font=font, color="white", method="label")
        .set_position(("center", 0.50), relative=True)
        .set_duration(duration)
    )

    return CompositeVideoClip([bg, title_clip, sub_clip])


def create_ending_card(
    width: int,
    height: int,
    title: str = ENDING_TITLE,
    subtitle: str = ENDING_SUBTITLE,
    duration: float = ENDING_DURATION,
) -> CompositeVideoClip:
    """エンディングカードを生成"""
    font = _get_font()

    bg = ColorClip(size=(width, height), color=(5, 15, 30), duration=duration)

    main_text = (
        TextClip(title, fontsize=50, font=font, color="#5BB8D4", method="label")
        .set_position(("center", 0.35), relative=True)
        .set_duration(duration)
    )

    sub_text = (
        TextClip(subtitle, fontsize=32, font=font, color="white", method="label")
        .set_position(("center", 0.55), relative=True)
        .set_duration(duration)
    )

    url_text = (
        TextClip("AI Prediction Powered by Machine Learning", fontsize=22, font=font,
                 color="#888888", method="label")
        .set_position(("center", 0.75), relative=True)
        .set_duration(duration)
    )

    return CompositeVideoClip([bg, main_text, sub_text, url_text])


def assemble_pr_video(
    lipsync_video_path: str,
    audio_path: str,
    output_path: str,
    bgm_path: str = None,
    bgm_volume: float = 0.12,
    include_title_card: bool = True,
    include_ending_card: bool = True,
) -> str:
    """
    最終PR動画を組み立てる

    Args:
        lipsync_video_path: リップシンク済み動画
        audio_path: ナレーション音声
        output_path: 最終出力パス
        bgm_path: BGM音声（任意）
        bgm_volume: BGMの音量（0.0〜1.0）
        include_title_card: タイトルカードを先頭に追加するか
        include_ending_card: エンディングカードを末尾に追加するか

    Returns:
        最終動画のパス
    """
    print("🎞️  PR動画を組み立て中...")

    # メイン動画を読み込み
    main_video = VideoFileClip(lipsync_video_path)
    w, h = main_video.size

    # 字幕を追加
    main_with_subs = add_subtitles(main_video)

    # クリップリストを構築
    clips = []

    if include_title_card:
        title = create_title_card(w, h, duration=3.0)
        clips.append(title)

    clips.append(main_with_subs)

    if include_ending_card:
        ending = create_ending_card(w, h, duration=4.0)
        clips.append(ending)

    # 結合
    final_video = concatenate_videoclips(clips, method="compose")

    # 音声の設定
    narration = AudioFileClip(audio_path)
    narration_start = 3.0 if include_title_card else 0.0

    audio_clips = [narration.set_start(narration_start)]

    if bgm_path and os.path.exists(bgm_path):
        bgm = (
            AudioFileClip(bgm_path)
            .volumex(bgm_volume)
            .set_duration(final_video.duration)
            .audio_fadeout(3.0)
        )
        audio_clips.append(bgm)

    final_audio = CompositeAudioClip(audio_clips)
    final_video = final_video.set_audio(final_audio)

    # エクスポート
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    print(f"   動画エクスポート中... ({output_path})")
    final_video.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile="temp_audio.m4a",
        remove_temp=True,
        logger="bar",
    )

    # クリーンアップ
    main_video.close()
    narration.close()

    print(f"✅ PR動画完成: {output_path}")
    return output_path
