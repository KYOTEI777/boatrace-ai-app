
import schedule
import time
import subprocess
from datetime import datetime

def job():
    today = datetime.today().strftime("%Y%m%d")
    cmd = f"python scrape_boatrace_data_full.py --start {today} --end {today} --all_jyo"
    print(f"実行中: {cmd}")
    subprocess.run(cmd, shell=True)

# 毎朝08:00に実行
schedule.every().day.at("08:00").do(job)

print("⏳ フルオート自動スクレイピング開始（毎朝08:00）")

while True:
    schedule.run_pending()
    time.sleep(60)
