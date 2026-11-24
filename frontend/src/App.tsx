import { useEffect, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";
import "./App.css";

// Where your Flask API lives (set VITE_API_URL when deployed)
const API = import.meta.env.VITE_API_URL ?? "http://localhost:3001";

// The shape of one snippet coming back from the API
type Snippet = {
  id: number;
  title: string;
  content: string;
  source: string | null;
  created_at: string;
  score?: number; // only present on fuzzy search results
};

type Mode = "exact" | "fuzzy";

export default function App() {
  // ---- state: data that, when it changes, redraws the screen ----
  const [snippets, setSnippets] = useState<Snippet[]>([]);
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<Mode>("fuzzy");
  const [ms, setMs] = useState<number | null>(null); // how long the last fetch took
  const [error, setError] = useState("");

  // form fields (used for both adding and editing)
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [source, setSource] = useState("");

  // null = the form is adding a new snippet; a number = editing that snippet's id
  const [editingId, setEditingId] = useState<number | null>(null);

  // lets us scroll the page down to the form when Edit is clicked
  const formRef = useRef<HTMLFormElement>(null);

  // Get snippets from the API: all of them if the search box is empty, otherwise search
  async function load(q: string, m: Mode) {
    setError("");
    try {
      const start = performance.now();
      const url = q.trim()
        ? `${API}/snippets/search?q=${encodeURIComponent(q)}&mode=${m}`
        : `${API}/snippets`;
      const res = await fetch(url);
      if (!res.ok) throw new Error("Server returned " + res.status);
      const data: Snippet[] = await res.json();
      setMs(Math.round(performance.now() - start));
      setSnippets(data);
    } catch {
      setError("Couldn't reach the API. Is Flask running on port 3001?");
    }
  }

  // Runs once when the page first loads: show everything
  useEffect(() => {
    load("", "fuzzy");
  }, []);

  function handleSearch(e: FormEvent) {
    e.preventDefault(); // stop the browser reloading the page
    load(query, mode);
  }

  // Empty the form and go back to "add" mode
  function resetForm() {
    setTitle("");
    setContent("");
    setSource("");
    setEditingId(null);
  }

  // One submit handler for the form: POST when adding, PUT when editing
  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const isEditing = editingId !== null;
    try {
      const res = await fetch(
        isEditing ? `${API}/snippets/${editingId}` : `${API}/snippets`,
        {
          method: isEditing ? "PUT" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title, content, source: source || null }),
        }
      );
      if (!res.ok) throw new Error("Server returned " + res.status);
      resetForm();
      load(query, mode); // refresh the list
    } catch {
      setError("Couldn't save the snippet.");
    }
  }

  // Edit clicked: copy the snippet into the form and scroll to it
  function startEdit(s: Snippet) {
    setEditingId(s.id);
    setTitle(s.title);
    setContent(s.content);
    setSource(s.source ?? ""); // null becomes an empty box
    formRef.current?.scrollIntoView({ behavior: "smooth" });
  }

  async function handleDelete(id: number) {
    try {
      await fetch(`${API}/snippets/${id}`, { method: "DELETE" });
      setSnippets(snippets.filter((s) => s.id !== id)); // remove it from the screen
      if (editingId === id) resetForm(); // don't keep editing something that's gone
    } catch {
      setError("Couldn't delete the snippet.");
    }
  }

  // Pressing Tab in the content box inserts spaces instead of jumping to the next field
  function handleTab(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key !== "Tab") return;
    e.preventDefault();
    const el = e.currentTarget;
    const start = el.selectionStart;
    const end = el.selectionEnd;
    setContent(content.slice(0, start) + "    " + content.slice(end));
    // after React redraws, put the cursor just after the inserted spaces
    requestAnimationFrame(() => {
      el.selectionStart = el.selectionEnd = start + 4;
    });
  }

  // ---- what gets drawn ----
  return (
    <main className="app">
      <h1>Snippet Vault</h1>

      <form onSubmit={handleSearch} className="row">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search snippets..."
        />
        <select value={mode} onChange={(e) => setMode(e.target.value as Mode)}>
          <option value="fuzzy">Fuzzy</option>
          <option value="exact">Exact</option>
        </select>
        <button type="submit">Search</button>
      </form>

      {error && <p className="error">{error}</p>}
      {ms !== null && (
        <p className="meta">
          {snippets.length} result(s) in {ms} ms
        </p>
      )}

      <ul className="list">
        {snippets.map((s) => (
          <li key={s.id} className="card">
            <div className="card-head">
              <h3>{s.title}</h3>
              <div className="actions">
                <button onClick={() => startEdit(s)}>Edit</button>
                <button onClick={() => handleDelete(s.id)}>Delete</button>
              </div>
            </div>
            <pre className="code">
              <code>{s.content}</code>
            </pre>
            {s.source && <small>Source: {s.source}</small>}
            {s.score !== undefined && <small> · typos: {s.score}</small>}
          </li>
        ))}
      </ul>

      <h2>{editingId === null ? "Add a snippet" : "Edit snippet"}</h2>
      <form onSubmit={handleSubmit} className="col" ref={formRef}>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Title"
          required
        />
        <textarea
          className="code"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onKeyDown={handleTab}
          placeholder="Content (paste code here)"
          required
        />
        <input
          value={source}
          onChange={(e) => setSource(e.target.value)}
          placeholder="Source (optional)"
        />
        <div className="actions">
          <button type="submit">{editingId === null ? "Add" : "Save"}</button>
          {editingId !== null && (
            <button type="button" onClick={resetForm}>
              Cancel
            </button>
          )}
        </div>
      </form>
    </main>
  );
}