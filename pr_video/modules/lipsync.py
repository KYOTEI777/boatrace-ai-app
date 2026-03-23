"""
Lipsync Module: Replicate API (sync-labs/wav2lip)
MIZUMONOキャラクターの口を音声に合わせて動かす
"""

import os
import time
import requests
import replicate
from pathlib import Path


# Replicate上のlipsyncモデル（マンガ/イラスト対応）
LIPSYNC_MODEL = "sync-labs/wav2lip:8d65e3f4f4298520e079198b493c25adfc43c058"

# イラストスタイル向け: より自然な動きのモデル
LIPSYNC_MODEL_ALT = "lucataco/wav2lip:7f56175a4b5e1defc9d3e043a6a804eb424f86da"


def apply_lipsync(
    video_path: str,
    audio_path: str,
    output_path: str,
    model: str = LIPSYNC_MODEL,
) -> str:
    """
    動画キャラクターに音声のリップシンクを適用

    Args:
        video_path: 入力動画パス（Runwayで生成したMIZUMONO動画）
        audio_path: 音声パス（Edge-TTSで生成したMP3）
        output_path: 出力動画パス
        model: 使用するReplicateモデル

    Returns:
        リップシンク済み動画のパス
    """
    _check_api_key()

    print(f"💋 リップシンク処理開始...")
    print(f"   動画: {video_path}")
    print(f"   音声: {audio_path}")

    # ファイルをReplicateにアップロードして実行
    with open(video_path, "rb") as vf, open(audio_path, "rb") as af:
        output = replicate.run(
            model,
            input={
                "face": vf,
                "audio": af,
                "pads": "0 10 0 0",         # 口周りのパディング調整
                "smooth": True,              # スムーズな口の動き
                "resize_factor": 1,
            },
        )

    # 出力URLからダウンロード
    output_url = str(output)
    _download_file(output_url, output_path)
    print(f"✅ リップシンク完了: {output_path}")
    return output_path


def apply_lipsync_advanced(
    video_path: str,
    audio_path: str,
    output_path: str,
) -> str:
    """
    より高品質なlipsync（Replicate REST API直接呼び出し）
    マンガスタイルのキャラクターに最適化
    """
    _check_api_key()

    api_token = os.environ["REPLICATE_API_TOKEN"]
    headers = {
        "Authorization": f"Token {api_token}",
        "Content-Type": "application/json",
    }

    # ファイルをbase64エンコード（小さなファイル向け）
    import base64
    with open(video_path, "rb") as vf:
        video_b64 = "data:video/mp4;base64," + base64.b64encode(vf.read()).decode()
    with open(audio_path, "rb") as af:
        audio_b64 = "data:audio/mpeg;base64," + base64.b64encode(af.read()).decode()

    # 予測を作成
    response = requests.post(
        "https://api.replicate.com/v1/predictions",
        headers=headers,
        json={
            "version": LIPSYNC_MODEL.split(":")[1],
            "input": {
                "face": video_b64,
                "audio": audio_b64,
                "smooth": True,
                "pads": "0 10 0 0",
            },
        },
        timeout=60,
    )
    response.raise_for_status()
    prediction = response.json()
    prediction_id = prediction["id"]
    print(f"   予測ID: {prediction_id}")

    # ポーリングで完了待ち
    return _poll_prediction(prediction_id, output_path, headers)


def _poll_prediction(prediction_id: str, output_path: str, headers: dict, timeout: int = 600) -> str:
    """Replicate予測の完了を待つ"""
    start = time.time()
    interval = 5

    while time.time() - start < timeout:
        resp = requests.get(
            f"https://api.replicate.com/v1/predictions/{prediction_id}",
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")

        if status == "succeeded":
            output_url = data["output"]
            if isinstance(output_url, list):
                output_url = output_url[0]
            _download_file(output_url, output_path)
            return output_path

        elif status == "failed":
            error = data.get("error", "不明なエラー")
            raise RuntimeError(f"Replicate 予測失敗: {error}")

        print(f"   ステータス: {status} ... {int(time.time() - start)}秒経過")
        time.sleep(interval)

    raise TimeoutError(f"Replicate タスクがタイムアウトしました ({timeout}秒)")


def _download_file(url: str, output_path: str) -> None:
    """ファイルをダウンロード"""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


def _check_api_key() -> None:
    if not os.environ.get("REPLICATE_API_TOKEN"):
        raise ValueError("REPLICATE_API_TOKEN が設定されていません。.env ファイルを確認してください。")
