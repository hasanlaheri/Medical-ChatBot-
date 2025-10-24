from flask import Flask, render_template, jsonify, request, session, make_response
from db_utils import *
from rag_utils import agent_with_history
import uuid

app = Flask(__name__)
app.secret_key = "my_secret_key"
init_db()

@app.route("/")
def index():
    return render_template("chat.html")

# --- Chat management routes ---
@app.route("/new_chat", methods=["POST"])
def new_chat():
    session_id = str(uuid.uuid4())
    save_session(session_id)
    resp = make_response(jsonify({"session_id": session_id}))
    resp.set_cookie("session_id", session_id)
    return resp

@app.route("/sessions", methods=["GET"])
def list_sessions_route():
    return jsonify({"sessions": get_sessions()})

@app.route("/delete_chat/<session_id>", methods=["DELETE"])
def delete_chat_route(session_id):
    delete_session(session_id)
    resp = jsonify({"status": "ok"})
    if request.cookies.get("session_id") == session_id:
        resp.set_cookie("session_id", "", expires=0)
    return resp

@app.route("/history/<session_id>", methods=["GET"])
def history_route(session_id):
    return jsonify(get_messages(session_id))

@app.route("/rename_chat/<session_id>", methods=["POST"])
def rename_chat_route(session_id):
    new_name = request.form.get("name", "").strip()
    if session_id and new_name:
        save_session(session_id, name=new_name)
        return jsonify({"status": "ok", "name": new_name})
    return jsonify({"status": "error", "message": "Invalid session or name"}), 400

@app.route("/get", methods=["POST"])
def chat_route():
    session_id = request.cookies.get("session_id") or str(uuid.uuid4())
    user_input = request.form.get("msg", "").strip()
    if not user_input:
        return ""

    # Only update last_active, do NOT overwrite the name
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE sessions SET last_active = ? WHERE session_id = ?", (datetime.utcnow(), session_id))
    conn.commit()
    conn.close()

    save_message(session_id, "human", user_input)

    try:
        response = agent_with_history.invoke(
            {"input": user_input},
            config={"configurable": {"session_id": session_id}},
            handle_parsing_errors=True
        )
        answer = response.get("answer") or response.get("output") or str(response)
        if not answer.strip():
            answer = "I’m here to help with medical questions. Could you please ask a medical-related question?"
    except Exception as e:
        print("Error in /get:", e)
        answer = "I’m here to help with medical questions. Could you please ask a medical-related question?"

    save_message(session_id, "ai", answer)
    return str(answer)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
