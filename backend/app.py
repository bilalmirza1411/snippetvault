from flask import Flask, jsonify, request
from flask_cors import CORS
from db import get_conn
from search.fuzzy_match import fuzzy_match

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