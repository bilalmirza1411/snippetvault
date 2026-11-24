from flask import Flask, jsonify, request, g
from flask_cors import CORS
from db import get_conn
from search.fuzzy_match import fuzzy_match
from psycopg2 import errors
from werkzeug.security import check_password_hash, generate_password_hash
from auth import login_required, make_token
app = Flask(__name__)
CORS(app)

# Database query helper
def query_db(sql, params=(), fetch="all"):
    # fetch: "all", "one", or None (for statements that return nothing)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            if fetch == "all":
                return cur.fetchall()
            if fetch == "one":
                return cur.fetchone()
    # leaving the `with get_conn()` block commits automatically and rolls back on the case an exception is raised
@app.post("/register") # Route to register a new user
def register():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if len(username) < 3 or len(password) < 8:
        return jsonify(error="username needs 3+ characters and password 8+"), 400
    try:
        row = query_db(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id",
            (username, generate_password_hash(password)),  # store the hash, never the password
            fetch="one",
        )
    except errors.UniqueViolation:
        return jsonify(error="username already taken"), 409
    return jsonify(token=make_token(row["id"]), username=username), 201


@app.post("/login")
def login(): # Route to log in an existing user
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    row = query_db(
        "SELECT id, password_hash FROM users WHERE username = %s",
        (username,),
        fetch="one",
    )
    # same message whether the username or the password was wrong, so attackers learn nothing
    if not row or not check_password_hash(row["password_hash"], data.get("password") or ""):
        return jsonify(error="wrong username or password"), 401
    return jsonify(token=make_token(row["id"]), username=username)


@app.get("/me")
@login_required
def me(): # a quick way to test that a token works
    return jsonify(user_id=g.user_id)


# route to create a new snippet
@app.post("/snippets")
def create_snippet():
    data = request.get_json()
    if not data or not data.get("title") or not data.get("content"):
        return jsonify(error="title and content are required"), 400
    row = query_db(
        "INSERT INTO snippets (title, content, source) VALUES (%s, %s, %s) RETURNING *",
        (data["title"], data["content"], data.get("source")),
        fetch="one",
    )
    return jsonify(row), 201

# route to list all snippets
@app.get("/snippets")
def list_snippets():
    return jsonify(query_db("SELECT * FROM snippets ORDER BY created_at DESC"))
# route to search snippets
@app.get("/snippets/search")
def search_snippets():
    # Read the search settings from the URL
    q = request.args.get("q", "").strip()            # the search text
    mode = request.args.get("mode", "fuzzy")         # "exact" or "fuzzy"; defaults to fuzzy
    max_edits = int(request.args.get("max_edits", 1))  # how many typos are allowed, URL values are text, and int() converts it

    # Nothing typed in the search box so return an empty list straight away
    if not q:
        return jsonify([])

    #  EXACT MODE database does the searching 
    if mode == "exact":
        rows = query_db(
            "SELECT * FROM snippets WHERE title ILIKE %s OR content ILIKE %s",
            (f"%{q}%", f"%{q}%"),   
        )
        return jsonify(rows)

    #  FUZZY MODE: use our own matcher in Python 
    results = []                                      # snippets that match will be collected here

    # Load EVERY snippet from the database, then check each one ourselves
    for row in query_db("SELECT * FROM snippets"):

        # Run fuzzy_match on the title and on the content.
        # It returns a number (typos needed) or None (no match within max_edits)
        # The list keeps only the actual numbers, dropping the Nones.
        scores = [
            s
            for s in (
                fuzzy_match(q, row["title"], max_edits),
                fuzzy_match(q, row["content"], max_edits),
            )
            if s is not None
        ]

        # If the title OR the content matched, keep this snippet
        if scores:
            # {**row, "score": ...} copies all the row's fields and adds a "score" field.
            # min(scores) = the better of the two matches (lower = closer to exact).
            results.append({**row, "score": min(scores)})

    # Best matches first: score 0 (perfect) comes before score 1 (one typo)
    results.sort(key=lambda r: r["score"])

    # Send the list back to the caller as JSON
    return jsonify(results)
# route to get a single snippet by ID
@app.get("/snippets/<int:snippet_id>")
def get_snippet(snippet_id):
    row = query_db("SELECT * FROM snippets WHERE id = %s", (snippet_id,), fetch="one")
    return (jsonify(row), 200) if row else (jsonify(error="not found"), 404)

# route to update a snippet by ID
@app.put("/snippets/<int:snippet_id>")
def update_snippet(snippet_id):
    data = request.get_json()
    if not data or not data.get("title") or not data.get("content"):
        return jsonify(error="title and content are required"), 400
    row = query_db(
        "UPDATE snippets SET title = %s, content = %s, source = %s "
        "WHERE id = %s RETURNING *",
        (data["title"], data["content"], data.get("source"), snippet_id),
        fetch="one",
    )
    return (jsonify(row), 200) if row else (jsonify(error="not found"), 404)

# route to delete a snippet by ID
@app.delete("/snippets/<int:snippet_id>")
def delete_snippet(snippet_id):
    query_db("DELETE FROM snippets WHERE id = %s", (snippet_id,), fetch=None)
    return "", 204

if __name__ == "__main__":
    app.run(port=3001, debug=True)