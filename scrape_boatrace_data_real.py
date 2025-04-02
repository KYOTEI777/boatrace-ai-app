
import requests
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime
import time

DB_NAME = "boatrace_data.db"

def create_tables(conn):
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS entries (jyo_code TEXT, race_date TEXT, race_no INTEGER, lane INTEGER, motor_no INTEGER, win_rate REAL, two_win_rate REAL, weight REAL, st REAL, course INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS exhibitions (jyo_code TEXT, race_date TEXT, race_no INTEGER, lane INTEGER, exhibition_time REAL, exhibition_rank INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS weather (jyo_code TEXT, race_date TEXT, race_no INTEGER, weather TEXT, wind_speed REAL, wave_height REAL, temp REAL, water_temp REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS results (jyo_code TEXT, race_date TEXT, race_no INTEGER, lane INTEGER, rank INTEGER)")
    conn.commit()

def scrape_and_insert(jyo_code, date_str):
    print(f"取得中: {date_str} / 場: {jyo_code}")
    conn = sqlite3.connect(DB_NAME)
    create_tables(conn)
    cur = conn.cursor()

    for race_no in range(1, 13):
        try:
            url = f"https://www.boatrace.jp/owpc/pc/race/raceresult?rno={race_no}&jcd={jyo_code}&hd={date_str}"
            r = requests.get(url)
            soup = BeautifulSoup(r.content, "html.parser")

            # 天気・風・波情報の取得
            weather_box = soup.select_one(".weather1_body")
            if weather_box:
                weather_text = weather_box.select_one(".weather1_bodyUnitLabel").text.strip()
                wind_text = weather_box.select("div.weather1_bodyUnit")[1].text.strip()
                wave_text = weather_box.select("div.weather1_bodyUnit")[2].text.strip()
                temp = weather_box.select("div.weather1_bodyUnit")[3].text.strip().replace("℃", "")
                water_temp = weather_box.select("div.weather1_bodyUnit")[4].text.strip().replace("℃", "")

                wind_speed = float(wind_text.replace("m", "").strip("無風").strip()) if "m" in wind_text else 0.0
                wave_height = float(wave_text.replace("cm", "").strip()) if "cm" in wave_text else 0.0

                cur.execute("INSERT INTO weather VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (jyo_code, date_str, race_no, weather_text, wind_speed, wave_height, float(temp), float(water_temp)))

            # 選手・展示・ST・体重など取得
            rows = soup.select("div.race_table_01 tr")[1:7]
            etimes = []
            for i, row in enumerate(rows, start=1):
                cols = row.find_all("td")
                if len(cols) < 10:
                    continue
                motor_no = int(cols[3].text.strip())
                win_rate = float(cols[6].text.strip() or 0)
                two_win = float(cols[7].text.strip() or 0)
                weight = float(cols[8].text.strip() or 0)
                st_text = cols[9].text.strip().replace("F", "").replace("L", "")
                st = float(st_text) if st_text else 0.0
                course = i  # 仮: 枠なり進入
                etime = float(cols[4].text.strip()) if cols[4].text.strip() else 0.0
                etimes.append((i, etime))

                cur.execute("INSERT INTO entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (jyo_code, date_str, race_no, i, motor_no, win_rate, two_win, weight, st, course))

            # 展示タイム順に順位付け
            etimes.sort(key=lambda x: x[1])
            for rank, (lane, etime) in enumerate(etimes, start=1):
                cur.execute("INSERT INTO exhibitions VALUES (?, ?, ?, ?, ?, ?)",
                            (jyo_code, date_str, race_no, lane, etime, rank))

            # 仮の着順（実装中）
            for lane in range(1, 7):
                cur.execute("INSERT INTO results VALUES (?, ?, ?, ?, ?)",
                            (jyo_code, date_str, race_no, lane, lane))

            conn.commit()
            time.sleep(0.3)
        except Exception as e:
            print(f"❌ エラー: {date_str} R{race_no} → {e}")
    conn.close()

def run():
    jyo_list = ["12", "02"]
    date_list = ["20250401", "20250402"]
    for d in date_list:
        for j in jyo_list:
            scrape_and_insert(j, d)

if __name__ == "__main__":
    run()
