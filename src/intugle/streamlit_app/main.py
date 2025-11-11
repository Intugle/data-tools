# -----------------------
# Import Packages
# -----------------------
# Standard library
import hashlib
import os
import re
import shutil
import time

from datetime import datetime
from pathlib import Path
from typing import Dict, Literal

# Third-party
import pandas as pd
import streamlit as st

from graphviz import Digraph
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from intugle.streamlit_app.helper import (
    _csv_path_for,
    _normalized_table_name,
    _on_name_edit,
    _on_select_change,
    add_table_to_state,
    build_yaml_zip,
    clean_table_name,
    clear_cache,
    ensure_unique_name,
    get_secret,
    go_semantic_all,
    llm_ready_check,
    normalize_col_name,
    read_bytes_to_df,
    rename_table_in_state,
    safe_filename,
    show_links_graph_and_table,
    sizeof_mb,
    standardize_columns,
    validate_column_names,
)

# Local package: intugle
try:
    from intugle import SemanticModel
    from intugle.analysis.models import DataSet
    from intugle.core.settings import settings
except Exception:
    st.error("`intugle` package not available. Please install and restart the app.")
    st.stop()

# -----------------------
# Config & constants
# -----------------------
# MAX_MB = 25
# ACCEPTED_TYPES = (".csv", ".xls", ".xlsx")
# PREVIEW_ROWS = 100

# st.set_page_config(
#     page_title="Intugle • Semantic Model Builder",
#     page_icon="🟣",
#     layout="wide"
# )
# def set_base_dir_once():
#     """
#     Create and store a per-session base directory exactly once.
#     Default folder name is current datetime, e.g., 2025-10-19_14-32-07.
#     Files go under <parent>/<timestamp>/...
#     """
#     if "BASE_DIR" in st.session_state:
#         return

#     # format timestamp (safe for folders)
#     now = datetime.now()
#     stamp = now.strftime("%Y-%m-%d_%H-%M-%S")

#     base = str(stamp)
#     st.session_state.BASE_DIR = base
#     st.toast("Base dir:"+ st.session_state.BASE_DIR)


# def relpath(path: str) -> Path:
#     """Build paths under the session's base dir."""
#     base = Path(st.session_state["BASE_DIR"])
#     return base / path  # returns a Path


# # --- call once at the top of your script ---
# set_base_dir_once()
# # Folders for I/O
# # INPUT_DIR = Path("input")
# INPUT_DIR = relpath("input")
# # MODIFIED_DIR = Path("modified_input")
# MODIFIED_DIR = relpath("modified_input")
# INPUT_DIR.mkdir(parents=True, exist_ok=True)
# MODIFIED_DIR.mkdir(parents=True, exist_ok=True)
# ASSET_DIR = relpath("models")  # change if your folder is named differently
# settings.PROJECT_BASE = str(ASSET_DIR)
# ICON_DIR = relpath("intugle_assets")
# # make directory if dosent exist
# if not ASSET_DIR.exists():
#     ASSET_DIR.mkdir(parents=True, exist_ok=True)
# if not ICON_DIR.exists():
#     ICON_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------
# Config & constants
# -----------------------

# --- Page config MUST be first in the script ---
st.set_page_config(
    page_title="Intugle • Semantic Model Builder",
    page_icon="🟣",
    layout="wide",
)
# ---- Constants ----
MAX_MB: int = 25
ACCEPTED_TYPES = (".csv", ".xls", ".xlsx")
PREVIEW_ROWS: int = 100


# ---- Session-scoped base directory helpers ----
def _timestamp_folder() -> str:
    """Return a filesystem-safe timestamp like '2025-10-19_14-32-07'."""
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def ensure_base_dir() -> Path:
    """
    Create and store a per-session base directory exactly once.
    Returns the Path to the base dir.
    """
    created = False
    if "BASE_DIR" not in st.session_state:
        st.session_state["BASE_DIR"] = _timestamp_folder()
        created = True

    base = Path(st.session_state["BASE_DIR"])
    if created:
        st.toast(f"Base dir: {base}")
    return base


def relpath(path: str | Path) -> Path:
    """Build a path under the session's base dir."""
    base = ensure_base_dir()
    return base / Path(path)


# ---- Initialize I/O directories ----
def init_io_dirs() -> Dict[str, Path]:
    """
    Prepare the working directories for the session and return them.
    """
    paths = {
        "INPUT_DIR": relpath("input"),
        "MODIFIED_DIR": relpath("modified_input"),
        "ASSET_DIR": relpath("intugle/models"),  # adjust if your folder name differs
        # "ICON_DIR": relpath("intugle_assets"),
    }

    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)

    # If intugle settings is available, set project base
    try:
        # 'settings' should be imported earlier from intugle.core.settings
        settings.set_project_base(str(relpath("intugle")))
    except NameError:
        # settings not imported/available; skip without failing the app
        pass

    return paths


# ---- Call once near top of script ----
dirs = init_io_dirs()
INPUT_DIR = dirs["INPUT_DIR"]
MODIFIED_DIR = dirs["MODIFIED_DIR"]
ASSET_DIR = dirs["ASSET_DIR"]
# ICON_DIR = dirs["ICON_DIR"]
# -----------------------
# Session state initialization & lightweight router
# -----------------------

# Types (optional, for clarity in editors)
Route = Literal["home", "semantic"]

DEFAULT_STATE = {
    # Core app state
    "uploader_key": 0,
    "tables": {},
    "ingest_log": [],
    "seen_files": {},
    "main_modify_select": "none",
    "llm_choice": "openai",
    "llm_config": {},
    # Router + semantic flow
    "route": "home",  # type: Route
    "semantic_table": None,
    "data_profiling_glossary": False,
    "semantic_model_done": False,
    "creds_saved": False,
    "links_list": None,
    # One-shot flags
    "just_uploaded_rerun": False,
}


