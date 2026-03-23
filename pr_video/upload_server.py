"""
簡易ファイルアップロードサーバー
ブラウザから画像をアップロードするために使用
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import os, cgi
from pathlib import Path

SAVE_DIR = Path(__file__).parent / "assets"

HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>画像アップロード</title>
<style>body{font-family:sans-serif;max-width:500px;margin:80px auto;text-align:center}
input[type=file]{margin:20px}button{background:#2196F3;color:white;border:none;padding:12px 30px;font-size:16px;border-radius:6px;cursor:pointer}</style>
</head><body>
<h2>🖼️ MIZUMONO画像アップロード</h2>
<p>デスクトップの <strong>mizumono.jpg</strong> を選択してアップロード</p>
<form method="POST" enctype="multipart/form-data">
  <input type="file" name="file" accept="image/*"><br>
  <button type="submit">アップロード</button>
</form>
</body></html>"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML.encode())

    def do_POST(self):
        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers,
                                environ={"REQUEST_METHOD": "POST"})
        file_item = form["file"]
        if file_item.filename:
            save_path = SAVE_DIR / "mizumono.jpg"
            with open(save_path, "wb") as f:
                f.write(file_item.file.read())
            msg = f"✅ 保存完了: {save_path}".encode()
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(("<h2>" + save_path.name + " 保存完了</h2><p>このページを閉じてください。</p>").encode())
            print(f"\n✅ 画像保存完了: {save_path}\n   Ctrl+C でサーバーを停止してください")

    def log_message(self, *args): pass

if __name__ == "__main__":
    port = 8765
    print(f"\n📂 アップロードサーバー起動中...")
    print(f"   ブラウザで → http://localhost:{port}")
    print(f"   アップロード後に Ctrl+C で停止\n")
    HTTPServer(("", port), Handler).serve_forever()
