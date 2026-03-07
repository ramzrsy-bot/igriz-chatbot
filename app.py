from flask import Flask, request, jsonify, session, redirect, send_from_directory
from flask_cors import CORS
import os 
import sqlite3
import google.genai as genai

app = Flask(__name__)
app.secret_key = "igriz_secret_key"
CORS(app)

# ---------------- DATABASE ----------------
conn = sqlite3.connect("igriz.db", check_same_thread=False)
cursor = conn.cursor()

# College info table
cursor.execute("""
CREATE TABLE IF NOT EXISTS college_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT UNIQUE,
    response TEXT
)
""")

conn.commit()

# ---------------- DEFAULT DATA ----------------
cursor.execute("SELECT COUNT(*) FROM college_info")
if cursor.fetchone()[0] == 0:
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

# ---------------- HOME & STATIC FILE SERVING ----------------
@app.route("/")
def serve_index():
    return send_from_directory('.', 'index.html')  # Serve chat UI as default page

@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory('.', filename)  # Serve JS, CSS, images, etc.

# ---------------- GEMINI API SETUP ----------------
client = genai.Client(api_key="AIzaSyDXnHw68dtptpPeyBzF3fGtXjmrrkuuFtc")

# ---------------- CHATBOT API ----------------
@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json["message"].lower()

    # ---------------- KEYWORD MATCHING ----------------
    cursor.execute("SELECT keyword, response FROM college_info")
    data = cursor.fetchall()

    replies = []
    words = user_message.replace("?", "").replace(",", "").split()

    for keyword, response in data:
        if keyword.lower() in words:
            replies.append(response)

    if replies:
        final_reply = "<br><br>".join(replies)
    else:
        # ---------------- MULTI-TURN MEMORY ----------------
        if 'chat_history' not in session:
            session['chat_history'] = []

        # Add current user message
        session['chat_history'].append({"role": "user", "parts": [{"text": user_message}]})

        # Limit to last 6 messages (3 full turns)
        if len(session['chat_history']) > 6:
            session['chat_history'] = session['chat_history'][-6:]

        try:
            # System prompt with Tamil support
            system_prompt = """You are IGRIZ, a professional and friendly college AI assistant for Hindusthan College of Arts & Science (HICAS) in Coimbatore. 
Give clear, short, helpful answers to students about admissions, fees, courses, campus facilities, events, etc. 
Be polite and use simple English. If the user question contains Tamil words or script (like டா, எவ்ளோ, கல்லூரி, ஃபீஸ் etc.), reply in friendly Tamlish or simple Tamil. 
Add a friendly touch like 'da' or 'டா' if it fits."""

            # Build full contents for Gemini (system + history)
            contents = [{"role": "model", "parts": [{"text": system_prompt}]}]
            contents.extend(session['chat_history'])

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents
            )
            final_reply = response.text.strip().replace("\n", "<br>")

            # Save bot reply to history
            session['chat_history'].append({"role": "model", "parts": [{"text": final_reply}]})

        except Exception as e:
            print("Gemini Error:", e)
            final_reply = "Oops! AI server is taking a break da. Try again or ask about fees/admission."

    # ---------------- CHAT HISTORY LOGGING ----------------
    # COMMENTED OUT FOR STABILITY (messages stay visible now)
    # To re-enable later, use per-request connection (safe version below)
    """
    try:
        temp_conn = sqlite3.connect("igriz.db")
        temp_cursor = temp_conn.cursor()
        temp_cursor.execute(
            "INSERT INTO chat_history (user_message, bot_reply) VALUES (?, ?)",
            (user_message, final_reply)
        )
        temp_conn.commit()
        temp_conn.close()
    except Exception as db_err:
        print("DB Log Error (ignored):", db_err)
    """

    return jsonify({"reply": final_reply})

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form["password"]
        if password == "15012006":
            session["admin"] = True
            return redirect("/admin")
        else:
            return "Wrong Password! <br><a href='/login'>Try Again</a>"
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

    cursor.execute("SELECT keyword FROM college_info")
    data = cursor.fetchall()

    keyword_list = ""
    for item in data:
        keyword_list += f"""
        <li>
            {item[0]}
            <form action="/delete" method="post" style="display:inline;">
                <input type="hidden" name="keyword" value="{item[0]}">
                <button type="submit">Delete</button>
            </form>
        </li>
        """

    return f"""
    <h2>IGRIZ Admin Panel</h2>
    <a href="/logout">Logout</a> | <a href="/admin/chat-history">View Chat History</a>
    <h3>Add / Update</h3>
    <form action="/save" method="post">
        Keyword:<br>
        <input type="text" name="keyword"><br><br>
        Response:<br>
        <textarea name="response" rows="5" cols="40"></textarea><br><br>
        <button type="submit">Save / Update</button>
    </form>
    <h3>Existing Keywords</h3>
    <ul>
        {keyword_list}
    </ul>
    """

# ---------------- CHAT HISTORY PAGE ----------------
@app.route("/admin/chat-history")
def chat_history():
    if "admin" not in session:
        return redirect("/login")

    cursor.execute("SELECT user_message, bot_reply, timestamp FROM chat_history ORDER BY timestamp DESC LIMIT 50")
    history = cursor.fetchall()

    rows = ""
    for row in history:
        rows += f"""
        <tr>
            <td>{row[2]}</td>
            <td>{row[0]}</td>
            <td>{row[1]}</td>
        </tr>
        """

    return f"""
    <h2>Chat History (Last 50 Messages)</h2>
    <a href="/admin">← Back to Admin Panel</a><br><br>
    <table border="1" style="width:100%; border-collapse:collapse; text-align:left;">
        <tr style="background:#0f2a5c; color:white;">
            <th>Time</th>
            <th>User Asked</th>
            <th>IGRIZ Replied</th>
        </tr>
        {rows}
    </table>
    """

# ---------------- SAVE DATA ----------------
@app.route("/save", methods=["POST"])
def save():
    keyword = request.form["keyword"]
    response = request.form["response"]

    cursor.execute("SELECT * FROM college_info WHERE keyword=?", (keyword,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("UPDATE college_info SET response=? WHERE keyword=?", (response, keyword))
        conn.commit()
        return "Data Updated Successfully! <br><a href='/admin'>Go Back</a>"
    else:
        cursor.execute("INSERT INTO college_info (keyword, response) VALUES (?, ?)", (keyword, response))
        conn.commit()
        return "Data Added Successfully! <br><a href='/admin'>Go Back</a>"

# ---------------- DELETE ----------------
@app.route("/delete", methods=["POST"])
def delete():
    keyword = request.form["keyword"]
    cursor.execute("DELETE FROM college_info WHERE keyword=?", (keyword,))
    conn.commit()
    return "Deleted Successfully! <br><a href='/admin'>Go Back</a>"

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/login")

# ---------------- RUN SERVER ----------------
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)