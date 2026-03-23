"""
MIZUMONO PR動画 自動生成スクリプト
水ノ上玄舟伝キャラクターを使ったボートレースAI予測システムのPR動画を生成する

【モード】
  --free-mode  : APIキー不要。Edge-TTS + Ken Burns効果 + moviepy のみ（完全無料）
  通常モード   : Runway Gen-4 + Replicate リップシンク（本格品質）

使い方:
    # APIキーなしで今すぐ試す
    python generate_pr_video.py --image assets/mizumono.jpg --free-mode

    # 本格版（APIキーあり）
    python generate_pr_video.py --image assets/mizumono.jpg

必要な環境変数 (.env) ※通常モードのみ:
    RUNWAY_API_KEY=your_runway_api_key
    REPLICATE_API_TOKEN=your_replicate_token
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# .env ファイルを読み込む
load_dotenv(Path(__file__).parent / ".env")

# モジュールのパスを追加
sys.path.insert(0, str(Path(__file__).parent))

from modules.tts import generate_pr_voice
from modules.video_editor import assemble_pr_video


OUTPUT_DIR = Path(__file__).parent / "output"
ASSETS_DIR = Path(__file__).parent / "assets"


def run_free_pipeline(
    image_path: str,
    output_name: str = "mizumono_pr",
    bgm_path: str = None,
) -> str:
    """
    完全無料パイプライン（APIキー不要）

    1. Edge-TTS  → 日本語ナレーション音声
    2. Ken Burns → 静止画にズーム/パン効果（moviepy）
    3. moviepy   → タイトル・字幕・BGM・エンディング組み立て
    """
    from modules.ken_burns import image_to_ken_burns_video

    OUTPUT_DIR.mkdir(exist_ok=True)

    print("=" * 60)
    print("🎬 MIZUMONO PR動画 生成開始（無料モード）")
    print("=" * 60)

    # ── ステップ 1: 音声生成 ──────────────────────────────────
    print("\n[1/3] 🎙️  ナレーション音声を生成中（Edge-TTS）...")
    generate_pr_voice(str(OUTPUT_DIR))
    voice_path = str(OUTPUT_DIR / "mizumono_voice.mp3")
    print(f"   → {voice_path}")

    # ── ステップ 2: Ken Burns動画生成 ─────────────────────────
    print("\n[2/3] 🌊 Ken Burns効果で動画生成中（APIなし）...")
    motion_video_path = str(OUTPUT_DIR / f"{output_name}_motion.mp4")

    # 音声の長さに合わせて動画の長さを決める
    from moviepy.editor import AudioFileClip
    audio = AudioFileClip(voice_path)
    video_duration = int(audio.duration) + 6  # 音声 + タイトル/エンディング分
    audio.close()

    image_to_ken_burns_video(
        image_path=image_path,
        output_path=motion_video_path,
        duration=video_duration,
        fps=30,
        target_size=(720, 1280),
    )
    print(f"   → {motion_video_path}")

    # ── ステップ 3: 最終編集 ──────────────────────────────────
    print("\n[3/3] 🎞️  最終PR動画を組み立て中（moviepy）...")
    final_output_path = str(OUTPUT_DIR / f"{output_name}_final.mp4")
    assemble_pr_video(
        lipsync_video_path=motion_video_path,
        audio_path=voice_path,
        output_path=final_output_path,
        bgm_path=bgm_path,
        include_title_card=True,
        include_ending_card=True,
    )

    print("\n" + "=" * 60)
    print(f"✅ PR動画完成！（無料モード）")
    print(f"   📁 {final_output_path}")
    print("=" * 60)

    return final_output_path


def run_pipeline(
    image_path: str,
    output_name: str = "mizumono_pr",
    skip_image_to_video: bool = False,
    existing_video: str = None,
    bgm_path: str = None,
) -> str:
    """
    本格パイプライン（Runway + Replicate 使用）

    1. Edge-TTS     → 日本語ナレーション音声
    2. Runway Gen-4 → 画像から動画（着物なびく・波が揺れる）
    3. Replicate    → リップシンク（口を音声に同期）
    4. moviepy      → タイトル・字幕・BGM・エンディング
    """
    from modules.image_to_video import generate_motion_video, CHARACTER_PROMPT
    from modules.lipsync import apply_lipsync

    OUTPUT_DIR.mkdir(exist_ok=True)

    print("=" * 60)
    print("🎬 MIZUMONO PR動画 生成開始（本格モード）")
    print("=" * 60)

    # ── ステップ 1: 音声生成 ──────────────────────────────────
    print("\n[1/4] 🎙️  ナレーション音声を生成中（Edge-TTS）...")
    generate_pr_voice(str(OUTPUT_DIR))
    voice_path = str(OUTPUT_DIR / "mizumono_voice.mp3")
    print(f"   → {voice_path}")

    # ── ステップ 2: 画像 → 動画 ───────────────────────────────
    if skip_image_to_video and existing_video:
        motion_video_path = existing_video
        print(f"\n[2/4] ⏭️  Runway スキップ（既存動画使用: {existing_video}）")
    else:
        print("\n[2/4] 🌊 キャラクター画像から動画を生成中（Runway Gen-4）...")
        motion_video_path = str(OUTPUT_DIR / f"{output_name}_motion.mp4")
        generate_motion_video(
            image_path=image_path,
            output_path=motion_video_path,
            prompt=CHARACTER_PROMPT,
            duration=10,
            ratio="720:1280",
        )
        print(f"   → {motion_video_path}")

    # ── ステップ 3: リップシンク ──────────────────────────────
    print("\n[3/4] 💋 リップシンク処理中（Replicate）...")
    lipsync_video_path = str(OUTPUT_DIR / f"{output_name}_lipsync.mp4")
    apply_lipsync(
        video_path=motion_video_path,
        audio_path=voice_path,
        output_path=lipsync_video_path,
    )
    print(f"   → {lipsync_video_path}")

    # ── ステップ 4: 最終編集 ──────────────────────────────────
    print("\n[4/4] 🎞️  最終PR動画を組み立て中（moviepy）...")
    final_output_path = str(OUTPUT_DIR / f"{output_name}_final.mp4")
    assemble_pr_video(
        lipsync_video_path=lipsync_video_path,
        audio_path=voice_path,
        output_path=final_output_path,
        bgm_path=bgm_path,
        include_title_card=True,
        include_ending_card=True,
    )

    print("\n" + "=" * 60)
    print(f"✅ PR動画完成！")
    print(f"   📁 {final_output_path}")
    print("=" * 60)

    return final_output_path


def main():
    parser = argparse.ArgumentParser(
        description="MIZUMONO PR動画 自動生成ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
【モード選択】
  --free-mode  APIキー不要（Edge-TTS + Ken Burns + moviepy のみ）
  通常モード   APIキーあり（Runway Gen-4 + Replicate リップシンク）

例:
  # 今すぐ試す（APIキー不要）
  python generate_pr_video.py --image assets/mizumono.jpg --free-mode

  # 本格版（APIキーあり）
  python generate_pr_video.py --image assets/mizumono.jpg

  # BGMを追加
  python generate_pr_video.py --image assets/mizumono.jpg --free-mode --bgm assets/bgm.mp3

  # Runway をスキップしてリップシンクのみ
  python generate_pr_video.py --image assets/mizumono.jpg \\
      --skip-image-to-video --existing-video output/my_video.mp4

必要な環境変数 (.env ファイル) ※通常モードのみ:
  RUNWAY_API_KEY=...
  REPLICATE_API_TOKEN=...
        """,
    )
    parser.add_argument(
        "--image",
        type=str,
        default=str(ASSETS_DIR / "mizumono.jpg"),
        help="MIZUMONOキャラクター画像のパス（デフォルト: assets/mizumono.jpg）",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="mizumono_pr",
        help="出力ファイル名（拡張子なし）",
    )
    parser.add_argument(
        "--bgm",
        type=str,
        default=None,
        help="BGM音声ファイルのパス（MP3/WAV）",
    )
    parser.add_argument(
        "--free-mode",
        action="store_true",
        help="APIキー不要モード（Ken Burns効果 + Edge-TTS のみ）",
    )
    parser.add_argument(
        "--skip-image-to-video",
        action="store_true",
        help="Runway API をスキップして既存動画を使用",
    )
    parser.add_argument(
        "--existing-video",
        type=str,
        default=None,
        help="スキップ時に使用する既存動画のパス",
    )

    args = parser.parse_args()

    # 画像ファイルの確認
    if not Path(args.image).exists():
        print(f"❌ 画像ファイルが見つかりません: {args.image}")
        print(f"   assets/mizumono.jpg にMIZUMONOキャラクター画像を配置してください。")
        sys.exit(1)

    # 無料モード
    if args.free_mode:
        run_free_pipeline(
            image_path=args.image,
            output_name=args.output,
            bgm_path=args.bgm,
        )
        return

    # 本格モード: API キーの確認
    missing_keys = []
    if not os.environ.get("RUNWAY_API_KEY") and not args.skip_image_to_video:
        missing_keys.append("RUNWAY_API_KEY")
    if not os.environ.get("REPLICATE_API_TOKEN"):
        missing_keys.append("REPLICATE_API_TOKEN")

    if missing_keys:
        print(f"❌ 以下の環境変数が設定されていません:")
        for key in missing_keys:
            print(f"   {key}")
        print(f"\n   APIキーなしで試すには --free-mode を使ってください:")
        print(f"   python generate_pr_video.py --image assets/mizumono.jpg --free-mode")
        sys.exit(1)

    run_pipeline(
        image_path=args.image,
        output_name=args.output,
        skip_image_to_video=args.skip_image_to_video,
        existing_video=args.existing_video,
        bgm_path=args.bgm,
    )


if __name__ == "__main__":
    main()
