import json
import os
import urllib.request
import urllib.error
from http.server import SimpleHTTPRequestHandler, HTTPServer
from datetime import datetime

PORT = 1004
DB_FILE = 'database.json'

# Mengambil config dari .env
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "mmstiore")
# Membaca URL dari docker-compose, default mengarah ke service 'web'
MAIN_APP_URL = os.getenv("MAIN_APP_URL", "http://web:8080/api/redeem")

def init_db():
    if not os.path.exists(DB_FILE) or os.path.isdir(DB_FILE) or os.path.getsize(DB_FILE) == 0:
        if os.path.isdir(DB_FILE): os.rmdir(DB_FILE)
        save_db({"users": {}, "inventory": {}, "history": []})

def load_db():
    try:
        with open(DB_FILE, 'r') as f: return json.load(f)
    except:
        return {"users": {}, "inventory": {}, "history": []}

def save_db(data):
    with open(DB_FILE, 'w') as f: json.dump(data, f, indent=4)

def send_to_main_app(email, code):
    data = json.dumps({"email": email, "code": code}).encode('utf-8')
    req = urllib.request.Request(MAIN_APP_URL, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            res_data = json.loads(response.read().decode())
            return {"success": res_data.get("success", False), "message": res_data.get("message", "Berhasil")}
    except urllib.error.HTTPError as e:
        try:
            error_res = json.loads(e.read().decode())
            msg = error_res.get("message", f"HTTP Error {e.code}")
        except:
            msg = f"HTTP Error {e.code}"
        return {"success": False, "message": msg}
    except Exception as e:
        return {"success": False, "message": f"Gagal terhubung ke server utama: {str(e)}"}

class ResellerAPIHandler(SimpleHTTPRequestHandler):
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_POST(self):
        if not self.path.startswith('/api/'): return self.send_response(404)
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = json.loads(self.rfile.read(content_length))
        db = load_db()
        
        if self.path == '/api/login':
            user = post_data.get('username')
            pw = post_data.get('password')
            if user == 'admin' and pw == ADMIN_PASSWORD:
                return self.send_json({"success": True, "role": "admin", "username": "admin"})
            if user in db['users'] and db['users'][user]['password'] == pw:
                if db['users'][user]['status'] != 'approved': return self.send_json({"success": False, "msg": "Belum di-approve!"})
                return self.send_json({"success": True, "role": db['users'][user]['role'], "username": user})
            return self.send_json({"success": False, "msg": "Login salah!"})

        elif self.path == '/api/register':
            user = post_data.get('username')
            pw = post_data.get('password')
            if not user or not pw: return self.send_json({"success": False, "msg": "Wajib diisi!"})
            if user in db['users'] or user == 'admin': return self.send_json({"success": False, "msg": "Username terpakai!"})
            db['users'][user] = {"password": pw, "role": "reseller", "status": "pending"}
            db['inventory'][user] = {}
            save_db(db)
            return self.send_json({"success": True, "msg": "Menunggu approval admin."})

        elif self.path == '/api/admin_action':
            action = post_data.get('action')
            target = post_data.get('target')
            if action == 'approve': db['users'][target]['status'] = 'approved'
            elif action == 'delete':
                if target in db['users']: del db['users'][target]
                if target in db['inventory']: del db['inventory'][target]
            elif action == 'add_stock':
                team = post_data.get('team')
                codes = post_data.get('codes', '').split('\n')
                if team not in db['inventory'][target]: db['inventory'][target][team] = []
                db['inventory'][target][team].extend([c.strip() for c in codes if c.strip()])
            save_db(db)
            return self.send_json({"success": True})

        elif self.path == '/api/invite':
            user = post_data.get('username')
            email = post_data.get('email')
            team = post_data.get('team')
            if team not in db['inventory'].get(user, {}) or len(db['inventory'][user][team]) == 0:
                return self.send_json({"success": False, "message": "Stok habis!"})
            
            used_code = db['inventory'][user][team].pop(0)
            main_app_result = send_to_main_app(email, used_code)
            
            if main_app_result["success"]:
                log = {
                    "id": f"REC-{datetime.now().strftime('%Y%m%d%H%M%S')}", "reseller": user, 
                    "email": email, "team": team, "code": used_code, "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                db['history'].insert(0, log)
                save_db(db)
                return self.send_json({"success": True, "message": main_app_result["message"], "receipt": log})
            else:
                db['inventory'][user][team].insert(0, used_code)
                return self.send_json({"success": False, "message": main_app_result["message"]})

    def do_GET(self):
        if self.path == '/api/data': return self.send_json(load_db())
        if self.path == '/' or self.path == '/index.html': self.path = '/reseller.html'
        return super().do_GET()

if __name__ == '__main__':
    init_db()
    server = HTTPServer(('0.0.0.0', PORT), ResellerAPIHandler)
    print(f"Reseller Container Aktif di Port {PORT}")
    server.serve_forever()