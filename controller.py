from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import qrcode
from io import BytesIO
import threading
import time
import base64
import random
import os
import requests
import sqlite3
from bakong_khqr import KHQR
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "super-secret-key"

# =============================
# KHQR / BAKONG CONFIG
# =============================
API_TOKEN_BAKONG = os.getenv("BAKONG_API_TOKEN", "YOUR_API_TOKEN_HERE")
BANK_ACCOUNT = os.getenv("BANK_ACCOUNT", "chhira_ly@aclb")
PHONE_NUMBER = os.getenv("PHONE_NUMBER", "855882000544")
TELEGRAM_BOT_TOKEN = "8236265021:AAHuNos6PJTHld-Zx8URV4RgQUGKlG7qzdg"
TELEGRAM_CHAT_ID = "-1003461060957"
khqr = KHQR(API_TOKEN_BAKONG)

# =============================
# ADMIN CONFIG
# =============================
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = generate_password_hash(
    os.getenv("ADMIN_PASSWORD", "admin123")
)

# =============================
# PAYMENT STATUS & TRANSACTIONS
# =============================
payment_status = {}
transactions = {}  # Store transaction details

# =============================
# HELPERS
# =============================
def generate_short_transaction_id(length=8):
    return ''.join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=length))

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message})

def check_payment_cart(md5, player_id, server_id, item_name, order_id, amount):
    timeout = 180
    start = time.time()
    payment_status[md5] = "PENDING"

    while time.time() - start < timeout:
        try:
            r = requests.get(f"https://panha-dev.vercel.app/check_payment/{md5}", timeout=5)
            data = r.json()
            if data.get("success") and data.get("status") == "PAID":
                payment_status[md5] = "PAID"
                transactions[md5] = {
                    "order_id": order_id,
                    "status": "SUCCESS",
                    "game": "Mobile Legends",
                    "player_id": player_id,
                    "server_id": server_id,
                    "item": item_name,
                    "amount": amount,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "payment_method": "KHQR"
                }
                send_telegram(f"{player_id} {server_id} {item_name}") 
                send_telegram(f"✅ MLBB Order #{order_id}\n{player_id} ({server_id})\n{item_name}\n${amount}{md5}")            
                return
        except:
            pass
        time.sleep(1)

    payment_status[md5] = "EXPIRED"
    transactions[md5] = {
        "order_id": order_id,
        "status": "EXPIRED",
        "game": "Mobile Legends",
        "player_id": player_id,
        "server_id": server_id,
        "item": item_name,
        "amount": amount,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "payment_method": "KHQR"
    }

def check_payment_cart_f(md5, player_uid, item_name, order_id, amount):
    timeout = 180
    start = time.time()
    payment_status[md5] = "PENDING"

    while time.time() - start < timeout:
        try:
            r = requests.get(f"https://panha-dev.vercel.app/check_payment/{md5}", timeout=5)
            data = r.json()
            if data.get("success") and data.get("status") == "PAID":
                payment_status[md5] = "PAID"
                transactions[md5] = {
                    "order_id": order_id,
                    "status": "SUCCESS",
                    "game": "Free Fire",
                    "player_uid": player_uid,
                    "item": item_name,
                    "amount": amount,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "payment_method": "KHQR"
                }
                send_telegram(f"✅ FF Order #{order_id}\n{player_uid}\n{item_name}\n${amount}")
                return
        except:
            pass
        time.sleep(1)

    payment_status[md5] = "EXPIRED"
    transactions[md5] = {
        "order_id": order_id,
        "status": "EXPIRED",
        "game": "Free Fire",
        "player_uid": player_uid,
        "item": item_name,
        "amount": amount,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "payment_method": "KHQR"
    }

def check_payment_cart_roblox(md5, username, password, item_name, order_id, amount):
    """For Roblox - username and password"""
    timeout = 180
    start = time.time()
    payment_status[md5] = "PENDING"

    while time.time() - start < timeout:
        try:
            r = requests.get(f"https://panha-dev.vercel.app/check_payment/{md5}", timeout=5)
            data = r.json()
            if data.get("success") and data.get("status") == "PAID":
                payment_status[md5] = "PAID"
                transactions[md5] = {
                    "order_id": order_id,
                    "status": "SUCCESS",
                    "game": "Roblox",
                    "username": username,
                    "item": item_name,
                    "amount": amount,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "payment_method": "KHQR"
                }
                masked_password = password[:2] + "*" * (len(password) - 2)
                send_telegram(f"✅ Roblox Order #{order_id}\nUsername: {username}\nPassword: {masked_password}\nItem: {item_name}\n${amount}")
                return
        except:
            pass
        time.sleep(1)

    payment_status[md5] = "EXPIRED"
    transactions[md5] = {
        "order_id": order_id,
        "status": "EXPIRED",
        "game": "Roblox",
        "username": username,
        "item": item_name,
        "amount": amount,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "payment_method": "KHQR"
    }

