import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import "./App.css";

// Where the Flask API is.
const API = "http://localhost:3001";

// The type of one snippet coming back from the API
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
  //  state
  const [snippets, setSnippets] = useState<Snippet[]>([]);
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<Mode>("fuzzy");
  const [ms, setMs] = useState<number | null>(null); // how long the last fetch took
  const [error, setError] = useState("");

  // add snippet form fields
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [source, setSource] = useState("");

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

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    try {
      const res = await fetch(`${API}/snippets`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, content, source: source || null }),
      });
      if (!res.ok) throw new Error("Server returned " + res.status);
      setTitle("");
      setContent("");
      setSource("");
      load(query, mode); // refresh the list
    } catch {
      setError("Couldn't save the snippet.");
    }
  }

  async function handleDelete(id: number) {
    try {
      await fetch(`${API}/snippets/${id}`, { method: "DELETE" });
      setSnippets(snippets.filter((s) => s.id !== id)); // remove it from the screen
    } catch {
      setError("Couldn't delete the snippet.");
    }
  }

   
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
              <button onClick={() => handleDelete(s.id)}>Delete</button>
            </div>
            <p>{s.content}</p>
            {s.source && <small>Source: {s.source}</small>}
            {s.score !== undefined && <small> · typos: {s.score}</small>}
          </li>
        ))}
      </ul>

      <h2>Add a snippet</h2>
      <form onSubmit={handleAdd} className="col">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Title"
          required
        />
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Content"
          required
        />
        <input
          value={source}
          onChange={(e) => setSource(e.target.value)}
          placeholder="Source (optional)"
        />
        <button type="submit">Add</button>
      </form>
    </main>
  );
}