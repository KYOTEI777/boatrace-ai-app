# ボートレース データ取得＋分析準備（AI予測ロジック搭載版）
# ライブラリ：requests, BeautifulSoup4, sqlite3, pandas, schedule, matplotlib, streamlit, numpy, scikit-learn, joblib

import requests
from bs4 import BeautifulSoup
import sqlite3
import time
from datetime import datetime
import schedule
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib

DB_NAME = "boatrace_data.db"
MODEL_PATH = "boatrace_model.pkl"

# -------------------------------
# AI予測モデルに使う特徴量を拡張
# -------------------------------
def predict_race_outcome_ai(date, jyo_code, race_no):
    try:
        model = joblib.load(MODEL_PATH)
    except:
        return None

    conn = sqlite3.connect(DB_NAME)
    query = '''
        SELECT e.lane, e.exhibition_time, e.straight_time, e.turn_time,
               m.win_rate AS motor_win_rate, m.two_win_rate AS motor_2win,
               n.win_rate AS player_win_rate, n.two_win_rate AS player_2win
        FROM exhibitions e
        JOIN entries n ON e.jyo_code = n.jyo_code AND e.race_date = n.race_date AND e.race_no = n.race_no AND e.lane = n.lane
        JOIN motors m ON m.jyo_code = n.jyo_code AND m.race_date = n.race_date AND m.motor_no = n.motor_no
        WHERE e.race_date = ? AND e.jyo_code = ? AND e.race_no = ?
    '''
    df = pd.read_sql_query(query, conn, params=(date, jyo_code, race_no))
    conn.close()

    if df.empty:
        return None

    X = df[["exhibition_time", "straight_time", "turn_time", "motor_win_rate", "motor_2win", "player_win_rate", "player_2win", "lane"]]
    df["予測(舟券絡み)確率"] = model.predict_proba(X)[:, 1]
    return df.sort_values("予測(舟券絡み)確率", ascending=False)

# -------------------------------
# Streamlit UI: タブ統合版
# -------------------------------
def run_full_app():
    st.set_page_config(page_title="ボートレース分析", layout="wide")
    st.title("🚤 ボートレース分析＆予測ツール")

    tab1, tab2 = st.tabs(["AI展開予測", "モデル評価"])

    with tab1:
        st.subheader("AIによる着順絡み予測")
        date = st.text_input("日付 (例: 20250402)", "", key="pred_date")
        jyo = st.text_input("場コード (例: 24)", "", key="pred_jyo")
        race = st.text_input("レース番号 (1〜12)", "", key="pred_race")
        if date and jyo and race.isdigit():
            pred_df = predict_race_outcome_ai(date, jyo, int(race))
            if pred_df is not None:
                st.dataframe(pred_df.reset_index(drop=True))
            else:
                st.warning("モデルまたはデータが不足しています")

    with tab2:
        st.subheader("モデル精度 (Accuracy, F1)")
        if st.button("モデル再学習＆評価"):
            model, report_df = train_and_evaluate_model()
            joblib.dump(model, MODEL_PATH)
            st.success("モデル再学習・保存完了！")
            st.dataframe(report_df.round(3))