# =============================
# MLBB TOPUP
# =============================
@app.route("/mobile-legends-products", methods=["GET", "POST"])
def mlbb_topup():
    try:
        res = requests.get("https://hong123.pythonanywhere.com/api/items?game=mlbb")
        items = res.json().get("items", [])
    except Exception as e:
        print("Error fetching items:", e)
        items = []

    if request.method == "POST":
        player_id = request.form["player_id"]
        server_id = request.form["server_id"]
        item_id = int(request.form["item_id"])

        # Verify country is Cambodia
        try:
            check_url = f"https://panha-mlbb-check-v2.vercel.app/api/ml/check?id={player_id}&serverid={server_id}"
            check_response = requests.get(check_url, timeout=10)
            check_data = check_response.json()
            
            if check_data.get("status") == "success":
                player_info = check_data.get("player", {})
                country = player_info.get("country", "")
                
                if country != "Cambodia":
                    return jsonify({
                        "success": False,
                        "error": f"Sorry, this service is only available for Cambodia accounts. Your account is from: {country}"
                    }), 403
            else:
                return jsonify({
                    "success": False,
                    "error": "Unable to verify account. Please try again."
                }), 400
                
        except Exception as e:
            print(f"Error checking country: {e}")
            return jsonify({
                "success": False,
                "error": "Country verification failed. Please try again."
            }), 500

        item = next(i for i in items if i["id"] == item_id)
        amount = item["price"]
        order_id = generate_short_transaction_id(10)

        bill = generate_short_transaction_id()
        qr_string = khqr.create_qr(
            bank_account=BANK_ACCOUNT,
            merchant_name="MLBB TOPUP",
            merchant_city="Phnom Penh",
            amount=amount,
            currency="USD",
            store_label="MLBB",
            phone_number=PHONE_NUMBER,
            bill_number=bill,
            terminal_label="MLBB-01",
            static=False
        )

        img = qrcode.make(qr_string)
        buf = BytesIO()
        img.save(buf, format="PNG")
        qr_base64 = base64.b64encode(buf.getvalue()).decode()
        md5 = khqr.generate_md5(qr_string)

        threading.Thread(
            target=check_payment_cart,
            args=(md5, player_id, server_id, item["name"], order_id, amount)
        ).start()

        return render_template("mlbb_qrcode.html",
                               qr_data=qr_base64,
                               amount=amount,
                               item=item,
                               player_id=player_id,
                               server_id=server_id,
                               md5=md5,
                               order_id=order_id,
                               timeout=180)

    return render_template("mlbb_topup.html", items=items)

@app.route("/roblox-products", methods=["GET", "POST"])
def roblox_topup():
    try:
        res = requests.get("https://hong123.pythonanywhere.com/api/items?game=roblox")
        items = res.json().get("items", [])
    except Exception as e:
        print("Error fetching items:", e)
        items = []

    if request.method == "POST":
        username_input = request.form["username_input"]
        password_input = request.form["password_input"]
        item_id = int(request.form["item_id"])

        item = next(i for i in items if i["id"] == item_id)
        amount = item["price"]
        order_id = generate_short_transaction_id(10)

        bill = generate_short_transaction_id()
        qr_string = khqr.create_qr(
            bank_account=BANK_ACCOUNT,
            merchant_name="ROBLOX TOPUP",
            merchant_city="Phnom Penh",
            amount=amount,
            currency="USD",
            store_label="ROBLOX",
            phone_number=PHONE_NUMBER,
            bill_number=bill,
            terminal_label="ROBLOX-01",
            static=False
        )

        img = qrcode.make(qr_string)
        buf = BytesIO()
        img.save(buf, format="PNG")
        qr_base64 = base64.b64encode(buf.getvalue()).decode()
        md5 = khqr.generate_md5(qr_string)

        threading.Thread(
            target=check_payment_cart_roblox,
            args=(md5, username_input, password_input, item["name"], order_id, amount)
        ).start()

        return render_template("roblox_qrcode.html",
                               qr_data=qr_base64,
                               amount=amount,
                               item=item,
                               username_input=username_input,
                               password_input=password_input,
                               md5=md5,
                               order_id=order_id,
                               timeout=180)

    return render_template("roblox_topup.html", items=items)

