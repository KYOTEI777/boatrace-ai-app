# 水もの（MIZUMONO）モジュール
# ボートレースにおける気象・水面条件の分析と予測への組み込み

import sqlite3
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = 'DejaVu Sans'

DB_NAME = "boatrace_data.db"

WEATHER_CONDITIONS = {
    "晴": "sunny",
    "曇": "cloudy",
    "雨": "rainy",
    "雪": "snow",
    "霧": "fog",
}

WIND_THRESHOLDS = {
    "無風〜微風": (0, 2),
    "弱風": (2, 5),
    "中風": (5, 8),
    "強風": (8, 99),
}

WAVE_THRESHOLDS = {
    "静水面": (0, 5),
    "小波": (5, 10),
    "中波": (10, 20),
    "荒波": (20, 99),
}


def create_weather_table(conn):
    """weather テーブルを作成（存在しない場合）"""
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS weather (
            jyo_code TEXT,
            race_date TEXT,
            race_no INTEGER,
            weather TEXT,
            wind_speed REAL,
            wave_height REAL,
            temp REAL,
            water_temp REAL,
            wind_direction TEXT,
            PRIMARY KEY (jyo_code, race_date, race_no)
        )
    """)
    conn.commit()


def get_weather_features(conn, date, jyo_code, race_no):
    """予測モデル用の気象特徴量を取得"""
    query = """
        SELECT wind_speed, wave_height, temp, water_temp
        FROM weather
        WHERE race_date = ? AND jyo_code = ? AND race_no = ?
    """
    df = pd.read_sql_query(query, conn, params=(date, jyo_code, race_no))
    if df.empty:
        return None
    return df.iloc[0]


def analyze_wind_impact(conn):
    """風速が各コースの勝率に与える影響を分析"""
    query = """
        SELECT
            w.wind_speed,
            r.lane,
            COUNT(*) AS race_count,
            SUM(CASE WHEN r.rank = 1 THEN 1 ELSE 0 END) AS wins
        FROM weather w
        JOIN results r ON
            w.jyo_code = r.jyo_code AND
            w.race_date = r.race_date AND
            w.race_no = r.race_no
        GROUP BY
            CASE
                WHEN w.wind_speed < 2 THEN '無風〜微風(0-2m)'
                WHEN w.wind_speed < 5 THEN '弱風(2-5m)'
                WHEN w.wind_speed < 8 THEN '中風(5-8m)'
                ELSE '強風(8m+)'
            END,
            r.lane
        ORDER BY w.wind_speed, r.lane
    """
    return pd.read_sql_query(query, conn)


def analyze_wave_impact(conn):
    """波高が各コースの勝率に与える影響を分析"""
    query = """
        SELECT
            CASE
                WHEN w.wave_height < 5  THEN '静水面(0-5cm)'
                WHEN w.wave_height < 10 THEN '小波(5-10cm)'
                WHEN w.wave_height < 20 THEN '中波(10-20cm)'
                ELSE '荒波(20cm+)'
            END AS wave_category,
            r.lane,
            COUNT(*) AS race_count,
            SUM(CASE WHEN r.rank = 1 THEN 1 ELSE 0 END) AS wins,
            ROUND(100.0 * SUM(CASE WHEN r.rank = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_rate
        FROM weather w
        JOIN results r ON
            w.jyo_code = r.jyo_code AND
            w.race_date = r.race_date AND
            w.race_no = r.race_no
        GROUP BY wave_category, r.lane
        ORDER BY w.wave_height, r.lane
    """
    return pd.read_sql_query(query, conn)


def analyze_upset_conditions(conn):
    """波乱（1コース以外の1着）が起きやすい条件を分析"""
    query = """
        SELECT
            CASE
                WHEN w.wind_speed < 2 THEN '無風〜微風'
                WHEN w.wind_speed < 5 THEN '弱風'
                WHEN w.wind_speed < 8 THEN '中風'
                ELSE '強風'
            END AS wind_cat,
            CASE
                WHEN w.wave_height < 5  THEN '静水面'
                WHEN w.wave_height < 10 THEN '小波'
                WHEN w.wave_height < 20 THEN '中波'
                ELSE '荒波'
            END AS wave_cat,
            COUNT(*) AS total_races,
            SUM(CASE WHEN r.rank = 1 AND r.lane = 1 THEN 1 ELSE 0 END) AS course1_wins,
            SUM(CASE WHEN r.rank = 1 AND r.lane != 1 THEN 1 ELSE 0 END) AS upset_wins,
            ROUND(100.0 * SUM(CASE WHEN r.rank = 1 AND r.lane != 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS upset_rate
        FROM weather w
        JOIN results r ON
            w.jyo_code = r.jyo_code AND
            w.race_date = r.race_date AND
            w.race_no = r.race_no
        WHERE r.lane IN (1)
        GROUP BY wind_cat, wave_cat
        ORDER BY upset_rate DESC
    """
    return pd.read_sql_query(query, conn)


def get_mizumono_score(wind_speed, wave_height, water_temp=None):
    """
    水もの指数を計算。
    波風が強いほど荒れやすく（＝水もの度が高い）、外コース有利になる傾向。
    Returns: 0.0〜1.0 のスコア（高いほど荒れ展開の可能性）
    """
    wind_score = min(wind_speed / 10.0, 1.0)
    wave_score = min(wave_height / 25.0, 1.0)

    # 水温が低いとモーターの性能差が出やすい（荒れ度上昇）
    temp_score = 0.0
    if water_temp is not None:
        temp_score = max(0.0, (20.0 - water_temp) / 20.0)

    score = (wind_score * 0.45) + (wave_score * 0.45) + (temp_score * 0.10)
    return round(min(score, 1.0), 3)


def render_mizumono_gauge(score):
    """水もの指数のゲージを描画"""
    fig, ax = plt.subplots(figsize=(6, 1.2))
    ax.barh([0], [score], color=_score_color(score), height=0.5)
    ax.barh([0], [1.0 - score], left=[score], color="#e0e0e0", height=0.5)
    ax.set_xlim(0, 1)
    ax.set_yticks([])
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0", "低", "中", "高", "最高"], fontsize=9)
    ax.set_title(f"水もの指数: {score:.2f}", fontsize=11)
    ax.spines[['top', 'right', 'left']].set_visible(False)
    plt.tight_layout()
    return fig


def _score_color(score):
    if score < 0.3:
        return "#4CAF50"   # green: 安定
    elif score < 0.6:
        return "#FF9800"   # orange: 中程度
    else:
        return "#F44336"   # red: 荒れ


def render_mizumono_tab(conn):
    """StreamlitのMIZUMONOタブを描画"""
    st.subheader("🌊 水もの分析（MIZUMONO）")
    st.markdown(
        "**水もの**とは、気象・水面条件による展開の揺らぎのこと。"
        "風速・波高・水温が高いほど荒れた展開になりやすく、外コースが浮上しやすくなります。"
    )

    # ── リアルタイム水もの指数計算 ──────────────────────────
    st.markdown("---")
    st.markdown("#### 水もの指数シミュレーター")
    col1, col2, col3 = st.columns(3)
    with col1:
        wind = st.slider("風速 (m/s)", 0.0, 15.0, 3.0, 0.5, key="mz_wind")
    with col2:
        wave = st.slider("波高 (cm)", 0.0, 30.0, 5.0, 1.0, key="mz_wave")
    with col3:
        wtemp = st.slider("水温 (℃)", 5.0, 35.0, 20.0, 0.5, key="mz_wtemp")

    score = get_mizumono_score(wind, wave, wtemp)
    fig = render_mizumono_gauge(score)
    st.pyplot(fig)
    plt.close(fig)

    level_label = "🟢 安定" if score < 0.3 else ("🟡 やや荒れ" if score < 0.6 else "🔴 荒れ展開")
    st.info(f"水もの度: {level_label}　（スコア: {score:.2f}）")

    if score >= 0.5:
        st.warning("⚠️ 荒れ展開の可能性が高め。外コース（4〜6コース）の台頭に注意。")
    else:
        st.success("✅ 比較的安定した水面。インコース（1〜3コース）が有利な傾向。")

    # ── DB分析セクション ──────────────────────────────────
    st.markdown("---")
    st.markdown("#### 過去データによる波高・風速の影響分析")

    try:
        wave_df = analyze_wave_impact(conn)
        if wave_df.empty:
            st.info("weather テーブルにデータがありません。先にデータを取得してください。")
            return

        st.markdown("**波高別・コース別 勝率 (%)**")
        pivot = wave_df.pivot_table(
            index="wave_category", columns="lane",
            values="win_rate", aggfunc="first"
        )
        pivot.columns = [f"{c}コース" for c in pivot.columns]
        st.dataframe(pivot.style.background_gradient(cmap="RdYlGn", axis=None))

        # 波乱率分析
        upset_df = analyze_upset_conditions(conn)
        if not upset_df.empty:
            st.markdown("**条件別 波乱率（1コース以外1着）**")
            st.dataframe(
                upset_df[["wind_cat", "wave_cat", "total_races", "upset_rate"]]
                .rename(columns={
                    "wind_cat": "風速区分",
                    "wave_cat": "波高区分",
                    "total_races": "レース数",
                    "upset_rate": "波乱率(%)"
                })
                .sort_values("波乱率(%)", ascending=False)
                .reset_index(drop=True)
            )

    except Exception as e:
        st.error(f"分析エラー: {e}")


def add_weather_features_to_df(df, conn):
    """
    予測用DataFrameに気象特徴量を追加する。
    df には race_date, jyo_code, race_no 列が必要。
    """
    if df.empty:
        return df

    # 同一レースなので最初の行から取得
    row = df.iloc[0]
    features = get_weather_features(conn, row["race_date"] if "race_date" in df.columns else None,
                                    row.get("jyo_code"), row.get("race_no"))
    if features is None:
        df["wind_speed"] = 0.0
        df["wave_height"] = 0.0
        df["water_temp"] = 20.0
    else:
        df["wind_speed"] = features["wind_speed"]
        df["wave_height"] = features["wave_height"]
        df["water_temp"] = features["water_temp"]

    df["mizumono_score"] = df.apply(
        lambda r: get_mizumono_score(r["wind_speed"], r["wave_height"], r["water_temp"]),
        axis=1
    )
    return df
