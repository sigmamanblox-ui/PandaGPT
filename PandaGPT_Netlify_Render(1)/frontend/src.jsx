import React, {useEffect, useState} from "react";
import {createRoot} from "react-dom/client";
import "./style.css";

const API = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

function newSession() {
  const id = crypto.randomUUID();
  localStorage.setItem("pandgpt_session", id);
  return id;
}

function App() {
  const [session, setSession] = useState(localStorage.getItem("pandgpt_session") || newSession());
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [web, setWeb] = useState(false);
  const [name, setName] = useState("PandaGPT");
  const [sidebar, setSidebar] = useState(true);

  useEffect(() => {
    fetch(`${API}/settings`).then(r=>r.json()).then(x=>setName(x.name || "PandaGPT"));
    loadHistory(session);
  }, [session]);

  async function loadHistory(id) {
    const r = await fetch(`${API}/history/${id}`);
    const x = await r.json();
    setMessages(x.messages || []);
  }

  function newChat() {
    const id = newSession();
    setSession(id);
    setMessages([]);
  }

  async function send() {
    const q = text.trim();
    if (!q || busy) return;
    setText("");
    setMessages(m => [...m, {role:"user", content:q}]);
    setBusy(true);
    try {
      const r = await fetch(`${API}/chat`, {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({session_id:session, message:q, use_web:web})
      });
      const x = await r.json();
      setMessages(m => [...m, {role:"assistant", content:x.answer || x.detail || "Something went wrong."}]);
    } catch {
      setMessages(m => [...m, {role:"assistant", content:"I couldn't connect to PandaGPT. Make sure the backend is running."}]);
    } finally {
      setBusy(false);
    }
  }

  return <div className="shell">
    {sidebar && <aside className="sidebar">
      <button className="new-chat" onClick={newChat}>＋ New chat</button>
      <div className="side-section">PandaGPT</div>
      <div className="side-item active">▣ Current conversation</div>
      <div className="side-bottom">
        <div>⚙ Settings</div>
        <div className="version">PandaGPT</div>
      </div>
    </aside>}

    <section className="main">
      <header className="topbar">
        <button className="icon" onClick={()=>setSidebar(!sidebar)}>☰</button>
        <div className="brand"><span className="panda">🐼</span><b>{name}</b><span className="model">AI</span></div>
        <label className="web-toggle"><input type="checkbox" checked={web} onChange={e=>setWeb(e.target.checked)}/> Web</label>
      </header>

      <main className="chat">
        {messages.length === 0 ? <div className="welcome">
          <div className="big-panda">🐼</div>
          <h1>How can I help you today?</h1>
          <p>Ask PandaGPT anything.</p>
          <div className="cards">
            <button onClick={()=>setText("Explain quantum computing simply")}>Explain something</button>
            <button onClick={()=>setText("Write a Python program for me")}>Help me code</button>
            <button onClick={()=>setText("Give me creative ideas for a project")}>Brainstorm ideas</button>
            <button onClick={()=>setText("Help me plan my week")}>Plan something</button>
          </div>
        </div> : messages.map((m,i)=>
          <div key={i} className={"row "+m.role}>
            <div className="avatar">{m.role==="assistant" ? "🐼" : "U"}</div>
            <div className="content"><div className="role">{m.role==="assistant" ? "PandaGPT" : "You"}</div><div className="bubble">{m.content}</div></div>
          </div>
        )}
        {busy && <div className="row assistant"><div className="avatar">🐼</div><div className="content"><div className="role">PandaGPT</div><div className="typing"><i></i><i></i><i></i></div></div></div>}
      </main>

      <footer>
        <div className="composer">
          <button className="plus">＋</button>
          <textarea value={text} onChange={e=>setText(e.target.value)}
            onKeyDown={e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();send()}}}
            placeholder="Message PandaGPT…" />
          <button className="send" onClick={send} disabled={busy || !text.trim()}>↑</button>
        </div>
        <div className="hint">PandaGPT can make mistakes. Check important information.</div>
      </footer>
    </section>
  </div>
}
createRoot(document.getElementById("root")).render(<App/>);