# =============================
# FREE FIRE TOPUP
# =============================
@app.route("/free-fire-products", methods=["GET", "POST"])
def ff_topup():
    try:
        res = requests.get("https://hong123.pythonanywhere.com/api/items?game=ff")
        items = res.json().get("items", [])
    except Exception as e:
        print("Error fetching items:", e)
        items = []

    if request.method == "POST":
        player_uid = request.form["player_uid"]
        item_id = int(request.form["item_id"])

        item = next(i for i in items if i["id"] == item_id)
        amount = item["price"]
        order_id = generate_short_transaction_id(10)

        bill = generate_short_transaction_id()
        qr_string = khqr.create_qr(
            bank_account=BANK_ACCOUNT,
            merchant_name="FF TOPUP",
            merchant_city="Phnom Penh",
            amount=amount,
            currency="USD",
            store_label="FREE FIRE",
            phone_number=PHONE_NUMBER,
            bill_number=bill,
            terminal_label="FF-01",
            static=False
        )

        img = qrcode.make(qr_string)
        buf = BytesIO()
        img.save(buf, format="PNG")
        qr_base64 = base64.b64encode(buf.getvalue()).decode()
        md5 = khqr.generate_md5(qr_string)

        threading.Thread(
            target=check_payment_cart_f,
            args=(md5, player_uid, item["name"], order_id, amount)
        ).start()

        return render_template("ff_qrcode.html",
                               qr_data=qr_base64,
                               amount=amount,
                               item=item,
                               player_uid=player_uid,
                               md5=md5,
                               order_id=order_id,
                               timeout=180)

    return render_template("freefire_topup.html", items=items)

# =============================
# RECEIPT PAGE
# =============================
@app.route("/receipt/<md5>")
def receipt(md5):
    transaction = transactions.get(md5)
    if not transaction:
        return "Transaction not found", 404
    
    return render_template("receipt.html", transaction=transaction, md5=md5)

# =============================
# VERIFICATION APIS
# =============================
@app.route("/api/verify_roblox_username", methods=["POST"])
def verify_roblox_username():
    try:
        data = request.get_json()
        username = data.get("username", "").strip()
        
        if not username:
            return jsonify({"error": "Username is required"}), 400
        
        api_url = f"https://panha-roblox-check-profile.vercel.app/api/roblox/avatar-headshot?username={username}"
        response = requests.get(api_url, timeout=10)
        roblox_data = response.json()
        
        if roblox_data.get("data") and len(roblox_data["data"]) > 0:
            avatar_data = roblox_data["data"][0]
            return jsonify({
                "success": True,
                "username": username,
                "imageUrl": avatar_data.get("imageUrl"),
                "state": avatar_data.get("state"),
                "targetId": avatar_data.get("targetId")
            })
        else:
            return jsonify({
                "success": False,
                "error": "Username not found"
            }), 404
            
    except Exception as e:
        print(f"Error verifying Roblox username: {e}")
        return jsonify({
            "success": False,
            "error": "API error. Please try again."
        }), 500

@app.route("/api/check_mlbb_nickname", methods=["POST"])
def check_mlbb_nickname():
    try:
        data = request.get_json()
        player_id = data.get("player_id", "").strip()
        server_id = data.get("server_id", "").strip()
        
        if not player_id or not server_id:
            return jsonify({
                "success": False,
                "error": "Player ID and Server ID are required"
            }), 400
        
        api_url = f"https://panha-mlbb-check-v2.vercel.app/api/ml/check?id={player_id}&serverid={server_id}"
        response = requests.get(api_url, timeout=10)
        api_data = response.json()
        
        if api_data.get("status") == "success":
            player_info = api_data.get("player", {})
            country = player_info.get("country", "")
            nickname = player_info.get("nickname", "")
            
            if country != "Cambodia":
                return jsonify({
                    "success": False,
                    "error": f"Only Cambodia accounts are supported. Your account is from: {country}",
                    "country": country
                }), 403
            
            return jsonify({
                "success": True,
                "nickname": nickname,
                "country": country,
                "player_id": player_id,
                "server_id": server_id
            })
        else:
            return jsonify({
                "success": False,
                "error": "Invalid Player ID or Server ID"
            }), 404
            
    except Exception as e:
        print(f"Error checking MLBB nickname: {e}")
        return jsonify({
            "success": False,
            "error": "API error. Please try again."
        }), 500

# =============================
# PAYMENT STATUS
# =============================
@app.route("/check_payment_status")
def check_payment_status():
    md5 = request.args.get("bill_number")
    return jsonify({"status": payment_status.get(md5, "PENDING")})

# =============================
# HOME
# =============================
@app.route("/")
def game():
    games = [
        {
            "name": "Mobile Legends",
            "slug": "mlbb",
            "url": url_for("mlbb_topup"),
            "image": "images/mlbb.jpg"
        },
        {
            "name": "Free Fire",
            "slug": "freefire",
            "url": url_for("ff_topup"),
            "image": "images/freefire.jpg"
        },
        {
            "name": "PUBG Mobile",
            "slug": "pubg",
            "url": "#",
            "image": "images/pubg.jpg"
        }
    ]
    return render_template("game.html", games=games)

# =============================
# RUN
# =============================
if __name__ == "__main__":
    app.run(debug=True)