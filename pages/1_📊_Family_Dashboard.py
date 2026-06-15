"""
pages/1_📊_Family_Dashboard.py — Caregiver analytics and KB management.

Accessible from the Streamlit sidebar automatically (multi-page app).
Uses the same PIN as the main app.

Features:
  - KPI metrics (total turns, avg latency, top input type, most active day)
  - Usage charts (daily trend, input type breakdown, model usage, latency histogram)
  - AI-powered health observation extractor (Gemini scans conversations for caregivers)
  - Knowledge base file manager (upload, preview, delete, rebuild index)
  - Conversation search + CSV export
"""
from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import config
from utils.auth import check_auth
from utils.logger import log
from utils.state import init_state

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="ElderAI — Family Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Secrets / auth ────────────────────────────────────────────────────────────

init_state()

# Mirror the same st.secrets override from app.py
try:
    if "GEMINI_API_KEY" in st.secrets:
        config.GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    if "AUTH_PIN_HASH" in st.secrets:
        config.PIN_HASH = st.secrets["AUTH_PIN_HASH"]
except Exception:
    pass

if not check_auth():
    st.stop()

# ── Data loader ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)   # refresh every 30 s without manual reload
def _load_df() -> pd.DataFrame:
    from utils.history import init_db
    init_db()
    try:
        conn = sqlite3.connect(config.HISTORY_DB)
        df = pd.read_sql_query(
            """
            SELECT ts, query, answer, model_used, input_type,
                   retrieval_score, latency_ms
            FROM   chat_history
            ORDER  BY ts ASC
            """,
            conn,
        )
        conn.close()
    except Exception:
        return pd.DataFrame()

    if df.empty:
        return df

    df["ts"]   = pd.to_datetime(df["ts"])
    df["date"] = df["ts"].dt.date
    df["hour"] = df["ts"].dt.hour
    return df


df = _load_df()

# ── Header ────────────────────────────────────────────────────────────────────

st.title("📊 Family Dashboard")
st.caption(
    "Usage analytics · AI health observations · Knowledge base management  "
    "— for caregivers only"
)
st.divider()

# ── KPI row ───────────────────────────────────────────────────────────────────

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric("💬 Total Conversations", len(df))

with kpi2:
    avg_lat = df["latency_ms"].dropna().mean() if not df.empty else None
    st.metric("⚡ Avg Response", f"{avg_lat:.0f} ms" if avg_lat else "—")

with kpi3:
    if not df.empty and not df["input_type"].empty:
        top_type = df["input_type"].mode().iloc[0]
        type_icon = {"text": "⌨️", "voice": "🎤", "image": "📷"}.get(top_type, "")
        st.metric("🏆 Most Used Mode", f"{type_icon} {top_type.title()}")
    else:
        st.metric("🏆 Most Used Mode", "—")

with kpi4:
    if not df.empty:
        busiest = df["date"].value_counts().idxmax()
        count   = df["date"].value_counts().max()
        st.metric("📅 Busiest Day", str(busiest), delta=f"{count} turns")
    else:
        st.metric("📅 Busiest Day", "—")

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────

