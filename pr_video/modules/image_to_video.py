"""
Image-to-Video Module: Runway Gen-4 Turbo API
MIZUMONOキャラクター画像に動きをつける（着物なびく、波が揺れる）
"""

import os
import time
import base64
import requests
from pathlib import Path


RUNWAY_API_URL = "https://api.dev.runwayml.com/v1"
RUNWAY_API_VERSION = "2024-11-06"


# MIZUMONOキャラクター用プロンプト
CHARACTER_PROMPT = (
    "The old man's kimono billows gently in the night breeze. "
    "His silver hair and beard move slightly. "
    "The water behind him shimmers with reflected stadium lights. "
    "Racing boats glide across the dark water. "
    "Dramatic, cinematic atmosphere. Slow, powerful motion."
)


def _get_headers() -> dict:
    api_key = os.environ.get("RUNWAY_API_KEY")
    if not api_key:
        raise ValueError("RUNWAY_API_KEY が設定されていません。.env ファイルを確認してください。")
    return {
        "Authorization": f"Bearer {api_key}",
        "X-Runway-Version": RUNWAY_API_VERSION,
        "Content-Type": "application/json",
    }


def _image_to_data_uri(image_path: str) -> str:
    """画像をbase64 data URIに変換"""
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    ext = Path(image_path).suffix.lower().lstrip(".")
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
    return f"data:{mime};base64,{data}"


def generate_motion_video(
    image_path: str,
    output_path: str,
    prompt: str = CHARACTER_PROMPT,
    duration: int = 10,
    ratio: str = "720:1280",  # 縦型（スマホ向け）
) -> str:
    """
    Runway Gen-4 Turbo で画像から動画を生成

    Args:
        image_path: 入力画像パス（MIZUMONOキャラクター画像）
        output_path: 出力動画パス
        prompt: 動きの説明プロンプト
        duration: 動画の長さ（秒）5 or 10
        ratio: アスペクト比

    Returns:
        生成された動画のパス
    """
    headers = _get_headers()
    image_uri = _image_to_data_uri(image_path)

    # タスク作成
    payload = {
        "model": "gen4_turbo",
        "promptImage": image_uri,
        "promptText": prompt,
        "ratio": ratio,
        "duration": duration,
    }

    print(f"🎬 Runway Gen-4 Turbo: 動画生成開始...")
    response = requests.post(
        f"{RUNWAY_API_URL}/image_to_video",
        headers=headers,
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    task_id = response.json()["id"]
    print(f"   タスクID: {task_id}")

    # ポーリングで完了待ち
    return _poll_task(task_id, output_path, headers)


def _poll_task(task_id: str, output_path: str, headers: dict, timeout: int = 600) -> str:
    """タスク完了までポーリング"""
    start = time.time()
    interval = 10

    while time.time() - start < timeout:
        resp = requests.get(
            f"{RUNWAY_API_URL}/tasks/{task_id}",
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")

        if status == "SUCCEEDED":
            video_url = data["output"][0]
            print(f"✅ 動画生成完了！ダウンロード中...")
            _download_video(video_url, output_path)
            return output_path

        elif status == "FAILED":
            error = data.get("failure", "不明なエラー")
            raise RuntimeError(f"Runway タスク失敗: {error}")

        print(f"   ステータス: {status} ... {int(time.time() - start)}秒経過")
        time.sleep(interval)

    raise TimeoutError(f"Runway タスクがタイムアウトしました ({timeout}秒)")


def _download_video(url: str, output_path: str) -> None:
    """動画をダウンロード"""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    print(f"✅ 動画保存: {output_path}")