def init_session_state(defaults: dict) -> None:
    """Idempotently seed st.session_state with defaults."""
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


# Initialize once at top of file
init_session_state(DEFAULT_STATE)

# Clear one-shot flags if set
_ = st.session_state.pop("just_uploaded_rerun", False)

# Convenience: whether to show the upload expander
upload_expander: bool = st.session_state["uploader_key"] == 0

# --- init state (add once) ---

# ---- sensible defaults so it doesn't crash on first run
# st.session_state.setdefault("seen_files", {})
# st.session_state.setdefault("creds_saved", False)
# st.session_state.setdefault("route", "home")
# st.session_state.setdefault("data_profiling_glossary", False)
# st.session_state.setdefault("semantic_model_done", False)

# # ----- Session init -----
# if "creds_saved" not in st.session_state:
#     st.session_state.creds_saved = False

# # Provider choice: "openai", "azure-openai", "gemini"
# if "llm_choice" not in st.session_state:
#     st.session_state.llm_choice = "openai"

# # Store normalized config for the active provider
# if "llm_config" not in st.session_state:
#     st.session_state.llm_config = {}


# # Initialize state
# # if "uploader_key" not in st.session_state: st.session_state["uploader_key"] = 0
# if "tables" not in st.session_state: st.session_state["tables"] = {}
# if "ingest_log" not in st.session_state: st.session_state["ingest_log"] = []
# if "seen_files" not in st.session_state: st.session_state["seen_files"] = {}
# if "main_modify_select" not in st.session_state: st.session_state["main_modify_select"] = 'none'

# # --- Simple router state ---
# if "route" not in st.session_state:
#   st.session_state["route"] = "home"  # "home" | "semantic"
# if "semantic_table" not in st.session_state:
#   st.session_state["semantic_table"] = None
# if "data_profiling_glossary" not in st.session_state:
#   st.session_state["data_profiling_glossary"] = False
# if "semantic_model_done" not in st.session_state:
#   st.session_state["semantic_model_done"] = False


# # ---- init once (top of file) ----
# st.session_state.setdefault("uploader_key", 0)
# st.session_state.setdefault("just_uploaded_rerun", False)

# # If we just forced a rerun, clear the flag (one-shot)
# if st.session_state.pop("just_uploaded_rerun", False):
#     pass


# if st.session_state["uploader_key"] ==0:
#     upload_expander = True
# else:
#     upload_expander = False


# -----------------------
# UI: Header
# -----------------------

# download image
# if upload_expander:
#   # url = "https://commons.wikimedia.org/wiki/File:Intugle_icon.png"
#   url = "https://commons.wikimedia.org/wiki/File:Intugle_main_logo.png"
#   path = download_image(url, save_folder=ICON_DIR)
#   print(f"Image downloaded to: {path}")

# Layout: logo + title side by side
_, tcol1, tcol2 = st.columns([1, 2, 0.5])

with tcol1:
    st.title(":violet[Intugle Semantic Modeler]")

with tcol2:
    # st.link_button("🌐 Website", "https://intugle.ai/",type="tertiary")
    st.link_button("GitHub Repo", "https://intugle.github.io/data-tools/")


logo_path = os.path.join(os.path.dirname(__file__), "intugle_assets", "Intugle_main_logo.png")
st.logo(
    # 'https://commons.wikimedia.org/wiki/File:Intugle_icon.png',
    logo_path,
    size="large",
)


# =========================
# Status Bar (single row)
# =========================

# ---- your booleans
upload_done = bool(st.session_state["seen_files"])
creds_done = bool(st.session_state["creds_saved"])
freeze_done = st.session_state.get("route") == "semantic_all"
profiling_done = bool(st.session_state["data_profiling_glossary"])
links_done = bool(st.session_state["semantic_model_done"])

# ---- stages in order
stages = [
    ("Upload Files", upload_done),
    ("LLM Credentials", creds_done),
    ("Rename Tables & Columns", freeze_done),
    ("Profiling & Glossary", profiling_done),
    ("Semantic Link Identification", links_done),
]

# ---- render in sidebar
with st.sidebar:
    st.markdown("## Progress")

    st.markdown(
        """<style>
/* widen sidebar a bit (optional) */
[data-testid="stSidebar"] { width: 320px; min-width: 320px; }

/* scope styles to sidebar only */
.sidebar-status .stage {
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
  border-radius: 999px;
  padding: 8px 12px;
  border: 1.5px solid #E5E7EB;  /* gray-200 */
  background: #F9FAFB;           /* gray-50 */
  font-size: 0.90rem;
  line-height: 1;
  margin-bottom: 8px;            /* stack spacing */
}
.sidebar-status .stage .dot { font-size: 1rem; }
.sidebar-status .stage.done {
  border-color: #10B981;         /* emerald-500 */
  background: #ECFDF5;           /* emerald-50 */
}
.sidebar-status .stage.todo {
  border-color: #8B5CF6;         /* purple-500 */
  background: #F3E8FF;           /* purple-100 */
}
.sidebar-status .stage .label { font-weight: 600; color: #111827; } /* gray-900 */
</style>
<div class="sidebar-status">
""",
        unsafe_allow_html=True,
    )

    html_parts = []
    for label, done in stages:
        icon = "✔️" if done else "🟣"
        state_cls = "done" if done else "todo"
        html_parts.append(
            f'<div class="stage {state_cls}"><span class="dot">{icon}</span><span class="label">{label}</span></div>'
        )

    st.markdown("".join(html_parts) + "</div>", unsafe_allow_html=True)
    st.divider()
# ------------------------------------------
# st.title("Intugle Semantic Modeler")


