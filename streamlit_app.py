import asyncio
import html
import json
import os
import time
from pathlib import Path

import inngest
import requests
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Ask your PDFs", page_icon="📄", layout="centered")

# ---------------------------------------------------------------------------
# Page styling: dark theme + animated aurora background
# ---------------------------------------------------------------------------
STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700&family=DM+Sans:wght@400;500;600&display=swap');

:root {
  --bg: #070912;
  --text: #e8ecf6;
  --muted: #8a94ab;
  --glass: rgba(255,255,255,.045);
  --edge: rgba(255,255,255,.11);
  --accent: #7c9cff;
  --teal: #5eead4;
}
html, body, .stApp, [class*="css"] { font-family: 'DM Sans', system-ui, sans-serif; color: var(--text); }
.stApp { background: var(--bg); color-scheme: dark; }
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
.block-container { position: relative; z-index: 1; max-width: 740px; padding-top: 3.5rem; padding-bottom: 5rem; }
p, label, .stMarkdown, [data-testid="stWidgetLabel"] p { color: var(--text); }

/* Animated background */
.element-container:has(.bg) { position: absolute; height: 0; margin: 0; }
.bg { position: fixed; inset: 0; z-index: 0; overflow: hidden; pointer-events: none; }
.orb { position: absolute; border-radius: 50%; filter: blur(90px); opacity: .55; will-change: transform; }
.o1 { width: 52vmax; height: 52vmax; left: -14vmax; top: -18vmax; background: #3b4cca; animation: drift1 24s ease-in-out infinite alternate; }
.o2 { width: 44vmax; height: 44vmax; right: -16vmax; top: 10vmax; background: #0e7c86; animation: drift2 28s ease-in-out infinite alternate; }
.o3 { width: 40vmax; height: 40vmax; left: 20vmax; bottom: -24vmax; background: #6a2c91; animation: drift3 32s ease-in-out infinite alternate; }
.grid {
  position: absolute; inset: 0;
  background-image: linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px);
  background-size: 52px 52px;
  -webkit-mask-image: radial-gradient(ellipse at 50% 30%, #000 20%, transparent 75%);
  mask-image: radial-gradient(ellipse at 50% 30%, #000 20%, transparent 75%);
  animation: gridmove 40s linear infinite;
}
@keyframes drift1 { to { transform: translate3d(22vmax, 14vmax, 0) scale(1.15); } }
@keyframes drift2 { to { transform: translate3d(-24vmax, 18vmax, 0) scale(.9); } }
@keyframes drift3 { to { transform: translate3d(14vmax, -20vmax, 0) scale(1.2); } }
@keyframes gridmove { to { background-position: 52px 52px, 52px 52px; } }

/* Hero */
.hero { margin-bottom: 2rem; animation: rise .8s cubic-bezier(.2,.7,.2,1) both; }
.hero h1 {
  font-family: 'Sora', sans-serif; font-weight: 700; font-size: clamp(2.2rem, 6vw, 3.3rem);
  letter-spacing: -0.03em; line-height: 1.05; margin: 0 0 .7rem 0; color: #fff;
}
.hero p { color: var(--muted); font-size: 1.05rem; margin: 0; max-width: 46ch; line-height: 1.55; }
.sec { font-family: 'Sora', sans-serif; font-size: 1.1rem; font-weight: 600; margin: 2.25rem 0 .8rem; color: #fff; animation: rise .7s cubic-bezier(.2,.7,.2,1) both; }
@keyframes rise { from { opacity: 0; transform: translateY(18px); } to { opacity: 1; transform: none; } }

/* Uploader */
[data-testid="stFileUploader"] section {
  background: var(--glass); border: 1.5px dashed rgba(124,156,255,.4); border-radius: 18px;
  padding: 2.2rem 1.25rem; backdrop-filter: blur(12px);
  animation: breathe 3.2s ease-in-out infinite; transition: border-color .25s ease, background .25s ease;
}
[data-testid="stFileUploader"] section:hover { border-color: var(--accent); background: rgba(124,156,255,.09); }
[data-testid="stFileUploader"] section *, [data-testid="stFileUploaderFile"] * { color: #c5cdee !important; }
[data-testid="stFileUploader"] button {
  background: transparent; border: 1px solid var(--edge); border-radius: 10px; color: var(--text) !important;
}
[data-testid="stFileUploader"] button:hover { border-color: var(--accent); }
@keyframes breathe { 0%,100% { box-shadow: 0 0 0 0 rgba(124,156,255,0); } 50% { box-shadow: 0 0 34px 0 rgba(124,156,255,.16); } }

/* Skip button */
.stButton > button {
  background: transparent; border: none; color: var(--muted); padding: .2rem 0; font-size: .92rem;
  text-decoration: underline; text-underline-offset: 3px;
}
.stButton > button:hover { color: var(--text); background: transparent; }

/* Form + inputs */
[data-testid="stForm"] {
  background: var(--glass); border: 1px solid var(--edge); border-radius: 18px; padding: 1.4rem;
  backdrop-filter: blur(14px); animation: rise .7s cubic-bezier(.2,.7,.2,1) both;
}
[data-baseweb="input"], [data-baseweb="base-input"] { background: transparent !important; }
[data-baseweb="input"] {
  background: rgba(255,255,255,.06) !important; border: 1px solid var(--edge); border-radius: 12px;
  transition: border-color .2s ease, box-shadow .2s ease;
}
[data-baseweb="input"]:focus-within { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(124,156,255,.25); }
[data-baseweb="input"] input { color: var(--text) !important; -webkit-text-fill-color: var(--text); }
[data-baseweb="input"] input::placeholder { color: #66708a; -webkit-text-fill-color: #66708a; }
.stNumberInput button { background: transparent !important; color: #c5cdee !important; }
[data-testid="stFormSubmitButton"] button {
  width: 100%; border: none; border-radius: 12px; padding: .65rem 1rem; font-weight: 600;
  background: linear-gradient(120deg, #7c9cff, #5eead4); color: #08101f !important;
  background-size: 160% 100%; transition: transform .15s ease, box-shadow .25s ease, background-position .4s ease;
}
[data-testid="stFormSubmitButton"] button:hover { background-position: 100% 0; box-shadow: 0 8px 30px rgba(124,156,255,.35); }
[data-testid="stFormSubmitButton"] button:active { transform: scale(.98); }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

/* Notes + loader */
.note {
  display: flex; align-items: center; gap: .6rem; margin-top: 1rem; padding: .75rem 1rem;
  background: rgba(94,234,212,.08); border: 1px solid rgba(94,234,212,.25); border-radius: 12px; font-size: .95rem;
}
.note .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--teal); box-shadow: 0 0 10px var(--teal); }
.loader { margin: 1rem 0; color: var(--muted); font-size: .95rem; }
.loader .bar { position: relative; height: 3px; margin-top: .6rem; background: rgba(255,255,255,.08); border-radius: 3px; overflow: hidden; }
.loader .bar::after {
  content: ""; position: absolute; inset: 0 auto 0 0; width: 35%; border-radius: 3px;
  background: linear-gradient(90deg, #7c9cff, #5eead4); animation: slide 1.1s ease-in-out infinite;
}
@keyframes slide { from { transform: translateX(-100%); } to { transform: translateX(300%); } }
iframe { border: none; color-scheme: normal; }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
}
</style>
<div class="bg"><div class="orb o1"></div><div class="orb o2"></div><div class="orb o3"></div><div class="grid"></div></div>
"""
st.markdown(STYLE, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Framer Motion component (React + framer-motion from a CDN, inside an iframe)
# kind="upload" -> animated check badge; kind="answer" -> staggered answer + sources
# ---------------------------------------------------------------------------
MOTION_PAGE = """
<!doctype html><html><head><meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;600&family=DM+Sans:wght@400;500&display=swap');
html, body { margin: 0; background: transparent; color: #e8ecf6; font-family: 'DM Sans', sans-serif; }
body { padding: 8px 4px 28px; }
.card {
  position: relative; background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.12);
  border-radius: 18px; padding: 24px 26px; box-shadow: 0 24px 70px rgba(0,0,0,.5); overflow: hidden;
}
.bar { position: absolute; left: 0; right: 0; top: 0; height: 3px; background: linear-gradient(90deg,#7c9cff,#5eead4); }
h3 { font-family: 'Sora', sans-serif; font-weight: 600; font-size: 1.2rem; margin: 6px 0 12px; color: #fff; }
.ans { line-height: 1.75; font-size: 1rem; white-space: pre-wrap; color: #dfe4f3; }
.st { margin: 22px 0 4px; color: #8a94ab; font-size: .9rem; }
ul { list-style: none; margin: 0; padding: 0; }
.src {
  margin-top: 8px; padding: 10px 14px; border-radius: 12px; font-size: .92rem; color: #c5cdee;
  background: rgba(124,156,255,.08); border: 1px solid rgba(124,156,255,.22); cursor: default;
}
.up { display: flex; align-items: center; gap: 20px; padding: 26px; }
.badge { position: relative; width: 56px; height: 56px; flex: none; }
.p { position: absolute; left: 50%; top: 50%; width: 6px; height: 6px; margin: -3px; border-radius: 50%; background: #7c9cff; }
.ring { position: absolute; inset: 0; border-radius: 50%; border: 2px solid #5eead4; }
.fn { font-family: 'Sora', sans-serif; font-weight: 600; color: #fff; word-break: break-all; }
.sub { color: #8a94ab; font-size: .92rem; margin-top: 4px; }
</style></head>
<body><div id="root">__FALLBACK__</div>
<script type="module">
import React from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";
import { motion, MotionConfig } from "https://esm.sh/framer-motion@11.11.17?deps=react@18.3.1,react-dom@18.3.1";
import htm from "https://esm.sh/htm@3.1.1";
const html = htm.bind(React.createElement);
const DATA = __PAYLOAD__;

function Answer({ answer, sources }) {
  const tokens = answer.split(/(\\s+)/);
  let w = 0;
  const wordsDone = 0.3 + Math.min(tokens.length / 2 * 0.02, 2.4) + 0.4;
  return html`
    <${motion.div} className="card" initial=${{ opacity: 0, y: 44, scale: .95 }} animate=${{ opacity: 1, y: 0, scale: 1 }}
      transition=${{ type: "spring", stiffness: 140, damping: 18 }}>
      <${motion.div} className="bar" style=${{ transformOrigin: "left" }} initial=${{ scaleX: 0 }} animate=${{ scaleX: 1 }}
        transition=${{ duration: .9, ease: "easeOut" }} />
      <h3>Answer</h3>
      <div className="ans">${tokens.map((t, i) => /^\\s+$/.test(t) ? t : html`
        <${motion.span} key=${i} style=${{ display: "inline-block" }}
          initial=${{ opacity: 0, y: 10, filter: "blur(6px)" }} animate=${{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition=${{ delay: .3 + Math.min(w++ * 0.02, 2.4), duration: .4 }}>${t}<//>`)}</div>
      ${sources.length ? html`
        <${motion.div} className="st" initial=${{ opacity: 0 }} animate=${{ opacity: 1 }} transition=${{ delay: wordsDone }}>Drawn from<//>
        <${motion.ul} initial="hidden" animate="show"
          variants=${{ show: { transition: { delayChildren: wordsDone, staggerChildren: .13 } } }}>
          ${sources.map((s, i) => html`
            <${motion.li} key=${i} className="src"
              variants=${{ hidden: { opacity: 0, x: -28 }, show: { opacity: 1, x: 0, transition: { type: "spring", stiffness: 160, damping: 16 } } }}
              whileHover=${{ x: 6, backgroundColor: "rgba(124,156,255,.18)" }}>${s}<//>`)}
        <//>` : null}
    <//>`;
}

function Uploaded({ name }) {
  const N = 14;
  return html`
    <${motion.div} className="card up" initial=${{ opacity: 0, scale: .88 }} animate=${{ opacity: 1, scale: 1 }}
      transition=${{ type: "spring", stiffness: 200, damping: 15 }}>
      <div className="badge">
        ${Array.from({ length: N }, (_, i) => { const a = i / N * Math.PI * 2; return html`
          <${motion.span} key=${i} className="p" initial=${{ x: 0, y: 0, opacity: 1, scale: 1 }}
            animate=${{ x: Math.cos(a) * 46, y: Math.sin(a) * 46, opacity: 0, scale: .2 }}
            transition=${{ duration: .9, delay: .5, ease: "easeOut" }} />`; })}
        <${motion.div} className="ring" initial=${{ scale: .6, opacity: .9 }} animate=${{ scale: 1.9, opacity: 0 }}
          transition=${{ duration: 1, delay: .45 }} />
        <svg width="56" height="56" viewBox="0 0 56 56">
          <${motion.circle} cx="28" cy="28" r="25" fill="none" stroke="#5eead4" strokeWidth="2.5"
            initial=${{ pathLength: 0 }} animate=${{ pathLength: 1 }} transition=${{ duration: .6 }} />
          <${motion.path} d="M16 29 l8 8 l16 -17" fill="none" stroke="#5eead4" strokeWidth="3.5"
            strokeLinecap="round" strokeLinejoin="round"
            initial=${{ pathLength: 0 }} animate=${{ pathLength: 1 }} transition=${{ duration: .45, delay: .45 }} />
        </svg>
      </div>
      <div>
        <${motion.div} className="fn" initial=${{ opacity: 0, x: 16 }} animate=${{ opacity: 1, x: 0 }} transition=${{ delay: .3 }}>${name}<//>
        <${motion.div} className="sub" initial=${{ opacity: 0, x: 16 }} animate=${{ opacity: 1, x: 0 }} transition=${{ delay: .45 }}>
          Ingestion started. You can ask questions below.<//>
      </div>
    <//>`;
}

createRoot(document.getElementById("root")).render(html`
  <${MotionConfig} reducedMotion="user">
    ${DATA.kind === "upload"
      ? html`<${Uploaded} name=${DATA.name} />`
      : html`<${Answer} answer=${DATA.answer} sources=${DATA.sources} />`}
  <//>`);

// Fit the iframe to its content
const fit = () => { try { window.frameElement.style.height = document.documentElement.scrollHeight + "px"; } catch (e) {} };
new ResizeObserver(fit).observe(document.body);
setTimeout(fit, 100); setTimeout(fit, 1500);
</script></body></html>
"""


def motion_embed(payload: dict, fallback_html: str, height: int) -> None:
    data = json.dumps(payload).replace("</", "<\\/")
    page = MOTION_PAGE.replace("__FALLBACK__", fallback_html).replace("__PAYLOAD__", data)
    components.html(page, height=height, scrolling=False)


# ---------------------------------------------------------------------------
# Inngest + helpers (logic unchanged)
# ---------------------------------------------------------------------------
@st.cache_resource
def get_inngest_client() -> inngest.Inngest:
    return inngest.Inngest(app_id="rag_app", is_production=False)


def save_uploaded_pdf(file) -> Path:
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    file_path = uploads_dir / file.name
    file_path.write_bytes(file.getbuffer())
    return file_path


async def send_rag_ingest_event(pdf_path: Path) -> None:
    client = get_inngest_client()
    await client.send(
        inngest.Event(
            name="rag/ingest_pdf",
            data={"pdf_path": str(pdf_path.resolve()), "source_id": pdf_path.name},
        )
    )


async def send_rag_query_event(question: str, top_k: int) -> str:
    client = get_inngest_client()
    result = await client.send(
        inngest.Event(name="rag/query_pdf_ai", data={"question": question, "top_k": top_k})
    )
    return result[0]


def _inngest_api_base() -> str:
    return os.getenv("INNGEST_API_BASE", "http://127.0.0.1:8288/v1")


def fetch_runs(event_id: str) -> list[dict]:
    resp = requests.get(f"{_inngest_api_base()}/events/{event_id}/runs")
    resp.raise_for_status()
    return resp.json().get("data", [])


def wait_for_run_output(event_id: str, timeout_s: float = 120.0, poll_interval_s: float = 0.5) -> dict:
    start = time.time()
    last_status = None
    while True:
        runs = fetch_runs(event_id)
        if runs:
            run = runs[0]
            status = run.get("status")
            last_status = status or last_status
            if status in ("Completed", "Succeeded", "Success", "Finished"):
                return run.get("output") or {}
            if status in ("Failed", "Cancelled"):
                raise RuntimeError(f"Function run {status}")
        if time.time() - start > timeout_s:
            raise TimeoutError(f"Timed out waiting for run output (last status: {last_status})")
        time.sleep(poll_interval_s)


def loader_html(label: str) -> str:
    return f'<div class="loader">{html.escape(label)}<div class="bar"></div></div>'


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero">
      <h1>Ask your PDFs</h1>
      <p>Add a document, then ask anything about it. Answers come with the passages they were drawn from.</p>
    </div>
    <div class="sec" style="margin-top:0">Add a PDF</div>
    """,
    unsafe_allow_html=True,
)

uploaded = st.file_uploader("Choose a PDF", type=["pdf"], accept_multiple_files=False, label_visibility="collapsed")
just_ingested = False

if uploaded is not None:
    file_key = f"{uploaded.name}:{uploaded.size}"
    # Streamlit reruns on every interaction, so only ingest each file once.
    if st.session_state.get("ingested_key") != file_key:
        loader = st.empty()
        loader.markdown(loader_html("Uploading and starting ingestion"), unsafe_allow_html=True)
        try:
            path = save_uploaded_pdf(uploaded)
            asyncio.run(send_rag_ingest_event(path))
            st.session_state["ingested_key"] = file_key
            st.session_state["ingested_name"] = path.name
            just_ingested = True
        except Exception as exc:
            st.error(f"Couldn't start ingestion: {exc}")
        loader.empty()

    if just_ingested:
        name = st.session_state["ingested_name"]
        motion_embed(
            {"kind": "upload", "name": name},
            f'<div class="card up"><div class="fn">{html.escape(name)}</div></div>',
            height=150,
        )
    elif st.session_state.get("ingested_key") == file_key:
        st.markdown(
            f'<div class="note"><span class="dot"></span>'
            f'{html.escape(st.session_state["ingested_name"])} is added. Upload another PDF any time.</div>',
            unsafe_allow_html=True,
        )

ready = st.session_state.get("ingested_key") is not None or st.session_state.get("skip_upload")

if not ready:
    if st.button("My PDFs are already ingested", key="skip_btn"):
        st.session_state["skip_upload"] = True
        st.rerun()
else:
    st.markdown('<div class="sec">Ask a question</div>', unsafe_allow_html=True)
    with st.form("rag_query_form"):
        col_q, col_k = st.columns([4, 1])
        with col_q:
            question = st.text_input("Your question", placeholder="What does the document say about…")
        with col_k:
            top_k = st.number_input("Chunks", min_value=1, max_value=20, value=5, step=1)
        submitted = st.form_submit_button("Get answer")

    if submitted and question.strip():
        loader = st.empty()
        loader.markdown(loader_html("Searching your PDFs and writing an answer"), unsafe_allow_html=True)
        try:
            event_id = asyncio.run(send_rag_query_event(question.strip(), int(top_k)))
            output = wait_for_run_output(event_id)
        except (TimeoutError, RuntimeError, requests.RequestException) as exc:
            loader.empty()
            st.error(f"Couldn't get an answer: {exc}")
        else:
            loader.empty()
            answer = output.get("answer", "") or "No answer came back for that question."
            sources = [str(s) for s in output.get("sources", [])]
            est_lines = len(answer) // 80 + answer.count("\n") + 1
            motion_embed(
                {"kind": "answer", "answer": answer, "sources": sources},
                f'<div class="card"><h3>Answer</h3><div class="ans">{html.escape(answer)}</div></div>',
                height=min(160 + est_lines * 28 + len(sources) * 58 + (50 if sources else 0), 3000),
            )