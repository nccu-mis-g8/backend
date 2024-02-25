from flask import *
import psycopg2

# 建立Application物件，靜態檔案處理設定
app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/"
)

# 設定Session金鑰
app.secret_key="nccumisg8"

# 首頁(註冊、登入)
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

# 登入成功頁面
@app.route("/member", methods=["GET"])
def member():
    if "account" in session:
        return render_template("member.html")
    else:
        return redirect("/")

# 錯誤頁面
# /error?msg=錯誤訊息
@app.route("/error", methods=["GET"])
def error():
    msg = request.args.get("msg", "error occurred")
    return render_template("error.html", msg=msg)

# 註冊
@app.route("/signup", methods=["POST"])
def signup():
    account = request.form["account"]
    password = request.form["password"]
    # 資料庫處理
    conn = psycopg2.connect(host="localhost", dbname="flask", user="postgres", 
                        password="root123", port="5432")
    cur = conn.cursor()
    # 確認此帳號有無被註冊過
    sql = "SELECT * FROM users WHERE account='{}'".format(account) 
    cur.execute(sql)
    result = cur.fetchall()
    if len(result) != 0:
        return redirect("/error?msg=此帳號已被使用")
    # 若沒有則將資料加入資料庫 (完成註冊)
    sql = "INSERT INTO users(account, password) VALUES('{}', '{}')".format(account, password)
    cur.execute(sql)
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/") # 重新導向回首頁

# 登入
@app.route("/signin", methods=["POST"])
def signin():
    account = request.form["account"]
    password = request.form["password"]
    # 資料庫處理
    conn = psycopg2.connect(host="localhost", dbname="flask", user="postgres", 
                        password="root123", port="5432")
    cur = conn.cursor()
    # 確認是否登入成功
    sql = "SELECT * FROM users WHERE account='{}' AND password='{}'".format(account, password)
    cur.execute(sql)
    result = cur.fetchall()
    if result == 0:
        return redirect("/error?msg=帳號或密碼錯誤")
    # 登入成功
    # 在Session紀錄會員資訊，並導向到登入成功頁面
    sql = "SELECT account FROM users WHERE account='{}' AND password='{}'".format(account, password)
    cur.execute(sql)
    result = cur.fetchall()
    session["account"] = result[0]
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/member")

# 登出
@app.route("/signout", methods=["GET"])
def signout():
    # 移除Session中的會員資訊，並導回首頁
    del session["account"]
    return redirect("/")

app.run()