if st.session_state["route"] == "home":
    st.subheader("How it works")

    dot = Digraph(
        name="intugle_flow",
        graph_attr={
            "rankdir": "LR",  # left → right
            "bgcolor": "white",
            "fontsize": "10",
            "pad": "0.2",
        },
        node_attr={
            "shape": "rect",
            "style": "rounded,filled",
            "fontname": "Inter, Helvetica, Arial, sans-serif",
            "color": "#8B5CF6",  # Intugle purple border
            "fillcolor": "#F3E8FF",  # soft lilac fill
            "fontsize": "11",
        },
        edge_attr={
            "color": "#8B5CF6",
            "fontname": "Inter, Helvetica, Arial, sans-serif",
            "fontsize": "10",
        },
    )

    # Nodes
    dot.node("U", "Upload CSV/Excel\n(one or many)")
    dot.node("S", "Size ≤ 25 MB?", shape="diamond", fillcolor="#EDE9FE")
    dot.node("P", "Profile columns\n• Uniqueness\n• Completeness\n• Data type")
    dot.node("G", "Generate glossary\nfor all columns")
    dot.node("M", "Build semantic model\n(Currently single link per table pair)")
    dot.node("X", "Skip file\n(too large)", fillcolor="#FFE4E6", color="#EF4444")

    # Edges
    dot.edge("U", "S")
    dot.edge("S", "P", label="Yes")
    dot.edge("S", "X", label="No")
    dot.edge("P", "G")
    dot.edge("G", "M")

    # Render in Streamlit
    st.graphviz_chart(dot, width="stretch")

    st.subheader("1) Upload Files")
    with st.expander("Upload Your Files here..", expanded=upload_expander):
        uploaded_files = st.file_uploader(
            "Drop files here or browse",
            type=[ext.lstrip(".") for ext in ACCEPTED_TYPES],
            accept_multiple_files=True,
            key=f"uploader_{st.session_state['uploader_key']}",
        )

        if uploaded_files:
            st.caption(f"Received {len(uploaded_files)} file(s).")

            for upl in uploaded_files:
                # Read bytes once so we can hash and parse from the same buffer
                file_bytes = upl.getvalue()
                size_mb = sizeof_mb(len(file_bytes))
                sha = hashlib.sha1(file_bytes).hexdigest()

                # Skip files already seen by content hash (prevents duplicates on reruns)
                if sha in st.session_state["seen_files"]:
                    continue

                # Build a log row; we only append if we actually process/skip/error
                log_row = {
                    "source_file": upl.name,
                    "size_mb": size_mb,
                    "status": "⏳ pending",
                    "table_name": None,
                    "rows": None,
                    "cols": None,
                    "details": "",
                }

                # Enforce size
                if size_mb > MAX_MB:
                    st.warning(f"Skipping **{upl.name}** because it exceeds {MAX_MB} MB.")
                    # log_row["status"] = "⛔ too large (>25MB)"
                    # log_row["details"] = "Skipped due to size limit."
                    # st.session_state["ingest_log"].append(log_row)
                    continue

                # Parse
                try:
                    with st.spinner(f"Reading `{upl.name}`..."):
                        df, note = read_bytes_to_df(upl.name, file_bytes)
                except Exception as e:
                    st.error(f"Failed to read **{upl.name}**: {e}")
                    # log_row["status"] = "❌ read error"
                    # log_row["details"] = str(e)
                    # st.session_state["ingest_log"].append(log_row)
                    continue

                # Standardize columns
                with st.spinner(f"Standardizing columns for `{upl.name}`..."):
                    df = standardize_columns(df)

                # # Initial table name (no extra counters unless a different file collides)
                input_path = INPUT_DIR / safe_filename(clean_table_name(upl.name), ".csv")
                try:
                    if (not input_path.exists()) or (hashlib.sha1(input_path.read_bytes()).hexdigest() != sha):
                        input_path.write_bytes(file_bytes)
                except Exception as e:
                    st.warning(f"Could not save original file for **{upl.name}**: {e}")

                # b) Standardized table -> modified_input/ as CSV (ALWAYS overwrite)
                default_name = clean_table_name(upl.name)
                unique_default = ensure_unique_name(default_name, st.session_state["tables"])

                modified_path = MODIFIED_DIR / safe_filename(unique_default, ".csv")
                try:
                    df.to_csv(modified_path, index=False)
                    # cleanup any legacy xlsx with the same stem
                    legacy_xlsx = MODIFIED_DIR / safe_filename(unique_default, ".xlsx")
                    if legacy_xlsx.exists():
                        legacy_xlsx.unlink(missing_ok=True)
                except Exception as e:
                    st.error(f"Failed to save standardized CSV to modified_input/: {e}")
                    continue
                # -----------------------------------------------

                # -----------------------------------------------
                # Metadata
                rows_i, cols_i = int(df.shape[0]), int(df.shape[1])
                meta = {
                    "source_file": upl.name,
                    "size_mb": size_mb,
                    "note": note,
                    "rows": rows_i,
                    "cols": cols_i,
                    "timestamp": time.time(),
                    "modified_path": str(modified_path),  # <— new
                }

                # Save table and fingerprint
                with st.spinner(f"Saving `{unique_default}`..."):
                    add_table_to_state(unique_default, df, meta)

                st.session_state["seen_files"][sha] = {
                    "table_name": unique_default,
                    "source_file": upl.name,
                    "size_mb": size_mb,
                }

                # Log success
                log_row.update({
                    "status": "✅ loaded",
                    "table_name": unique_default,
                    "rows": rows_i,
                    "cols": cols_i,
                    "details": note or "",
                })
                st.session_state["ingest_log"].append(log_row)

            st.toast("Processing completed for all eligible files.")
            # Clear the uploader selection and force exactly one rerun
            st.session_state["uploader_key"] += 1  # resets file_uploader
            st.session_state["just_uploaded_rerun"] = True  # one-shot marker
            st.rerun()

    # -----------------------
    # Tables overview (read-only summary)
    # -----------------------
    # Normalize ingest_log names from seen_files (ensures latest rename is shown)
    for d, info in st.session_state.get("seen_files", {}).items():
        latest_name = info.get("table_name")
        for row in st.session_state.get("ingest_log", []):
            if row.get("source_file") == info.get("source_file") and row.get("status", "").startswith("✅"):
                row["table_name"] = latest_name

    if st.session_state.get("tables") or st.session_state.get("ingest_log"):
        with st.expander("1) Review Tables", expanded=False):
            # Summary now shows status/details only; no inline actions
            if st.session_state.get("ingest_log"):
                summary_df = pd.DataFrame(st.session_state["ingest_log"]).copy()
                cols_order = ["table_name", "source_file", "size_mb", "rows", "cols", "status", "details"]
                summary_df = summary_df[[c for c in cols_order if c in summary_df.columns]]
            else:
                # Fallback if ingest_log not present
                rows = []
                for tname, payload in st.session_state["tables"].items():
                    m = payload["meta"]
                    rows.append({
                        "table_name": tname,
                        "source_file": m["source_file"],
                        "size_mb": m["size_mb"],
                        "rows": m["rows"],
                        "cols": m["cols"],
                        "status": "✅ loaded",
                        "details": m.get("note", ""),
                    })
                summary_df = pd.DataFrame(rows).sort_values("table_name")

            st.dataframe(summary_df, width="stretch", hide_index=True)
    else:
        # st.info("No tables loaded yet. Upload some CSV/Excel files above to get started!")

        st.toast(
            """
      **Welcome to Intugle!**
      We’re thrilled to have you here.
      """,
            icon="🕸️",
        )

    # -----------------------
    # Modify table & columns (MAIN PAGE, under the review table)
    # -----------------------

    # --- Always-visible table picker + synced final name ---

    if not st.session_state.get("tables"):
        # st.info("Load tables to modify them here.")
        time.sleep(1)
        st.toast("Let us Start by uploading files and submit your LLM credentials")

    else:
        st.divider()
        st.subheader("2) Modify table & columns")
        # Ensure state keys exist
        st.session_state.setdefault("final_name_user_edited", False)

        # left, right = st.columns([0.5, 0.5])

        # Build options; always render the selectbox
        has_tables = bool(st.session_state.get("tables"))
        tnames = sorted(st.session_state["tables"].keys()) if has_tables else []
        options = tnames if has_tables else ["— no tables loaded —"]
        col1, col2, col3, col4 = st.columns([2, 0.5, 2, 2])
        with col1:
            sel = st.selectbox(
                "Select table to modify",
                options=options,
                index=0,
                # key="main_modify_select",
                on_change=_on_select_change,
                disabled=not has_tables,
                help="Choose a loaded table. This is always shown; it will be disabled until you upload data.",
            )
            out_fmt = "CSV"
            # Or, if you want to show a control but keep a default, uncomment:
            # out_fmt = st.radio("Save format", ["CSV", "Excel"], horizontal=True, key="main_modify_fmt")

            # Guard when there are no tables yet
            if not has_tables:
                st.info("Load tables to modify them here.")
                st.stop()

            # Use the selected table
            payload = st.session_state["tables"][sel]
            df_current = payload["df"]
            orig_cols = list(df_current.columns)
        with col2:
            # add a right emoji arrow
            # st.markdown("<div style='text-align: center; font-size: 24px;'>➡️</div>", unsafe_allow_html=True)
            st.image(
                "https://upload.wikimedia.org/wikipedia/commons/c/ca/Eo_circle_purple_arrow-right.svg",
                width=80,  # Manually Adjust the width of the image as per requirement
            )

        with col3:
            # Final name input that mirrors selection until the user edits it
            # st.markdown("**Rename table (optional)**")
            final_name_raw = st.text_input(
                "Rename table (optional)",
                # key="main_modify_final_name",
                # value=st.session_state.get("main_modify_final_name", sel) or sel,
                value=sel,
                on_change=_on_name_edit,
                help="Defaults to the selected table name. Will be normalized to lowercase with underscores.",
            )

        # Current paths
        current_name = sel
        current_path = _csv_path_for(current_name, MODIFIED_DIR)

        # -------------------------------
        # ACTIONS
        # -------------------------------
        (
            __,
            _,
            act_col1,
            ___,
        ) = st.columns([2, 0.5, 2, 2])

        # 1) RENAME TABLE (and CSV file) — no column changes here
        with act_col1:
            if st.button("Rename table", type="primary", width="content", key="btn_rename_table"):
                new_name = _normalized_table_name(final_name_raw)
                if not new_name:
                    st.error("Final table name cannot be empty after normalization.")
                    st.stop()

                if new_name == current_name:
                    st.toast("Table name unchanged.")
                else:
                    new_path = _csv_path_for(new_name, MODIFIED_DIR)

                    # Move/rename the CSV on disk (if it exists). If it doesn't, create from in-memory df.
                    try:
                        if current_path.exists():
                            # Avoid cross-device rename oddities
                            current_path.replace(new_path)
                        else:
                            # If the file isn't there yet, write the current DataFrame
                            st.session_state["tables"][current_name]["df"].to_csv(new_path, index=False)
                    except Exception as e:
                        st.error(f"Failed to rename CSV file: {e}")
                        st.stop()

                    # Cleanup any legacy .xlsx with the old name
                    legacy_xlsx = MODIFIED_DIR / safe_filename(current_name, ".xlsx")
                    legacy_xlsx.unlink(missing_ok=True)

                    # Update in-memory state & logs
                    rename_table_in_state(current_name, new_name)
                    st.session_state["tables"][new_name]["meta"]["modified_path"] = str(new_path)
                    for row in st.session_state.get("ingest_log", []):
                        if row.get("table_name") == current_name:
                            row["table_name"] = new_name
                    for _, info in st.session_state.get("seen_files", {}).items():
                        if info.get("table_name") == current_name:
                            info["table_name"] = new_name

                    # Sync the selectbox and input defaults
                    st.session_state["main_modify_select"] = new_name
                    st.session_state["main_modify_final_name"] = new_name
                    st.session_state["final_name_user_edited"] = False

                    st.success(f"Renamed **{current_name}** → **{new_name}** and updated CSV file.")
                    st.rerun()

        # Column editor (unchanged)
        st.markdown("**Edit or ignore columns**")
        editor_src = {
            "original_column_name": orig_cols,
            "new_column_name": orig_cols.copy(),  # default to current names
            "ignore_column": [False] * len(orig_cols),
        }
        edit_df = st.data_editor(
            pd.DataFrame(editor_src),
            hide_index=True,
            width="stretch",
            column_config={
                "original_column_name": st.column_config.TextColumn("Original_Column_Name", disabled=True),
                "new_column_name": st.column_config.TextColumn(
                    "New_Column_Name (Editable)", help="Enter desired column names"
                ),
                "ignore_column": st.column_config.CheckboxColumn(
                    "Select_column_to_Ignore", help="Drop this column for sematic model"
                ),
            },
            key="main_modify_editor",
        )
        # ---------- Editor UI already created above ----------
        # sel, df_current, orig_cols, final_name_raw, edit_df exist

        # 2) FREEZE COLUMN NAMES — apply edits/ignores & save back to SAME file name (CSV overwrite)
        # with act_col2:
        if st.button("Freeze column names", type="primary", width="content", key="btn_freeze_cols"):
            # Pull edits
            new_names_input = list(edit_df["new_column_name"])
            ignored_flags = list(edit_df["ignore_column"])

            # Validate proposed names
            errs = validate_column_names(orig_cols, new_names_input, ignored_flags)
            if errs:
                for e in errs:
                    st.error(e)
                st.stop()

            # Build modified DataFrame
            keep_idx = [i for i, ig in enumerate(ignored_flags) if not ig]
            kept_cols = [orig_cols[i] for i in keep_idx]
            new_names = [normalize_col_name(new_names_input[i]) for i in keep_idx]

            df_mod = df_current.loc[:, kept_cols].copy()
            df_mod.columns = new_names

            # Determine the *current* table name (which might have been renamed already)
            # live_name = st.session_state["main_modify_select"]
            live_name = final_name_raw
            st.info(live_name)
            live_path = _csv_path_for(live_name, MODIFIED_DIR)

            # Save back to the SAME file (overwrite)
            try:
                df_mod.to_csv(live_path, index=False)
            except Exception as e:
                st.error(f"Failed to write CSV: {e}")
                st.stop()
            time.sleep(3)
            # Update in-memory table payload
            st.session_state["tables"][live_name]["df"] = df_mod
            st.session_state["tables"][live_name]["meta"]["rows"] = int(df_mod.shape[0])
            st.session_state["tables"][live_name]["meta"]["cols"] = int(df_mod.shape[1])
            st.session_state["tables"][live_name]["meta"]["modified_path"] = str(live_path)

            st.success(f"Column names frozen and saved to `{live_path.name}`.")
            st.rerun()


