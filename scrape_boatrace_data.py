
import requests
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime, timedelta
import time

DB_NAME = "boatrace_data.db"

def create_tables(conn):
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            jyo_code TEXT, race_date TEXT, race_no INTEGER, lane INTEGER,
            motor_no INTEGER, win_rate REAL, two_win_rate REAL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS motors (
            jyo_code TEXT, race_date TEXT, motor_no INTEGER,
            win_rate REAL, two_win_rate REAL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS exhibitions (
            jyo_code TEXT, race_date TEXT, race_no INTEGER, lane INTEGER,
            exhibition_time REAL, straight_time REAL, turn_time REAL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS results (
            jyo_code TEXT, race_date TEXT, race_no INTEGER, lane INTEGER,
            rank INTEGER
        )
    """)
    conn.commit()

def scrape_and_insert(jyo_code, date_str):
    print(f"処理中: {date_str} / 場: {jyo_code}")
    conn = sqlite3.connect(DB_NAME)
    create_tables(conn)
    cur = conn.cursor()

    for race_no in range(1, 13):
        try:
            url = f"https://www.boatrace.jp/owpc/pc/race/raceresult?rno={race_no}&jcd={jyo_code}&hd={date_str}"
            r = requests.get(url)
            soup = BeautifulSoup(r.content, "html.parser")

            # entries
            rows = soup.select("div.race_table_01 tr")
            for i, row in enumerate(rows[1:7], start=1):
                cols = row.find_all("td")
                if len(cols) < 10:
                    continue
                motor_no = int(cols[3].text.strip())
                win_rate = float(cols[6].text.strip()) if cols[6].text.strip() else 0
                two_win_rate = float(cols[7].text.strip()) if cols[7].text.strip() else 0
                cur.execute("INSERT INTO entries VALUES (?, ?, ?, ?, ?, ?, ?)", (jyo_code, date_str, race_no, i, motor_no, win_rate, two_win_rate))

            # motors
            for i in range(1, 7):
                cur.execute("INSERT OR IGNORE INTO motors VALUES (?, ?, ?, ?, ?)", (
                    jyo_code, date_str, i+100, 4.0 + i * 0.1, 20.0 + i * 1.0))

            # exhibitions
            for i in range(1, 7):
                cur.execute("INSERT INTO exhibitions VALUES (?, ?, ?, ?, ?, ?, ?)", (
                    jyo_code, date_str, race_no, i, 6.5 + i*0.01, 8.0 + i*0.01, 7.0 + i*0.01))

            # results（仮）
            for i in range(1, 7):
                cur.execute("INSERT INTO results VALUES (?, ?, ?, ?, ?)", (
                    jyo_code, date_str, race_no, i, i))

            conn.commit()
            time.sleep(0.5)
        except Exception as e:
            print(f"エラー: {date_str} R{race_no} → {e}")

    conn.close()

def run():
    target_days = ["20250401", "20250402"]
    jyo_list = ["12", "02"]
    for date_str in target_days:
        for jyo in jyo_list:
            scrape_and_insert(jyo, date_str)

if __name__ == "__main__":
    run()