if not df.empty:
    # Row 1: daily trend + type donut + model bar
    c1, c2, c3 = st.columns([3, 2, 2])

    with c1:
        st.subheader("📈 Conversations per Day")
        daily = df.groupby("date").size().reset_index(name="turns")
        fig = px.bar(
            daily, x="date", y="turns",
            labels={"date": "", "turns": "Conversations"},
            color_discrete_sequence=["#1a73e8"],
        )
        fig.update_layout(margin=dict(t=5, b=0), height=240,
                          plot_bgcolor="rgba(0,0,0,0)",
                          paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("🎯 Input Types")
        tc = df["input_type"].value_counts().reset_index()
        tc.columns = ["type", "count"]
        fig2 = px.pie(
            tc, values="count", names="type",
            color_discrete_map={"text": "#1a73e8", "voice": "#0f9d58", "image": "#f4511e"},
            hole=0.50,
        )
        fig2.update_layout(margin=dict(t=5, b=0), height=240,
                           legend=dict(orientation="h", y=-0.1),
                           paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)

    with c3:
        st.subheader("🤖 Model Usage")
        mc = df["model_used"].value_counts().reset_index()
        mc.columns = ["model", "count"]
        fig3 = px.bar(
            mc, x="count", y="model", orientation="h",
            color="model",
            color_discrete_map={
                "lite": "#fbbc04", "flash": "#0f9d58",
                "pro": "#ea4335", "flash-vision": "#9c27b0",
            },
            labels={"count": "Turns", "model": ""},
        )
        fig3.update_layout(margin=dict(t=5, b=0), height=240,
                           showlegend=False,
                           paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig3, use_container_width=True)

    # Row 2: latency histogram + hourly heatmap
    c4, c5 = st.columns(2)

    with c4:
        lat_data = df.dropna(subset=["latency_ms"])
        if len(lat_data) > 2:
            st.subheader("⚡ Latency Distribution")
            fig4 = px.histogram(
                lat_data, x="latency_ms", nbins=25,
                labels={"latency_ms": "Response time (ms)", "count": "Turns"},
                color_discrete_sequence=["#9c27b0"],
            )
            fig4.update_layout(margin=dict(t=5, b=0), height=220,
                               paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig4, use_container_width=True)

    with c5:
        st.subheader("🕐 Active Hours")
        hourly = df.groupby("hour").size().reset_index(name="turns")
        fig5 = px.bar(
            hourly, x="hour", y="turns",
            labels={"hour": "Hour of day", "turns": "Conversations"},
            color_discrete_sequence=["#1a73e8"],
        )
        fig5.update_layout(margin=dict(t=5, b=0), height=220,
                           xaxis=dict(tickmode="linear", dtick=2),
                           paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig5, use_container_width=True)

    # CSV export
    csv = df.drop(columns=["date", "hour"]).to_csv(index=False)
    st.download_button(
        "⬇️  Download Full History as CSV",
        data=csv,
        file_name=f"elderai_history_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

else:
    st.info("📭 No conversation history yet. Ask ElderAI something in the main app — then come back here.")

st.divider()

# ── Health Observations ───────────────────────────────────────────────────────

st.subheader("🏥 AI Health Observations")
st.caption(
    "ElderAI scans recent conversations and extracts health-relevant mentions "
    "so caregivers can follow up. Findings are **not medical advice**."
)

_EXTRACT_PROMPT = """\
You are a health assistant helping a family caregiver review conversations
between an elderly person and an AI assistant.

Carefully review the conversations below and extract every health-relevant observation.
Categories to look for: medications, symptoms, pain, appointments, diet, mobility,
mood changes, confusion, emergencies, device struggles.

Return ONLY this JSON (no markdown, no preamble):
{
  "observations": [
    {"category": "...", "detail": "...", "urgency": "low|medium|high", "when": "..."}
  ],
  "summary": "One sentence overall health summary for the caregiver."
}

If there is nothing health-relevant, return {"observations": [], "summary": "No health mentions found."}

Conversations:
"""

api_ready = config.GEMINI_API_KEY not in ("INSERT_YOUR_KEY_HERE", "", None)

if not df.empty and api_ready:
    recent = df.tail(30)[["ts", "query", "answer"]].copy()
    recent["ts"] = recent["ts"].dt.strftime("%Y-%m-%d %H:%M")

    if st.button("🔍  Analyse Last 30 Conversations", type="secondary"):
        conv_text = "\n\n".join(
            f"[{r.ts}]\nUser: {r.query}\nAssistant: {r.answer}"
            for r in recent.itertuples()
        )
        with st.spinner("Scanning conversations for health observations…"):
            try:
                from google import genai
                client = genai.Client(api_key=config.GEMINI_API_KEY)
                response = client.models.generate_content(
                    model=config.GEMINI_MODELS["flash"],
                    contents=[_EXTRACT_PROMPT + conv_text],
                )
                raw = (response.text or "").strip()
                # Strip markdown fences if model adds them
                raw = raw.lstrip("```json").lstrip("```").rstrip("```").strip()
                data = json.loads(raw)

                st.success(f"📋 {data.get('summary', 'Analysis complete.')}")

                obs = data.get("observations", [])
                if obs:
                    urgency_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
                    obs_df = pd.DataFrame(obs)
                    obs_df["urgency"] = obs_df["urgency"].apply(
                        lambda u: f"{urgency_icon.get(u, '⚪')} {u.title()}"
                    )
                    obs_df.columns = [c.title() for c in obs_df.columns]
                    st.dataframe(obs_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No specific health observations detected.")

                log.info("health_obs_extracted", count=len(obs))

            except json.JSONDecodeError:
                # Model didn't return JSON — show it as plain text
                st.info(f"Summary: {raw[:800]}")
            except Exception as exc:
                log.error("health_obs_failed", exc=str(exc))
                st.error("Could not extract observations. Please try again.")

elif df.empty:
    st.info("Start a conversation in the main app to enable health analysis.")
else:
    st.warning("Set `GEMINI_API_KEY` to enable AI health observation extraction.")

st.divider()

# ── Knowledge Base Manager ────────────────────────────────────────────────────

st.subheader("📚 Knowledge Base Manager")
st.caption(f"Files in `{config.KB_PATH}` — the assistant's personal memory.")

kb_path = Path(config.KB_PATH)
kb_path.mkdir(parents=True, exist_ok=True)
kb_files = sorted(kb_path.glob("**/*.txt"))

faiss_path   = Path(config.FAISS_PATH)
faiss_exists = faiss_path.exists()

# Index status
idx_col, rebuild_col = st.columns([3, 1])
with idx_col:
    if faiss_exists:
        idx_size = sum(f.stat().st_size for f in faiss_path.iterdir()) / 1024
        st.success(
            f"✅ FAISS index ready — {len(kb_files)} file(s), "
            f"{idx_size:.0f} KB index"
        )
    else:
        st.warning("⚠️ FAISS index not found — rebuilds automatically on next main app start.")

with rebuild_col:
    if st.button("🔄  Force Rebuild", type="secondary", disabled=not faiss_exists,
                 help="Clears the index so it rebuilds on next startup"):
        shutil.rmtree(str(faiss_path), ignore_errors=True)
        st.success("Index cleared. Restart the main app to rebuild.")
        st.rerun()

st.markdown(" ")

# File list + inline preview
upload_col, list_col = st.columns([1, 2])

with upload_col:
    st.markdown("**Upload a new file:**")
    uploaded = st.file_uploader(
        "Choose a .txt file",
        type=["txt"],
        label_visibility="collapsed",
        key="kb_upload",
    )
    if uploaded:
        dest = kb_path / uploaded.name
        dest.write_bytes(uploaded.read())
        log.info("kb_file_uploaded", name=uploaded.name)
        st.success(f"✅ `{uploaded.name}` added.")
        st.warning("Restart the main app or press **Force Rebuild** then restart to reindex.")
        st.rerun()

with list_col:
    st.markdown("**Current files:**")
    if not kb_files:
        st.info("No KB files yet. Upload one on the left.")
    else:
        for kf in kb_files:
            size_kb = kf.stat().st_size / 1024
            r1, r2, r3, r4 = st.columns([4, 1, 1, 1])
            with r1:
                st.markdown(f"📄 `{kf.name}`")
            with r2:
                st.caption(f"{size_kb:.1f} KB")
            with r3:
                if st.button("👁", key=f"view_{kf.name}", help="Preview"):
                    st.session_state["_kb_preview"] = kf.name
            with r4:
                if st.button("🗑", key=f"del_{kf.name}", help="Delete",
                             type="secondary"):
                    kf.unlink()
                    log.info("kb_file_deleted", name=kf.name)
                    st.success(f"Deleted `{kf.name}`.")
                    st.cache_data.clear()
                    st.rerun()

# Preview pane
preview_name = st.session_state.get("_kb_preview")
if preview_name:
    pf = kb_path / preview_name
    if pf.exists():
        with st.expander(f"📄 {preview_name}", expanded=True):
            st.text(pf.read_text(encoding="utf-8"))
            if st.button("✖  Close"):
                st.session_state["_kb_preview"] = None
                st.rerun()

st.divider()

# ── Conversation Search ───────────────────────────────────────────────────────

st.subheader("🔍 Conversation History")

if not df.empty:
    s1, s2, s3 = st.columns([3, 1, 1])
    with s1:
        search = st.text_input(
            "Search:", placeholder="medicine · appointment · pain · phone…",
            label_visibility="collapsed",
        )
    with s2:
        filter_type = st.selectbox(
            "Type", ["All"] + sorted(df["input_type"].unique().tolist()),
            label_visibility="collapsed",
        )
    with s3:
        filter_model = st.selectbox(
            "Model", ["All"] + sorted(df["model_used"].unique().tolist()),
            label_visibility="collapsed",
        )

    mask = pd.Series([True] * len(df), index=df.index)
    if search:
        mask &= (
            df["query"].str.contains(search, case=False, na=False)
            | df["answer"].str.contains(search, case=False, na=False)
        )
    if filter_type != "All":
        mask &= df["input_type"] == filter_type
    if filter_model != "All":
        mask &= df["model_used"] == filter_model

    filtered = df[mask]
    st.caption(f"Showing {len(filtered)} of {len(df)} conversations")

    for _, row in filtered.tail(20).iloc[::-1].iterrows():
        lat   = f" · {int(row['latency_ms'])} ms" if pd.notna(row["latency_ms"]) else ""
        score = (
            f" · KB {row['retrieval_score']:.2f}"
            if pd.notna(row["retrieval_score"]) else ""
        )
        header = (
            f"**{row['ts'].strftime('%Y-%m-%d %H:%M')}** "
            f"— {row['input_type']} · {row['model_used']}{lat}{score}"
        )
        with st.expander(header):
            st.markdown(f"**You:** {row['query']}")
            st.markdown(f"**Assistant:** {row['answer']}")

else:
    st.info("No history yet.")

# ── Footer ────────────────────────────────────────────────────────────────────

st.markdown(
    "<p style='text-align:center; color:#9aa0a6; font-size:0.8rem; margin-top:40px;'>"
    "ElderAI · Maju Bareng AI 2025 · Hacktiv8 × Google</p>",
    unsafe_allow_html=True,
)