# -----------------------
# Sidebar
# -----------------------
with st.sidebar:
    st.header("🔑 LLM Settings")

    # If already saved this session: show summary + "Change settings"
    if st.session_state.creds_saved:
        # st.write(f"**LLM Service:** `{provider_display_string()}`")

        choice = st.session_state.llm_choice
        cfg = st.session_state.llm_config

        if choice == "openai":
            # st.write(f"**OpenAI Model Loaded** `{cfg.get('model','')}`")
            # st.write(f"**Model:** `{cfg.get('model','')}`")
            # st.write(f"**OPENAI_API_KEY:** {mask(get_secret('OPENAI_API_KEY'))}")
            # pip install -U langchain-openai

            llm_temp = ChatOpenAI(
                model=os.environ["LLM_PROVIDER"],  # pick your OpenAI model
                temperature=0,
                # api_key="...",       # or set env var: OPENAI_API_KEY=...
                # base_url="...",      # only if you're using a compatible proxy
            )

            messages = [
                (
                    "system",
                    "You are a helpful assistant that translates French to English. Translate the user sentence.",
                ),
                ("human", "Le point de terminaison OpenAI a été chargé avec succès."),
            ]

            ai_msg = llm_temp.invoke(messages)
            st.success(ai_msg.content)

            # st.success(f"**OpenAI API Key load successful:**")

        elif choice == "azure-openai":
            # Import Azure OpenAI
            model = os.environ.get("LLM_PROVIDER", "").split(":")[-1]
            llm_temp = AzureChatOpenAI(
                azure_deployment=model,  # your deployed model name or alias
                # azure_endpoint="https://<your>.openai.azure.com/",
                # api_key="...",
                # api_version="2024-xx-xx"
            )
            messages = [
                (
                    "system",
                    "You are a helpful assistant that translates French to English. Translate the user sentence.",
                ),
                ("human", "Le point de terminaison Azure OpenAI a été chargé avec succès."),
            ]
            ai_msg = llm_temp.invoke(messages)
            ai_msg = ai_msg.content
            # st.success(f"**Azure OpenAI Endpoint load successful:**")
            st.success(ai_msg)
            # st.write(f'LLM_PROVIDER: {os.environ["LLM_PROVIDER"]}')
            # st.write(f'AZURE_OPENAI_API_KEY: {os.environ["AZURE_OPENAI_API_KEY"]}')
            # st.write(f'OPENAI_API_VERSION: {os.environ["OPENAI_API_VERSION"]}')
            # st.write(f'AZURE_OPENAI_ENDPOINT: {os.environ["AZURE_OPENAI_ENDPOINT"]}')

        elif choice == "gemini":
            # st.write(f"**Model:** `{cfg.get('model','')}`")
            # Common env names for Gemini: GEMINI_API_KEY or GOOGLE_API_KEY
            # st.write(f"**GEMINI/GOOGLE_API_KEY:** {mask(get_secret('GEMINI_API_KEY') or get_secret('GOOGLE_API_KEY'))}")

            llm_temp = ChatGoogleGenerativeAI(
                model=os.environ["LLM_PROVIDER"],
                temperature=0,
                # google_api_key="...",     # or set env var: GOOGLE_API_KEY=...
            )

            messages = [
                (
                    "system",
                    "You are a helpful assistant that translates French to English. Translate the user sentence.",
                ),
                ("human", "Le point de terminaison Google Gemini a été chargé avec succès."),
            ]

            ai_msg = llm_temp.invoke(messages)
            ai_msg = ai_msg.content
            st.success(ai_msg)
            # st.success(f"**Gemini API Key load successful:**")
        # if st.button("Change settings"):
        #     st.session_state.creds_saved = False
        #     st.stop()

    # Otherwise: render the provider picker + provider-specific fields
    with st.expander("LLM Settings", expanded=not st.session_state.creds_saved):
        provider = st.selectbox(
            "Choose LLM provider",
            options=["openai", "azure-openai", "google_genai"],
            index=["openai", "azure-openai", "google_genai"].index(st.session_state.llm_choice),
            help="Pick your LLM backend.",
        )
        st.session_state.llm_choice = provider

        # --------- OPENAI ---------
        if provider == "openai":
            # Pre-fill from env/secrets if present
            pre_key = get_secret("OPENAI_API_KEY", "")
            model = st.selectbox(
                "Model",
                # ["openai:gpt-3.5-turbo"],
                ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
                index=0,
            )
            api_key = st.text_input(
                "OpenAI API key", type="password", value=pre_key, placeholder="sk-********************************"
            )

            if st.button("Save provider settings", type="primary", width="stretch"):
                if not api_key or len(api_key) < 20:
                    st.error("Please enter a valid OpenAI API key.")
                else:
                    st.session_state.llm_config = {
                        "model": model,
                    }
                    # Normalize env vars (and a generic LLM_PROVIDER string if you use it elsewhere)
                    # save_env({
                    #     "OPENAI_API_KEY": api_key.strip(),
                    #     "LLM_PROVIDER": f"openai:{model}",
                    # })
                    settings.LLM_PROVIDER = f"openai:{model}"
                    os.environ["OPENAI_API_KEY"] = api_key.strip()
                    os.environ["LLM_PROVIDER"] = model
                    st.session_state.creds_saved = True
                    st.success("OpenAI settings saved.")
                    st.rerun()

        # --------- AZURE OPENAI ---------
        elif provider == "azure-openai":
            pre_key = get_secret("AZURE_OPENAI_API_KEY", "")
            pre_endpoint = get_secret("AZURE_OPENAI_ENDPOINT", "https://YOUR-RESOURCE-NAME.openai.azure.com/")
            pre_llm_provider = get_secret("LLM_PROVIDER", "")
            pre_version = get_secret("OPENAI_API_VERSION", "2024-06-01")

            endpoint = st.text_input(
                "Azure OpenAI endpoint", value=pre_endpoint, placeholder="https://<resource>.openai.azure.com/"
            )
            llm_provider = st.text_input("Provider name", value=pre_llm_provider, placeholder="azure_openai:gpt-4o")
            api_version = st.text_input("API version", value=pre_version, placeholder="2024-06-01")
            api_key = st.text_input(
                "Azure OpenAI API key", type="password", value=pre_key, placeholder="****************"
            )

            if st.button("Save provider settings", type="primary", width="stretch"):
                errs = []
                if not endpoint.startswith("http"):
                    errs.append("Endpoint must start with http/https.")
                if not llm_provider:
                    errs.append("LLM provider name is required.")
                if not api_version:
                    errs.append("API version is required.")
                if not api_key or len(api_key) < 20:
                    errs.append("Enter a valid Azure OpenAI API key.")
                if errs:
                    for e in errs:
                        st.error(e)
                else:
                    st.session_state.llm_config = {
                        "endpoint": endpoint.strip(),
                        "llm_provider": llm_provider.strip(),
                        "api_version": api_version.strip(),
                    }
                    # save_env({
                    #     "AZURE_OPENAI_ENDPOINT": endpoint.strip(),
                    #     "LLM_PROVIDER": llm_provider.strip(),
                    #     "OPENAI_API_VERSION": api_version.strip(),
                    #     "AZURE_OPENAI_API_KEY": api_key.strip(),
                    #     # "LLM_PROVIDER": f"azure-openai:{deployment.strip()}@{api_version.strip()}",
                    # })
                    os.environ["LLM_PROVIDER"] = str(llm_provider.strip())
                    settings.LLM_PROVIDER = str(llm_provider.strip())
                    os.environ["AZURE_OPENAI_API_KEY"] = str(api_key.strip())
                    os.environ["OPENAI_API_VERSION"] = str(api_version.strip())
                    os.environ["AZURE_OPENAI_ENDPOINT"] = str(endpoint.strip())

                    st.session_state.creds_saved = True
                    st.success("Azure OpenAI settings saved.")
                    st.rerun()

        # --------- GEMINI ---------
        elif provider == "google_genai":
            # Gemini keys are commonly under GEMINI_API_KEY or GOOGLE_API_KEY
            pre_key = get_secret("GOOGLE_API_KEY") or ""
            model = st.selectbox("Model", ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite"], index=0)
            api_key = st.text_input(
                "Gemini API key", type="password", value=pre_key, placeholder="********************************"
            )

            if st.button("Save provider settings", type="primary", width="stretch"):
                if not api_key or len(api_key) < 20:
                    st.error("Please enter a valid Gemini API key.")
                else:
                    st.session_state.llm_config = {"model": model}
                    # Set both common env var names so whichever client you use can find it
                    # save_env({
                    #     "GEMINI_API_KEY": api_key.strip(),
                    #     "GOOGLE_API_KEY": api_key.strip(),
                    #     "LLM_PROVIDER": f"gemini:{model}",
                    # })
                    os.environ["GOOGLE_API_KEY"] = api_key.strip()
                    os.environ["LLM_PROVIDER"] = model
                    settings.LLM_PROVIDER = f"google_genai:{model}"
                    st.session_state.creds_saved = True
                    st.success("Gemini settings saved.")
                    st.rerun()

with st.sidebar:
    # Settings & info
    # with st.expander("Reset Settings",expanded=False):
    #   st.write(f"Max file size per file: **{MAX_MB} MB**")
    #   st.write(f"Accepted types: {', '.join(ACCEPTED_TYPES)}")

    if st.button("Reset App", type="primary", width="content"):
        # st.session_state["tables"] = {}
        # st.session_state["ingest_log"] = []   # optional: reset the log
        # st.session_state["seen_files"] = {}   # important: allow re-uploading same files
        # st.session_state["uploader_key"] += 1 # <-- resets the uploader selection
        clear_cache()
        try:
            shutil.rmtree(INPUT_DIR)
            shutil.rmtree(ASSET_DIR)
            shutil.rmtree(MODIFIED_DIR)

            print("input & modified_input folders found & deleted. You are good to go")
        except:  # noqa: E722
            print("No folders found. You are good to go")

        st.success("Cleared all loaded tables and upload selection.")

        st.rerun()


# ----------------------- ----------------------- ----------------------- ----------------------- -----------------------
# 5) Create a Semantic Model (uses all files in modified_input/)
# ----------------------- ----------------------- ----------------------- ----------------------- -----------------------
# ======================

# --- tiny helpers (define once) ---


def _list_modified_files():
    return sorted(list(MODIFIED_DIR.glob("*.csv")) + list(MODIFIED_DIR.glob("*.xlsx")))


def _source_type_from_suffix(p: Path) -> str:
    return "csv" if p.suffix.lower() == ".csv" else "excel"


# Find modified files
modified_csv = list(MODIFIED_DIR.glob("*.csv"))
modified_xlsx = list(MODIFIED_DIR.glob("*.xlsx"))
modified_files = modified_csv + modified_xlsx
n_files = len(modified_files)

# LLM readiness
ok, err = llm_ready_check()
if not ok:
    st.error(err)
    st.stop()


if n_files == 0:
    st.info("No tables found. Upload & Freeze at least one table to continue.")
elif st.session_state.get("route") != "semantic_all":
    st.caption(f"Found **{n_files}** file(s)")
    # Brief preview of filenames (first 5)
    show = [p.name for p in modified_files[:5]]
    # st.write(", ".join(show) + (" ..." if n_files > 5 else ""))

    # Full-width action button
    st.divider()
    if st.button(
        "🧠 Create Semantic Model from Modified Data", type="primary", width="stretch", key="btn_semantic_all"
    ):
        go_semantic_all()


# =========================
# Semantic page content
# =========================
if st.session_state.get("route") == "semantic_all":
    # if st.sidebar.button("⬅️ Back to Data", key="btn_semantic_back"):
    #     st.session_state["route"] = "home"
    #     st.rerun()
    ##############################################################################
    with st.sidebar:
        # Make the sidebar a full-height flex column
        st.markdown(
            """
    <style>
    [data-testid="stSidebar"] > div {
        display: flex;
        flex-direction: column;
        height: 100%;
    }
    </style>
    """,
            unsafe_allow_html=True,
        )

        # --- your existing sidebar content goes here ---
        st.markdown("# ")
        # ... (status pills, etc.)

        # This flexible spacer expands and pushes what follows to the bottom
        st.markdown('<div style="flex:1 1 auto;"></div>', unsafe_allow_html=True)

        st.divider()
        if st.button("⬅️ Back to Data", key="btn_semantic_back", width="stretch"):
            st.session_state["route"] = "home"
            st.rerun()
    ##############################################################################
    st.header("3) 🧠 Build Semantic Model")
    # 2) Define domain BEFORE using it
    st.markdown("#### Domain")
    dcol1, dcol2 = st.columns([1, 1])
    with dcol1:
        # show whatever is currently saved as the default in the box
        domain = st.text_input(
            "Enter a domain (e.g., Manufacturing)",
            value=st.session_state.get("semantic_domain", "NA"),
            key="semantic_domain_input",
        )

    # with dcol2:
    if st.button("Set Domain", type="primary", width="content"):
        # Only commit when the button is clicked
        committed = (st.session_state.get("semantic_domain_input") or "").strip() or "NA"
        st.session_state["semantic_domain"] = committed
        st.toast(f"Domain set to: **{committed}**")

    # Require domain

    if (
        not domain.strip()
        or domain.strip().upper() == "NA"
        or domain.strip() == ""
        or not bool(re.search(r"[A-Za-z0-9]", domain.strip()))
    ):
        st.warning("Please enter a valid domain before building the semantic model.")
        st.stop()
    # 1) Define files BEFORE using them
    files = _list_modified_files()
    if not files:
        st.warning("No files found in modified_input/. Go back and save at least one modified table.")
        if st.button("⬅️ Back"):
            st.session_state["route"] = "home"
            st.rerun()
        st.stop()

    st.caption(f"Semantic Model will be built for **{len(files)}** table(s).")

    gdf_iter_ph = st.empty()
    # optional: keep a cumulative copy if you still want it elsewhere
    st.session_state.setdefault("semantic_gdf_all", None)

    total = len(files)
    my_bar = st.progress(0, text="Preparing data for semantic model creation. Please wait.")

    for idx, p in enumerate(files, start=1):  # start=2 because first file already processed
        if idx == 1:
            # Initialize with the first file
            first = files[0]
            data_sources = {first.stem: {"path": str(first), "type": _source_type_from_suffix(first)}}

            with st.spinner(f"Initializing Semantic Model with `{first.name}` …"):
                sm = SemanticModel(data_input=data_sources, domain=domain.strip())
                st.session_state["sm"] = sm

        ds_name = p.stem

        with st.spinner(f"Adding dataset `{ds_name}` …"):
            new_ds = DataSet({"path": str(p), "type": _source_type_from_suffix(p)}, name=ds_name)
            sm.datasets[ds_name] = new_ds

        with st.spinner(f"Profiling `{ds_name}` ({idx}/{total})…"):
            sm.profile()
        with st.spinner(f"Generating glossary for `{ds_name}` …"):
            sm.generate_glossary()

        # with st.status(f"Preparing data to build semantic model `{ds_name}` …", expanded=True) as status:
        #     new_ds = DataSet({"path": str(p), "type": _source_type_from_suffix(p)}, name=ds_name)
        #     sm.datasets[ds_name] = new_ds
        #     st.write(f"Profiling `{ds_name}` ({idx}/{total}) …")
        #     sm.profile()
        #     st.write(f"Generating glossary for `{ds_name}` …")
        #     sm.generate_glossary()
        percent_complete = idx / total
        my_bar.progress(
            percent_complete,
            text=f"Preparing data for semantic model creation {round(percent_complete * 100)}%. Please wait.",
        )

        try:
            profiling_df = sm.profiling_df.copy()
            glossary_df = sm.glossary_df.copy()

            gdf_this = pd.merge(
                glossary_df,
                profiling_df,
                on=["table_name", "column_name"],
                how="left",
                suffixes=("_gloss", "_prof"),
            )

            # ---- FLUSH previous view and show ONLY this iteration ----
            gdf_iter_ph.empty()
            with gdf_iter_ph.container():
                st.toast(f"##### ✅ Glossary for `{ds_name}` ({idx}/{total})")
                # add title to the table
                st.markdown(f"### Glossary & Profiling details for `{idx}` tables")
                st.dataframe(
                    gdf_this[
                        [
                            "table_name",
                            "column_name",
                            "datatype_l1",
                            "datatype_l2",
                            "count",
                            "null_count",
                            "distinct_count",
                            "uniqueness",
                            "completeness",
                            "business_glossary",
                            "business_tags",
                            "sample_data",
                        ]
                    ],
                    hide_index=True,
                    width="stretch",
                )
                st.session_state["sm"] = sm

        except Exception as e:
            st.warning(f"Could not render glossary view for `{ds_name}`: {e}")

    st.success("Semantic model profiling & glossary generation completed for all tables.")
    if not st.session_state["data_profiling_glossary"]:
        st.session_state["data_profiling_glossary"] = True
        st.rerun()

    # Link prediction and back button (unchanged)
    st.divider()
    st.subheader("4) Link Prediction")

    if "sm" not in st.session_state:
        st.info("Build the semantic model first to enable link prediction.")
    else:
        sm = st.session_state["sm"]
        if st.button("🔗 Run Link Prediction", type="primary", key="btn_link_pred", width="stretch"):
            with st.spinner("Predicting links …"):
                sm.predict_links()
                predictor_instance = sm.link_predictor
                st.session_state["links_list"] = predictor_instance.links  # <-- SAVE to state
            st.session_state["semantic_model_done"] = True  # <-- FLAG done
            st.success("Link prediction completed.")

        # --- render results if we have them ---
        if st.session_state.get("semantic_model_done") and st.session_state.get("links_list"):
            try:
                show_links_graph_and_table(st.session_state["links_list"])  # <-- use saved list
            except Exception as e:
                st.warning(f"Could not render link prediction results: {e}")
        # if st.button("🔗 Run Link Prediction", type="primary", width="stretch", key="btn_link_pred"):
        #     with st.spinner("Predicting links …"):
        #         sm.predict_links()
        #         # After running the pipeline...
        #         predictor_instance = sm.link_predictor

        #         # Now you can use all the methods of the LinkPredictor
        #         links_list = predictor_instance.links
        #     st.success("Link prediction completed.")

        #     try:
        #         # ---------- usage ----------
        #         show_links_graph_and_table(links_list)   # <-- pass your list[PredictedLink] here
        #     except Exception as e:
        #         st.warning(f"Could not render link prediction results: {e}")

        #     if st.session_state["semantic_model_done"] == False:
        #         st.session_state["semantic_model_done"] = True
        #         st.rerun()

        with st.sidebar:
            zip_bytes, file_count = build_yaml_zip(ASSET_DIR)
            if file_count:
                st.download_button(
                    label=f"Download {file_count} YAML file{'s' if file_count != 1 else ''} (ZIP)",
                    data=zip_bytes,
                    file_name=f"yaml_assets_{time.strftime('%Y%m%d_%H%M%S')}.zip",
                    mime="application/zip",
                    width="stretch",
                )
            else:
                st.info(f"No .yml or .yaml files found in '{ASSET_DIR}/'.")
