from flask import Flask, request, jsonify, session, redirect, send_from_directory
from flask_cors import CORS
import os
import sqlite3
from mistralai import Mistral

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "igriz_secret_key")
CORS(app)

DB_PATH = "igriz.db"

# ---------------- DATABASE CONNECTION ----------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS college_info (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT UNIQUE,
        response TEXT
    )
    """)

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM college_info")
    count = cursor.fetchone()[0]

    if count == 0:
        cursor.executemany(
            "INSERT INTO college_info (keyword, response) VALUES (?, ?)",
            [
                ("fees", """Fees can be paid in the college office.<br>
Office Timing: 8:30 AM – 1:30 PM (Monday to Friday)"""),
                ("admission", "Admission details are available in the admission office."),
                ("department", "We offer BSc, BCom, BBA, BA and many departments.")
            ]
        )
        conn.commit()

    conn.close()

init_db()

# ---------------- MISTRAL SETUP ----------------
client = Mistral(api_key=os.environ.get("6EahEodzPZXNdxmHoU20Vit9XA8LjSJN"))

# ---------------- HOME ----------------
@app.route("/")
def serve_index():
    return send_from_directory(".", "index.html")

@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory(".", filename)

# ---------------- CHAT API ----------------
@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json["message"].lower()

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT keyword, response FROM college_info")
    data = cursor.fetchall()

    replies = []
    words = user_message.replace("?", "").replace(",", "").split()

    for row in data:
        if row["keyword"].lower() in words:
            replies.append(row["response"])

    if replies:
        final_reply = "<br><br>".join(replies)

    else:

        if "chat_history" not in session:
            session["chat_history"] = []

        session["chat_history"].append({
            "role": "user",
            "content": user_message
        })

        if len(session["chat_history"]) > 6:
            session["chat_history"] = session["chat_history"][-6:]

        try:

            system_prompt = """
You are IGRIZ, a professional and friendly college AI assistant for
Hindusthan College of Arts & Science (HICAS) in Coimbatore.

Give clear, short answers to students about admissions, fees, courses,
campus facilities and events.

Use simple English.

If the user message contains Tamil words or script
(டா, எவ்ளோ, கல்லூரி, ஃபீஸ் etc), reply in friendly Tamil or Tamlish.
"""

            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(session["chat_history"])

            response = client.chat.complete(
                model="mistral-small-latest",
                messages=messages
            )

            final_reply = response.choices[0].message.content.replace("\n", "<br>")

            session["chat_history"].append({
                "role": "assistant",
                "content": final_reply
            })

        except Exception as e:
            print("Mistral error:", e)
            final_reply = "AI server busy da. Try again later."

    conn.close()

    return jsonify({"reply": final_reply})

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        password = request.form["password"]

        if password == "15012006":
            session["admin"] = True
            return redirect("/admin")

        return "Wrong Password <br><a href='/login'>Try again</a>"

    return """
    <h2>Admin Login</h2>
    <form method="post">
        Password:<br>
        <input type="password" name="password"><br><br>
        <button type="submit">Login</button>
    </form>
    """

# ---------------- ADMIN PANEL ----------------
@app.route("/admin")
def admin():

    if "admin" not in session:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT keyword FROM college_info")
    data = cursor.fetchall()

    keyword_list = ""

    for item in data:
        keyword_list += f"""
        <li>
            {item['keyword']}
            <form action="/delete" method="post" style="display:inline;">
                <input type="hidden" name="keyword" value="{item['keyword']}">
                <button type="submit">Delete</button>
            </form>
        </li>
        """

    conn.close()

    return f"""
    <h2>IGRIZ Admin Panel</h2>

    <a href="/logout">Logout</a>

    <h3>Add / Update</h3>

    <form action="/save" method="post">
        Keyword:<br>
        <input type="text" name="keyword"><br><br>

        Response:<br>
        <textarea name="response" rows="5" cols="40"></textarea><br><br>

        <button type="submit">Save</button>
    </form>

    <h3>Existing Keywords</h3>

    <ul>
        {keyword_list}
    </ul>
    """

# ---------------- SAVE ----------------
@app.route("/save", methods=["POST"])
def save():

    keyword = request.form["keyword"]
    response = request.form["response"]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM college_info WHERE keyword=?",
        (keyword,)
    )

    existing = cursor.fetchone()

    if existing:
        cursor.execute(
            "UPDATE college_info SET response=? WHERE keyword=?",
            (response, keyword)
        )
    else:
        cursor.execute(
            "INSERT INTO college_info (keyword,response) VALUES (?,?)",
            (keyword, response)
        )

    conn.commit()
    conn.close()

    return "Saved successfully <br><a href='/admin'>Back</a>"

# ---------------- DELETE ----------------
@app.route("/delete", methods=["POST"])
def delete():

    keyword = request.form["keyword"]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM college_info WHERE keyword=?",
        (keyword,)
    )

    conn.commit()
    conn.close()

    return "Deleted <br><a href='/admin'>Back</a>"

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():

    session.pop("admin", None)

    return redirect("/login")

app = app