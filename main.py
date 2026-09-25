
import os
import time
import json
import datetime
import urllib.parse
import urllib.request
import gspread
from google.oauth2.service_account import Credentials

def get_last_month_dates():
    """先月1日と先月末日の日付文字列を取得"""
    today = datetime.date.today()
    first_day_this_month = today.replace(day=1)
    last_month_end = first_day_this_month - datetime.timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    return last_month_start.strftime("%Y-%m-%d"), last_month_end.strftime("%Y-%m-%d")

def get_pixiv_count(tag, scd, ecd):
    """Pixiv Ajax APIを使って指定期間の作品数を取得"""
    encoded_tag = urllib.parse.quote(tag)
    url = f"https://www.pixiv.net/ajax/search/artworks/{encoded_tag}?word={encoded_tag}&order=date_d&scd={scd}&ecd={ecd}&s_mode=s_tag&p=1&lang=ja"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.pixiv.net/"
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            if not data.get("error"):
                return data["body"]["illustManga"]["total"]
    except Exception as e:
        print(f"Error fetching [{tag}]: {e}")
    return 0

def main():
    scd, ecd = get_last_month_dates()
    target_month = scd[:7] # YYYY-MM
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    
    print(f"Target Period: {scd} to {ecd}")

    # Google Sheets 認証
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    gcp_key = json.loads(os.environ["GCP_SA_KEY"])
    creds = Credentials.from_service_account_info(gcp_key, scopes=scope)
    client = gspread.authorize(creds)
    
    spreadsheet_id = os.environ["SPREADSHEET_ID"]
    sheet = client.open_by_key(spreadsheet_id).sheet1

    # C列（検索タグ）の一覧を取得（ヘッダーを除く2行目以降）
    c_column_values = sheet.col_values(3)[1:] # 3列目＝C列
    
    a_column_updates = []
    b_column_updates = []
    d_column_updates = []

    for tag in c_column_values:
        if not tag.strip():
            a_column_updates.append([""])
            b_column_updates.append([""])
            d_column_updates.append([""])
            continue

        count = get_pixiv_count(tag, scd, ecd)
        print(f"{tag}: {count}")
        
        a_column_updates.append([today_str])
        b_column_updates.append([target_month])
        d_column_updates.append([count])
        time.sleep(1.5) # アクセス負荷軽減

    # まとめてA列・B列・D列に書き込み
    num_rows = len(c_column_values)
    if num_rows > 0:
        sheet.update(f"A2:A{num_rows + 1}", a_column_updates)
        sheet.update(f"B2:B{num_rows + 1}", b_column_updates)
        sheet.update(f"D2:D{num_rows + 1}", d_column_updates)
        print("Successfully updated Google Sheet!")

if __name__ == "__main__":
    main()
