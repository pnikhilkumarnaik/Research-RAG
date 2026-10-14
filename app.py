"""Streamlit UI:  streamlit run app.py"""
import os

import streamlit as st

from papermind import config, db, ingest, llm

st.set_page_config(page_title="PaperMind", page_icon="📄", layout="wide")
st.title("📄 PaperMind")
st.caption("Chat with research papers: summaries, comparisons, cited answers, saved notes.")

st.session_state.setdefault("chat", [])
st.session_state.setdefault("summaries", {})

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    if not os.getenv("GROQ_API_KEY"):
        st.error("Set GROQ_API_KEY in your .env file, then restart.")
    st.caption(f"Model: `{llm.current_model()}` · .env {'found' if config.ENV_PATH.exists() else 'NOT FOUND'}")

    st.header("Add papers")
    files = st.file_uploader("Upload PDFs", type="pdf", accept_multiple_files=True)
    if files and st.button("Index uploaded PDFs", use_container_width=True):
        for f in files:
            with st.spinner(f"Indexing {f.name}..."):
                try:
                    paper, new = ingest.ingest_pdf(f.getvalue(), f.name)
                    st.success(f"{'Added' if new else 'Already indexed'}: {paper['title'][:60]}")
                except Exception as e:  # noqa: BLE001
                    st.error(f"{f.name}: {e}")

    ref = st.text_input("arXiv URL or id", placeholder="1706.03762")
    if ref and st.button("Fetch from arXiv", use_container_width=True):
        with st.spinner("Downloading and indexing..."):
            try:
                paper, new = ingest.ingest_arxiv(ref)
                st.success(f"{'Added' if new else 'Already indexed'}: {paper['title'][:60]}")
            except Exception as e:  # noqa: BLE001
                st.error(str(e))

    st.header("Library")
    papers = db.list_papers()
    selected: list[str] = []
    if not papers:
        st.info("No papers yet.")
    for p in papers:
        c1, c2 = st.columns([5, 1])
        if c1.checkbox(p["title"][:70], key=f"sel_{p['id']}", value=True,
                       help=f"{p['n_pages']} pages, {p['n_chunks']} chunks"):
            selected.append(p["id"])
        if c2.button("🗑", key=f"del_{p['id']}", help="Remove paper"):
            ingest.remove_paper(p["id"])
            st.rerun()

titles = {p["id"]: p["title"] for p in papers}

tab_ask, tab_sum, tab_cmp, tab_notes = st.tabs(["Ask", "Summarize", "Compare", "Notes"])

# -------------------------------------------------------------------- ask
with tab_ask:
    for i, turn in enumerate(st.session_state.chat):
        with st.chat_message("user"):
            st.write(turn["q"])
        with st.chat_message("assistant"):
            st.markdown(turn["a"])
            with st.expander(f"Sources ({len(turn['hits'])})"):
                for n, h in enumerate(turn["hits"], start=1):
                    st.markdown(f"**[{n}]** {h.title} · {h.section} · p.{h.page} · sim {h.score}")
                    st.caption(h.text[:400] + ("..." if len(h.text) > 400 else ""))
            if st.button("💾 Save as note", key=f"save_{i}"):
                pid = turn["hits"][0].paper_id if turn["hits"] else None
                db.add_note(f"**Q:** {turn['q']}\n\n{turn['a']}", pid)
                st.toast("Saved to notes")

    with st.form("ask_form", clear_on_submit=True):
        q = st.text_input("Ask a question about the selected papers")
        k = st.slider("Passages to retrieve", 3, 12, 6)
        go = st.form_submit_button("Ask")
    if go and q:
        if not selected:
            st.warning("Select at least one paper in the sidebar.")
        else:
            history = []
            for t in st.session_state.chat[-3:]:
                history += [{"role": "user", "content": t["q"]},
                            {"role": "assistant", "content": t["a"]}]
            with st.spinner("Thinking..."):
                try:
                    a, hits = llm.ask(q, selected, k=k, history=history)
                    st.session_state.chat.append({"q": q, "a": a, "hits": hits})
                    st.rerun()
                except Exception as e:  # noqa: BLE001
                    st.error(str(e))
    if st.session_state.chat and st.button("Clear conversation"):
        st.session_state.chat = []
        st.rerun()

# -------------------------------------------------------------- summarize
with tab_sum:
    if not papers:
        st.info("Add a paper first.")
    else:
        pid = st.selectbox("Paper", list(titles), format_func=lambda x: titles[x])
        if st.button("Summarize"):
            with st.spinner("Reading the whole paper..."):
                try:
                    st.session_state.summaries[pid] = llm.summarize(pid)
                except Exception as e:  # noqa: BLE001
                    st.error(str(e))
        if pid in st.session_state.summaries:
            st.markdown(st.session_state.summaries[pid])
            if st.button("💾 Save summary as note"):
                db.add_note(f"**Summary**\n\n{st.session_state.summaries[pid]}", pid)
                st.toast("Saved to notes")

# ---------------------------------------------------------------- compare
with tab_cmp:
    chosen = st.multiselect("Papers to compare (2+)", list(titles), format_func=lambda x: titles[x])
    aspect = st.text_input("Compare on", value="methods, datasets and main results")
    if st.button("Compare"):
        if len(chosen) < 2:
            st.warning("Pick at least two papers.")
        else:
            with st.spinner("Comparing..."):
                try:
                    text, hits = llm.compare(chosen, aspect)
                    st.markdown(text)
                    with st.expander(f"Sources ({len(hits)})"):
                        for n, h in enumerate(hits, start=1):
                            st.markdown(f"**[{n}]** {h.title} · {h.section} · p.{h.page}")
                            st.caption(h.text[:300] + "...")
                except Exception as e:  # noqa: BLE001
                    st.error(str(e))

# ------------------------------------------------------------------ notes
with tab_notes:
    notes = db.list_notes()
    if not notes:
        st.info("Nothing saved yet. Use 'Save as note' on answers and summaries.")
    else:
        st.download_button("⬇ Export all notes (.md)", db.export_notes_markdown(),
                           file_name="notes.md", mime="text/markdown")
    for n in notes:
        with st.container(border=True):
            st.caption(f"{n['paper_title'] or 'General'} · {n['created_at']}")
            st.markdown(n["text"])
            if st.button("Delete", key=f"dn_{n['id']}"):
                db.delete_note(n["id"])
                st.rerun()
