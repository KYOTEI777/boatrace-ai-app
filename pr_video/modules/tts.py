"""
TTS Module: Edge-TTS による日本語音声生成
MIZUMONOキャラクターの渋いナレーション音声を生成する
"""

import asyncio
import edge_tts
from pathlib import Path


# PRスクリプト（水ノ上玄舟のセリフ）
PR_SCRIPT = """
水面を制する者が、勝利を制す。

俺の名は…水ノ上玄舟。

長年、ボートレースの世界で生きてきた。
勝者と敗者を分けるのは、運ではない。
データだ。

展示タイム、モーター勝率、風と波、選手の癖。
すべてを読み解いた者だけが、水面の真実を知る。

そのために、AIが生まれた。

ボートレースAI予測システム。
機械学習が、俺の経験と同じ目線で、レースを分析する。

信じるのも、疑うのも、お前次第だ。
だが…データは、嘘をつかない。
"""

# 音声設定
VOICE_MALE_DEEP = "ja-JP-KeitaNeural"   # 標準男性
VOICE_MALE_OLDER = "ja-JP-NaokiNeural"  # やや渋め

# キャラクター設定：渋い老人ボイス用パラメータ
VOICE_SETTINGS = {
    "voice": VOICE_MALE_OLDER,
    "rate": "-15%",    # やや遅め（老人らしく）
    "pitch": "-8Hz",   # やや低め（渋く）
    "volume": "+0%",
}


async def generate_voice_async(text: str, output_path: str, settings: dict = None) -> str:
    """Edge-TTSで音声を非同期生成"""
    if settings is None:
        settings = VOICE_SETTINGS

    communicate = edge_tts.Communicate(
        text=text,
        voice=settings["voice"],
        rate=settings["rate"],
        pitch=settings["pitch"],
        volume=settings["volume"],
    )
    await communicate.save(output_path)
    return output_path


def generate_voice(text: str, output_path: str, settings: dict = None) -> str:
    """Edge-TTSで音声を生成（同期ラッパー）"""
    asyncio.run(generate_voice_async(text, output_path, settings))
    print(f"✅ 音声生成完了: {output_path}")
    return output_path


def generate_pr_voice(output_dir: str = "output") -> str:
    """PRスクリプトの音声を生成"""
    output_path = str(Path(output_dir) / "mizumono_voice.mp3")
    return generate_voice(PR_SCRIPT, output_path)


if __name__ == "__main__":
    generate_pr_voice()
