
# -----------------------
# Import Packages
# -----------------------
# Standard library
import io
import os
import re
import zipfile

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

# Third-party
import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# -----------------------
# Helpers
# -----------------------


# EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# st.session_state.setdefault("email_prompt_done", False)
# st.session_state.setdefault("notification_email", "")

# def is_valid_email(s: str) -> bool:
#     return bool(EMAIL_RE.match(s.strip()))

# # --- helper: send email (SMTP via st.secrets)
# def send_email(to_addr: str, subject: str, body: str) -> tuple[bool, str]:
#     try:
#         import smtplib, ssl
#         conf = st.secrets["smtp"]
#         msg = (
#             f"From: {conf.get('from_name','Notifier')} <{conf['from_email']}>\r\n"
#             f"To: <{to_addr}>\r\n"
#             f"Subject: {subject}\r\n"
#             "\r\n"
#             f"{body}"
#         )
#         context = ssl.create_default_context()
#         with smtplib.SMTP_SSL(conf["host"], conf.get("port", 465), context=context) as server:
#             server.login(conf["username"], conf["password"])
#             server.sendmail(conf["from_email"], [to_addr], msg)
#         return True, "Sent"
#     except Exception as e:
#         return False, str(e)

# # --- choose dialog API (new or experimental)
# dialog_api = getattr(st, "dialog", getattr(st, "experimental_dialog", None))

# def open_email_dialog():
#     if not st.session_state.get("email_prompt_done", False) and dialog_api:
#         @dialog_api("Optional email for notification")
#         def _dlg():
#             st.write(
#                 "The semantic model can take a while to run. "
#                 "Provide an email (optional) and I’ll notify you when it’s ready."
#             )
#             email = st.text_input("Email (optional)", value=st.session_state.get("notification_email",""))
#             c1, c2 = st.columns([1,1])
#             with c1:
#                 if st.button("Notify me",width="stretch",type= "primary"):
#                     if email.strip():
#                         if is_valid_email(email):
#                             st.session_state["notification_email"] = email.strip()
#                             ok, msg = send_email(
#                                 to_addr=email.strip(),
#                                 subject="You’ll be notified when the semantic model is ready",
#                                 body="Thanks! We’ll email you when the semantic model completes."
#                             )
#                             if ok:
#                                 st.success("Email noted. You’ll get a notification.")
#                             else:
#                                 st.warning(f"Could not send email: {msg}")
#                         else:
#                             st.error("That doesn’t look like a valid email.")
#                             return  # keep dialog open
#                     # Either a valid email was processed, or user left it blank intentionally
#                     st.session_state["email_prompt_done"] = True
#                     st.rerun()
#             with c2:
#                 if st.button("Skip for now",width="stretch"):
#                     st.session_state["email_prompt_done"] = True
#                     st.rerun()
#         _dlg()

# # --- open dialog on first load
# open_email_dialog()

def build_yaml_zip(asset_dir: str) -> tuple[bytes, int]:
    """
    Create an in-memory ZIP archive containing all .yml/.yaml files under `asset_dir`.

    The directory structure relative to `asset_dir` is preserved inside the archive.

    Parameters
    ----------
    asset_dir : str | Path
        Root directory to search recursively for YAML files.

    Returns
    -------
    zip_bytes : bytes
        The full ZIP file as bytes (ready for download/saving).
    count : int
        Number of YAML files added to the archive.

    Raises
    ------
    FileNotFoundError
        If `asset_dir` does not exist.
    """
    base = Path(asset_dir)
    if not base.exists():
        raise FileNotFoundError(f"Asset directory not found: {base}")

    buf = io.BytesIO()
    count = 0
    # Use deflate compression for reasonable size/perf tradeoff
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for pattern in ("*.yml", "*.yaml"):
            for p in base.rglob(pattern):
                # Keep folder structure relative to the base dir
                zf.write(p, arcname=str(p.relative_to(base)))
                count += 1

    buf.seek(0)  # rewind buffer before reading
    return buf.read(), count


def clear_cache(keep: Iterable[str] = ()) -> None:
    """
    Clear Streamlit session state, optionally keeping specific keys.

    Parameters
    ----------
    keep : Iterable[str], optional
        Keys to *retain* in `st.session_state`. Useful for preserving auth,
        routing, or other sticky state between resets.

    Notes
    -----
    This mutates global Streamlit state; use sparingly.
    """
    keep_set = set(keep)
    # Copy keys to avoid mutating while iterating
    for key in list(st.session_state.keys()):
        if key not in keep_set:
            st.session_state.pop(key)


def safe_filename(name: str, ext: str) -> str:
    """
    Produce a filesystem-safe filename from `name` + `ext`.

    - Replaces sequences of forbidden characters with underscores.
    - Ensures the base name is non-empty (falls back to 'table').
    - Ensures `ext` starts with a '.'.

    Parameters
    ----------
    name : str
        Desired base filename (without extension).
    ext : str
        File extension (with or without a leading dot).

    Returns
    -------
    str
        A sanitized filename like 'my_table.csv'.
    """
    name = os.path.basename(name)  # Sanitize against path traversal
    base = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("._")
    if not base:
        base = "table"

    # Normalize extension: ensure a single leading dot if ext was provided
    ext = ext.strip()
    if ext and not ext.startswith("."):
        ext = f".{ext}"

    return f"{base}{ext}"


def normalize_col_name(s: str) -> str:
    """
    Normalize a user-provided column label to a snake_case identifier.

    Steps:
    - trim, collapse whitespace to single spaces, then replace spaces with '_'
    - lowercase
    - replace non [a-z0-9_] with '_'
    - collapse multiple underscores and trim leading/trailing underscores
    """
    # Use a distinct local variable to avoid shadowing/redefining the parameter
    s_clean: str = re.sub(r"\s+", " ", s.strip()).replace(" ", "_").lower()
    s_clean = re.sub(r"[^a-z0-9_]", "_", s_clean)
    s_clean = re.sub(r"_+", "_", s_clean).strip("_")
    return s_clean


def validate_column_names(
    orig_cols: list[str], new_cols: list[str], ignored: list[bool]
) -> list[str]:
    """
    Validate edited column names against a strict snake_case schema.

    Rules enforced:
    - Empty names (after normalization) are not allowed.
    - Names must be unique (after normalization).
    - Names must start with a letter and only contain [a-z0-9_].

    Parameters
    ----------
    orig_cols : list[str]
        Original column names (for reference).
    new_cols : list[str]
        Proposed edited names (one-for-one with `orig_cols`).
    ignored : list[bool]
        Flags indicating which columns are being dropped/ignored.

    Returns
    -------
    list[str]
        A list of human-readable error messages. Empty list means valid.

    Notes
    -----
    This function normalizes `new_cols` internally with `normalize_col_name`
    before validation to ensure checks match how names will be stored.
    """
    errors: list[str] = []

    # Keep pairs for non-ignored columns; normalize new names for validation
    kept_pairs = [
        (o, normalize_col_name(n))
        for o, n, ig in zip(orig_cols, new_cols, ignored)
        if not ig
    ]
    new_only = [n for _, n in kept_pairs]

    # 1) Empty check
    if any(n == "" for n in new_only):
        errors.append("Column names cannot be empty after normalization.")

    # 2) Uniqueness check
    if len(new_only) != len(set(new_only)):
        errors.append("Column names must be unique (after normalization).")

    # 3) Identifier pattern check
    for n in new_only:
        if not re.match(r"^[a-z][a-z0-9_]*$", n):
            errors.append(
                f"Invalid column name: '{n}'. Must start with a letter and contain only a–z, 0–9, _."
            )
            break  # One example is enough; avoid spamming errors

    return errors


def get_secret(name: str, fallback: str | None = None) -> str | None:
    """
    Return a secret value by checking, in order:
    1) os.environ
    2) st.secrets (if available)
    3) fallback

    Parameters
    ----------
    name : str
        Environment / secret key to look up.
    fallback : str | None
        Value to return if not found.

    Returns
    -------
    str | None
    """
    val = os.getenv(name)
    if not val:
        # st.secrets may not exist outside Streamlit runtime; guard it
        if hasattr(st, "secrets"):
            try:
                # st.secrets behaves like a Mapping; .get() may return None
                val = st.secrets.get(name)  # type: ignore[attr-defined]
            except Exception:
                val = None
    return val or fallback


def mask(s: str | None, *, show_last: int = 0) -> str:
    """
    Mask a secret for display.

    Parameters
    ----------
    s : str | None
        The secret value.
    show_last : int
        If > 0, reveal the last N characters (e.g., ...abcd).

    Returns
    -------
    str
    """
    if not s:
        return "(none)"
    if show_last > 0 and len(s) > show_last:
        return "••••••••" + s[-show_last:]
    return "••••••••"


def save_env(env_map: Mapping[str, Optional[str]], env_file: str = ".env") -> None:
    """
    Persist non-empty environment variables to both the running process and a .env file.

    Behavior
    --------
    - Sets os.environ[key] = value for each non-empty mapping entry.
    - Upserts to the .env file using KEY="value" with inner quotes escaped.
      (Will replace existing keys rather than appending duplicates.)

    Parameters
    ----------
    env_map : Mapping[str, Optional[str]]
        Keys and values to persist. None values are ignored.
    env_file : str
        Path to the .env file (defaults to ".env").
    """
    env_path = Path(env_file)
    existing: dict[str, str] = {}

    # Load existing .env if present
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.strip().startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()

    # Apply updates in-memory and to process env
    for k, v in env_map.items():
        if v is None:
            continue
        val_str = str(v)
        os.environ[k] = val_str
        # Store quoted value; escape internal double-quotes
        safe_val = '"' + val_str.replace('"', r'\"') + '"'
        existing[k] = safe_val

    # Write back (sorted for stability)
    lines = [f"{k}={existing[k]}" for k in sorted(existing)]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ------------------------------ File parsing ------------------------------

def _read_bytes_to_df_core(filename: str, data: bytes) -> tuple[pd.DataFrame, str]:
    """
    Core helper to read CSV/Excel files from bytes into a DataFrame.

    This private function encapsulates the common logic for reading different
    file formats from bytes, used by both read_bytes_to_df and read_file_to_df.

    Parameters
    ----------
    filename : str
        Original filename (used to infer type).
    data : bytes
        File content.

    Returns
    -------
    (df, note) : tuple[pandas.DataFrame, str]
        DataFrame plus a note describing how it was read.

    Raises
    ------
    ValueError
        If the file type is unsupported.
    """
    buf = io.BytesIO(data)
    lower = filename.lower()

    if lower.endswith(".csv"):
        try:
            buf.seek(0)
            df = pd.read_csv(buf)
            note = ""
        except UnicodeDecodeError:
            buf.seek(0)
            df = pd.read_csv(buf, encoding="latin-1")
            note = "Read with latin-1 encoding."
        return df, note

    if lower.endswith((".xls", ".xlsx")):
        buf.seek(0)
        # Let pandas choose engine (openpyxl for xlsx, xlrd for old xls if installed)
        xls = pd.ExcelFile(buf)
        first_sheet = xls.sheet_names[0]
        df = xls.parse(first_sheet)
        note = f"Read Excel first sheet: '{first_sheet}'."
        return df, note

    raise ValueError("Unsupported file type.")


def read_bytes_to_df(filename: str, data: bytes) -> tuple[pd.DataFrame, str]:
    """
    Read a CSV or Excel file from raw bytes into a DataFrame.

    Parameters
    ----------
    filename : str
        Original filename (used to infer type).
    data : bytes
        File content.

    Returns
    -------
    (df, note) : tuple[pandas.DataFrame, str]
        DataFrame plus a note describing how it was read.

    Raises
    ------
    ValueError
        If the file type is unsupported.
    """
    return _read_bytes_to_df_core(filename, data)


# ------------------------------ Naming helpers ------------------------------

def standardize_table_name(raw: str) -> str:
    """
    Convert an arbitrary table label to a strict snake_case identifier:

    - trim, collapse whitespace
    - spaces -> underscores
    - lowercase
    - replace non [a-z0-9_] with '_'
    - collapse multiple underscores and trim edges
    """
    s: str = re.sub(r"\s+", " ", raw.strip())
    s = s.replace(" ", "_").lower()
    s = re.sub(r"[^a-z0-9_]", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def validate_table_name(name: str) -> tuple[bool, str]:
    """
    Validate a standardized table name.

    Rules
    -----
    - Non-empty
    - <= 63 chars
    - ^[a-z][a-z0-9_]*$

    Returns
    -------
    (is_valid, message) : tuple[bool, str]
        message is empty when valid.
    """
    if not name:
        return False, "Name cannot be empty."
    if len(name) > 63:
        return False, "Max 63 characters."
    if not re.match(r"^[a-z][a-z0-9_]*$", name):
        return (
            False,
            "Must start with a letter and contain only lowercase letters, digits, and underscores.",
        )
    return True, ""


def sizeof_mb(bytes_size: int | float) -> float:
    """Return size in MiB (rounded to 2 decimals).

    Accepts integer or float byte counts and returns a float MiB value.
    """
    size_mib: float = round(float(bytes_size) / (1024 * 1024), 2)
    return size_mib


def clean_table_name(name: str) -> str:
    """
    Produce a display-friendly table name from a filename.

    - strips extension
    - trims whitespace
    - collapses internal whitespace to single underscores
    - preserves original case (for UI display)

    Note: this is for UI defaults; persist with `standardize_table_name` before saving.
    """
    # Preserve parent path(s) while cleaning only the basename
    name_str = name
    # Normalize separators to forward slash for stable behavior across OSes
    normalized = name_str.replace("\\", "/")
    parts = normalized.split("/")
    dir_part = "/".join(parts[:-1]) if len(parts) > 1 else ""
    filename = parts[-1]
    stem: str = os.path.splitext(filename)[0].strip()
    stem = re.sub(r"\s+", "_", stem)
    return f"{dir_part}/{stem}" if dir_part else stem
    return stem


# ------------------------------ DataFrame utilities ------------------------------

def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize DataFrame columns to snake_case and ensure uniqueness.

    - trim, collapse whitespace, spaces->'_', lowercase
    - if duplicates result after normalization, suffix with _1, _2, ...

    Returns
    -------
    pandas.DataFrame
        A shallow copy with standardized, unique column names.
    """
    def normalize(col: Any) -> str:
        c = re.sub(r"\s+", " ", str(col).strip())
        c = c.replace(" ", "_").lower()
        c = re.sub(r"[^a-z0-9_]", "_", c)
        c = re.sub(r"_+", "_", c).strip("_")
        if not c:
            c = "col"
        return c

    new_cols: list[str] = []
    seen: dict[str, int] = {}

    for c in df.columns:
        base = normalize(c)
        # Initialize counter for this base if missing
        seen.setdefault(base, 0)

        if seen[base] == 0 and base not in new_cols:
            new = base
        else:
            # Ensure uniqueness by suffixing with an incrementing number
            n = seen[base]
            if n == 0:
                n = 1
            new = f"{base}_{n}"
            # Bump until unique
            while new in new_cols:
                n += 1
                new = f"{base}_{n}"
            seen[base] = n

        new_cols.append(new)
        seen[base] += 1

    out: pd.DataFrame = df.copy()
    out.columns = new_cols
    return out

# ------------------------------ File → DataFrame ------------------------------


def read_file_to_df(uploaded_file) -> Tuple[pd.DataFrame, str]:
    """
    Read an uploaded CSV/XLS/XLSX into a DataFrame.

    Returns
    -------
    (df, note) : tuple[pd.DataFrame, str]
        `note` explains any special handling (fallback encoding or selected sheet).

    Raises
    ------
    ValueError
        If `uploaded_file` is missing or type is unsupported.
    """
    if not uploaded_file or not hasattr(uploaded_file, "name") or not hasattr(uploaded_file, "read"):
        raise ValueError("Invalid uploaded file object.")

    return _read_bytes_to_df_core(uploaded_file.name, uploaded_file.read())


# ------------------------------ State: tables ------------------------------

def ensure_unique_name(base: str, existing: Dict[str, pd.DataFrame]) -> str:
    """
    Ensure `base` is unique within `existing` table names by suffixing _2, _3, ...

    Parameters
    ----------
    base : str
        Desired table name.
    existing : Dict[str, pd.DataFrame]
        Current mapping of table_name -> table_data.

    Returns
    -------
    str
        A unique name not present in `existing`.
    """
    name = base
    i = 2
    while name in existing:
        name = f"{base}_{i}"
        i += 1
    return name


def add_table_to_state(name: str, df: pd.DataFrame, meta: dict) -> None:
    """
    Add (df, meta) to st.session_state['tables'] under `name`.
    Creates the container if missing.
    """
    st.session_state.setdefault("tables", {})
    st.session_state["tables"][name] = {"df": df, "meta": meta}


def rename_table_in_state(old: str, new: str) -> str | None:
    """
    Rename a table key in st.session_state['tables'].

    If `old` doesn't exist, no-op.
    If `new` already exists, it will be overwritten (keep your own guard if needed).

    Returns
    -------
    str | None
        The final new key if rename occurred; otherwise None.
    """
    tables = st.session_state.get("tables")
    if not tables or old not in tables:
        return None
    tables[new] = tables.pop(old)
    return new


def delete_table_in_state(name: str) -> bool:
    """
    Delete a table by name from st.session_state['tables'].

    Returns
    -------
    bool
        True if the table existed and was deleted, False otherwise.
    """
    tables = st.session_state.get("tables")
    if tables and name in tables:
        del tables[name]
        return True
    return False


# ------------------------------ Download helpers ------------------------------

def download_bytes_for_df(df: pd.DataFrame, kind: str) -> bytes:
    """
    Serialize a DataFrame to downloadable bytes.

    Parameters
    ----------
    df : pd.DataFrame
        Data to serialize.
    kind : {"csv","xlsx"}
        Output format.

    Returns
    -------
    bytes
        Encoded file content.

    Raises
    ------
    ValueError
        If `kind` is unknown.
    """
    if kind == "csv":
        return df.to_csv(index=False).encode("utf-8")
    if kind == "xlsx":
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="data")
        out.seek(0)
        return out.read()
    raise ValueError("Unknown download kind. Use 'csv' or 'xlsx'.")


# ------------------------------ Secrets (env) ------------------------------

def _get_secret_env(name: str) -> str | None:
    """
    Convenience getter for environment-like secrets:
    1) os.environ[name]
    2) st.secrets[name] (if available)

    Returns
    -------
    str | None
    """
    val = os.getenv(name)
    if not val and hasattr(st, "secrets"):
        try:
            val = st.secrets.get(name)  # type: ignore[attr-defined]
        except Exception:
            val = None
    return val

# Helpers

# ------------------------------ Name helpers ------------------------------


def _normalized_table_name(raw: str) -> str:
    """
    Normalize table names using the strongest available normalizer.
    Falls back to `normalize_col_name` if `standardize_table_name` is not defined.
    """
    if "standardize_table_name" in globals():
        return standardize_table_name(raw)  # type: ignore[name-defined]
    return normalize_col_name(raw)          # type: ignore[name-defined]


def _csv_path_for(name: str, MODIFIED_DIR) -> Path:
    """
    Return the output CSV path for a given table name within MODIFIED_DIR.
    Requires `MODIFIED_DIR` and `safe_filename` to be defined globally.
    """
    return MODIFIED_DIR / safe_filename(name, ".csv")  # type: ignore[name-defined]


# ------------------------------ UI callbacks ------------------------------

def _on_select_change() -> None:
    """
    When the source select changes, copy it into the final name
    unless the user has already started editing manually.
    """
    sel = st.session_state.get("main_modify_select")
    if not st.session_state.get("final_name_user_edited", False):
        st.session_state["main_modify_final_name"] = sel or ""


def _on_name_edit() -> None:
    """
    Mark that the user edited the name; prevents auto-sync from `_on_select_change`.
    """
    st.session_state["final_name_user_edited"] = True


# ------------------------------ LLM readiness ------------------------------

def llm_ready_check() -> tuple[bool, str]:
    """
    Validate provider-specific credentials based on st.session_state['llm_choice'].

    Returns
    -------
    (ok, message) : tuple[bool, str]
        ok=True if credentials are present; message contains guidance if not.
    """
    provider = (st.session_state.get("llm_choice") or "openai").strip().lower()

    if provider == "openai":
        key = _get_secret_env("OPENAI_API_KEY")  # type: ignore[name-defined]
        if not key:
            return False, "OpenAI key missing. Please set **OPENAI_API_KEY** in the sidebar."
        return True, ""

    if provider in {"azure-openai", "azure_openai", "azure"}:
        required = {
            "AZURE_OPENAI_API_KEY": _get_secret_env("AZURE_OPENAI_API_KEY"),  # type: ignore[name-defined]
            "AZURE_OPENAI_ENDPOINT": _get_secret_env("AZURE_OPENAI_ENDPOINT"),  # type: ignore[name-defined]
            "LLM_PROVIDER": _get_secret_env("LLM_PROVIDER"),  # type: ignore[name-defined]
            "OPENAI_API_VERSION": _get_secret_env("OPENAI_API_VERSION"),  # type: ignore[name-defined]
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            return False, "Azure OpenAI config missing: " + ", ".join(missing) + ". Set them in the sidebar."
        return True, ""

    if provider in {"google_genai", "google"}:
        key = _get_secret_env("GEMINI_API_KEY") or _get_secret_env("GOOGLE_API_KEY")  # type: ignore[name-defined]
        if not key:
            return False, "Gemini key missing. Please set **GEMINI_API_KEY** (or GOOGLE_API_KEY) in the sidebar."
        return True, ""

    if provider == "anthropic":
        key = _get_secret_env("ANTHROPIC_API_KEY")  # type: ignore[name-defined]
        if not key:
            return False, "Anthropic key missing. Please set **ANTHROPIC_API_KEY** in the sidebar."
        return True, ""

    return False, f"Unknown provider '{provider}'."


# ------------------------------ Object → dict ------------------------------

def link_to_dict(x: object) -> dict[str, Any]:
    """
    Convert dataclass / Pydantic / namedtuple / simple objects to a dict,
    filtering out private attrs where applicable. Falls back to {'value': str(x)}.
    """
    # If the incoming object is a plain mapping (dict-like), return a copy
    # with private keys filtered out. This ensures callers can pass simple
    # dictionaries to the normalizer without losing structure.
    if isinstance(x, Mapping):
        return {k: v for k, v in x.items() if not str(k).startswith("_")}

    # Only pass instances to `asdict`; dataclass `type` objects are not valid.
    if is_dataclass(x) and not isinstance(x, type):
        return asdict(x)
    if hasattr(x, "model_dump"):
        try:
            return x.model_dump()  # pydantic v2
        except Exception:
            pass
    if hasattr(x, "dict"):
        try:
            return x.dict()  # pydantic v1
        except Exception:
            pass
    if hasattr(x, "_asdict"):
        try:
            return x._asdict()  # namedtuple
        except Exception:
            pass
    if hasattr(x, "__dict__") and isinstance(getattr(x, "__dict__", None), dict):
        return {k: v for k, v in x.__dict__.items() if not str(k).startswith("_")}
    try:
        return {k: v for k, v in vars(x).items() if not str(k).startswith("_")}
    except Exception:
        res = {"value": str(x)}
        return res


# ------------------------------ Links → DataFrame ------------------------------

def predicted_links_to_df(links: Optional[Sequence[object]]) -> pd.DataFrame:
    """
    Normalize a collection of link-like objects to rows in a DataFrame, with
    preferred column ordering when available. Handles composite keys.
    """
    if not links:
        return pd.DataFrame()

    Mapping[str, Any] | object
    rows: list[dict[str, Any]] = [link_to_dict(x) for x in links]
    df: pd.DataFrame = pd.DataFrame(rows)

    if df.empty:
        return df

    # --- Handle composite keys and ensure column consistency ---

    # Ensure a `from_columns`/`to_columns` list exists for each row.
    # - If `from_columns` already exists and is a list, keep it.
    # - Else if `from_column` exists (string), convert to a single-element list.
    # - Else use an empty list.
    def _ensure_cols(series_name: str, legacy_name: str) -> None:
        """
        Ensure column `series_name` exists and contains lists of strings.

        - If `series_name` exists and is a list, coerce elements to str.
        - If missing but `legacy_name` exists, create a list from the legacy string value.
        - Otherwise create an empty list per row.
        """
        def _safe_str(v: Any) -> str:
            if isinstance(v, float) and v.is_integer():
                return str(int(v))
            return str(v)

        def _coerce_to_str_list(value: Any, legacy_value: Any) -> list[str]:
            # Value present and is list-like
            if isinstance(value, list):
                # If list has items, coerce each to str; otherwise fall back to legacy
                if len(value) > 0:
                    return [
                        _safe_str(x) for x in value if x is not None
                    ]
                # Otherwise try legacy
                if isinstance(legacy_value, (str, int, float)):
                    return [str(legacy_value)]
                return []
            # Treat pandas NA / numpy.nan as missing
            if pd.isna(value):
                value = None
            if pd.isna(legacy_value):
                legacy_value = None

            # Value present as a single scalar string-like or numeric
            if isinstance(value, (str, int, float)):
                return [_safe_str(value)]

            # Use legacy string or numeric value if provided
            if isinstance(legacy_value, (str, int, float)):
                return [_safe_str(legacy_value)]

            return []

        # Ensure column exists
        if series_name not in df.columns:
            if legacy_name in df.columns:
                def _from_legacy_to_list(x: Any) -> list[str]:
                    if isinstance(x, (str, int, float)):
                        return [_safe_str(x)]
                    return []
                df[series_name] = df[legacy_name].apply(_from_legacy_to_list)
            else:
                df[series_name] = pd.Series([[] for _ in range(len(df))], index=df.index)
        else:
            # Column exists; coerce to lists of strings using legacy if present
            if legacy_name in df.columns:
                df[series_name] = [
                    _coerce_to_str_list(v, lv)
                    for v, lv in zip(
                        df.get(series_name, pd.Series([None] * len(df))),
                        df.get(legacy_name, pd.Series([None] * len(df))),
                    )
                ]
            else:
                df[series_name] = [
                    _coerce_to_str_list(v, None) for v in df.get(series_name, pd.Series([None] * len(df)))
                ]

    _ensure_cols("from_columns", "from_column")
    _ensure_cols("to_columns", "to_column")

    # Ensure explicit list types for any remaining non-list values
    df["from_columns"] = df["from_columns"].apply(lambda x: x if isinstance(x, list) else [])
    df["to_columns"] = df["to_columns"].apply(lambda x: x if isinstance(x, list) else [])

    # Add `is_composite` flag
    # Convert to plain Python bools rather than numpy.bool_ so callers can
    # compare with `is True` where appropriate in tests.
    df["is_composite"] = df["from_columns"].apply(lambda x: bool(len(x) > 1)).astype(object)

    # Create user-friendly display strings for single and composite keys
    def format_column_display(cols: Sequence[Any]) -> str:
        if not cols:
            return ""
        # Ensure all elements are strings for display
        cols_str = [str(c) for c in cols]
        if len(cols_str) > 1:
            return f"({', '.join(cols_str)})"
        return cols_str[0]

    # Overwrite/create `from_column` and `to_column` for display purposes in graph/table
    df["from_column"] = df["from_columns"].apply(format_column_display)
    df["to_column"] = df["to_columns"].apply(format_column_display)

    # --- Reorder columns for display ---
    preferred: list[str] = [
        "from_dataset", "from_column", "to_dataset", "to_column",
        "is_composite", "intersect_count", "intersect_ratio_from_col", "intersect_ratio_to_col", "accuracy",
    ]

    existing_preferred: list[str] = [c for c in preferred if c in df.columns]
    # Include all other columns, but put original list-based columns at the end
    other_cols: list[str] = sorted([
        c for c in df.columns
        if c not in existing_preferred and c not in {"from_columns", "to_columns"}
    ])
    final_cols: list[str] = existing_preferred + other_cols + ["from_columns", "to_columns"]
    # Filter to only columns that actually exist in the dataframe
    final_cols = [c for c in final_cols if c in df.columns]

    return df[final_cols]

# ---------- new: plotly network (tables as nodes) ----------


def plotly_table_graph(
    df: pd.DataFrame,
    *,
    seed: int = 42,
    k: float = 0.8,
    max_individual_edge_traces: int = 200,
    node_min_size: int = 14,
    node_size_per_degree: int = 3,
    node_fill: str = "#F3E8FF",
    node_stroke: str = "#8B5CF6",
    edge_color: str = "#8B5CF6",
    composite_edge_color: str = "#4E195E",
    edge_min_width: float = 1.0,
    edge_width_scale: float = 4.0,
) -> go.Figure:
    """
    Build a Plotly figure showing dataset→dataset links from a row-wise edges table.
    Handles both single and composite links.

    Expected columns in `df`:
      - from_dataset, to_dataset (str)
      - from_column, to_column (str)  — used to label aggregated edges
      - is_composite (bool)           — used to style composite links
      - accuracy (float, optional)    — used to weight edge width (mean)
      - intersect_count (int, optional) — included in hover (summed)

    Parameters
    ----------
    seed : int
        Random seed for spring_layout stability.
    k : float
        Optimal distance between nodes in spring_layout (higher => more spread).
    max_individual_edge_traces : int
        If number of edges exceeds this, fall back to a single edge trace
        (faster for very dense graphs, but removes per-edge width).
    node_* : styling
        Node size/color styling knobs.
    edge_* : styling
        Edge color/width styling knobs.
    composite_edge_color : str
        Color for composite link edges.

    Returns
    -------
    go.Figure
    """
    # --- Early outs & validation ---
    if df.empty:
        return go.Figure()

    required = {"from_dataset", "to_dataset", "from_column", "to_column", "is_composite"}
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    # --- Build DiGraph; aggregate multiple (src,dst) rows into one edge payload ---
    G = nx.DiGraph()
    for _, r in df.iterrows():
        src = r["from_dataset"]
        dst = r["to_dataset"]
        G.add_node(src)
        G.add_node(dst)

        label = f"{r['from_column']} → {r['to_column']}"
        acc = float(r.get("accuracy", 1.0) or 1.0)
        cnt = int(r.get("intersect_count", 0) or 0)
        is_composite = bool(r.get("is_composite", False))

        if G.has_edge(src, dst):
            G[src][dst]["labels"].append(label)
            G[src][dst]["accs"].append(acc)
            G[src][dst]["counts"].append(cnt)
            # If any underlying link is composite, the aggregated edge is composite
            G[src][dst]["is_composite"] = G[src][dst].get("is_composite", False) or is_composite
        else:
            G.add_edge(src, dst, labels=[label], accs=[acc], counts=[cnt], is_composite=is_composite)

    # --- Layout ---
    pos = nx.spring_layout(G, seed=seed, k=k)

    # --- Build node trace ---
    node_x, node_y, node_text, node_deg, node_labels = [], [], [], [], []
    for n in G.nodes():
        x, y = pos[n]
        node_x.append(x)
        node_y.append(y)
        indeg = G.in_degree(n)
        outdeg = G.out_degree(n)
        node_text.append(f"<b>{n}</b><br>in: {indeg} • out: {outdeg}")
        node_deg.append(indeg + outdeg)
        node_labels.append(str(n))

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        text=node_labels,
        textposition="bottom center",
        hovertext=node_text,
        hoverinfo="text",
        marker=dict(
            size=[node_min_size + node_size_per_degree * d for d in node_deg],
            color=node_fill,
            line=dict(width=2, color=node_stroke),
        ),
        showlegend=False,
    )

    # --- Build edges ---
    def edge_hover(u: str, v: str, data: Mapping[str, Any]) -> str:
        link_type = "<b>Composite Link</b><br>" if data.get("is_composite") else ""
        pairs = ", ".join(data["labels"])
        n_sum = sum(int(x or 0) for x in data["counts"])
        acc_mean = sum(data["accs"]) / max(1, len(data["accs"]))
        return (
            f"{link_type}<b>{u}</b> → <b>{v}</b><br>"
            f"Columns: {pairs}<br>"
            f"Mean acc: {acc_mean:.2f} • Sum n: {n_sum}"
        )

    edge_label_x, edge_label_y, edge_label_text = [], [], []
    edge_traces: list[go.Scatter] = []

    edges_list: list[Tuple[str, str, Mapping[str, Any]]] = list(G.edges(data=True))
    use_single_trace = len(edges_list) > max_individual_edge_traces

    if use_single_trace:
        # Fast path: two traces (single, composite) with constant width
        single_x, single_y, single_hover = [], [], []
        comp_x, comp_y, comp_hover = [], [], []

        for u, v, data in edges_list:
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            hover_text = edge_hover(u, v, data)

            if data.get("is_composite"):
                comp_x += [x0, x1, None]
                comp_y += [y0, y1, None]
                comp_hover.append(hover_text)
            else:
                single_x += [x0, x1, None]
                single_y += [y0, y1, None]
                single_hover.append(hover_text)

            # Midpoint label text (common for both)
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            edge_label_x.append(mx)
            edge_label_y.append(my)
            if len(data["labels"]) == 1:
                edge_label_text.append(data["labels"][0])
            else:
                edge_label_text.append(f"{data['labels'][0]} (+{len(data['labels']) - 1} more)")
        if single_x:
            edge_traces.append(go.Scatter(
                x=single_x, y=single_y, mode="lines", hoverinfo="text", text=single_hover,
                line=dict(width=max(edge_min_width, 1.5), color=edge_color),
                opacity=0.85, showlegend=False
            ))
        if comp_x:
            edge_traces.append(go.Scatter(
                x=comp_x, y=comp_y, mode="lines", hoverinfo="text", text=comp_hover,
                line=dict(width=max(edge_min_width, 1.5), color=composite_edge_color, dash="dash"),
                opacity=0.85, showlegend=False
            ))
    else:
        # Accurate path: one trace per edge to vary width by mean accuracy
        for u, v, data in edges_list:
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            acc_mean = sum(data["accs"]) / max(1, len(data["accs"]))
            width = max(edge_min_width, acc_mean * edge_width_scale)
            is_composite = data.get("is_composite", False)

            line_style = dict(
                width=width,
                color=composite_edge_color if is_composite else edge_color,
                dash="dash" if is_composite else "solid",
            )

            edge_traces.append(
                go.Scatter(
                    x=[x0, x1], y=[y0, y1],
                    mode="lines",
                    hoverinfo="text",
                    text=[edge_hover(u, v, data)],
                    line=line_style,
                    opacity=0.85,
                    showlegend=False,
                )
            )

            # Midpoint label
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            edge_label_x.append(mx)
            edge_label_y.append(my)
            if len(data["labels"]) == 1:
                edge_label_text.append(data["labels"][0])
            else:
                edge_label_text.append(f"{data['labels'][0]} (+{len(data['labels']) - 1} more)")

    # Edge labels as a single text layer
    edge_label_trace = go.Scatter(
        x=edge_label_x, y=edge_label_y,
        mode="text",
        text=edge_label_text,
        textposition="middle center",
        textfont=dict(size=10),
        hoverinfo="skip",
        showlegend=False,
    )

    # --- Compose figure ---
    fig = go.Figure(data=[*edge_traces, edge_label_trace, node_trace])
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=False),
        plot_bgcolor="white",
        hoverlabel=dict(bgcolor="white"),
        showlegend=False,
    )
    return fig
# ---------- main render: 2 tabs (Graph / Table) ----------


# ------------------------------ UI: Graph + Table ------------------------------

def show_links_graph_and_table(links) -> None:
    """
    Render a two-tab view: a Plotly semantic graph and a tabular view of links.
    """
    df = predicted_links_to_df(links)
    tab_graph, tab_table = st.tabs(["📈 Graph", "📑 Table"])

    with tab_graph:
        if df.empty:
            st.info("No links to display.")
        else:
            st.subheader("Semantic Graph")
            try:
                fig = plotly_table_graph(df)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Couldn't render graph: {e}")

    with tab_table:
        if df.empty:
            st.info("No links to display.")
        else:
            st.subheader("Semantic Table")
            st.dataframe(df, use_container_width=True, hide_index=True)


# ------------------------------ Download helpers ------------------------------

# def resolve_commons_url(url: str) -> str:
#     """
#     Convert a Commons 'File:' page to a direct file redirector URL.
#     If already direct, return as-is.
#     """
#     if "commons.wikimedia.org/wiki/File:" in url:
#         m = re.search(r"/wiki/File:(.+)$", url)
#         if not m:
#             return url
#         filename = unquote(m.group(1))
#         # Special:FilePath redirects to the current best URL for the asset
#         return f"https://commons.wikimedia.org/wiki/Special:FilePath/{filename}"
#     return url


# def _sanitize_filename(name: str) -> str:
#     """
#     Make a filesystem-safe filename while preserving extension if present.
#     """
#     name = name.strip().replace("\\", "/").split("/")[-1]
#     # Split extension if any
#     stem, dot, ext = name.partition(".")
#     safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._") or "download"
#     safe_ext = re.sub(r"[^A-Za-z0-9]+", "", ext)
#     return f"{safe_stem}.{safe_ext}" if safe_ext else safe_stem


# def _ext_from_ctype(ctype: str) -> str:
#     """
#     Best-effort extension guess from an image content-type.
#     """
#     ctype = (ctype or "").lower()
#     mapping = {
#         "image/jpeg": "jpg",
#         "image/jpg": "jpg",
#         "image/png": "png",
#         "image/webp": "webp",
#         "image/gif": "gif",
#         "image/svg+xml": "svg",
#         "image/avif": "avif",
#         "image/bmp": "bmp",
#         "image/tiff": "tiff",
#     }
#     return mapping.get(ctype, "")


# def suggested_filename(url: str, resp: requests.Response) -> str:
#     """
#     Choose a filename from Content-Disposition (if present) or the URL path.
#     Fall back to a content-type-based extension when needed.
#     """
#     # 1) Content-Disposition
#     cd = resp.headers.get("content-disposition", "")
#     m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd, flags=re.I)
#     if m:
#         return _sanitize_filename(unquote(m.group(1)))

#     # 2) URL path
#     name = os.path.basename(urlparse(resp.url or url).path)
#     name = _sanitize_filename(unquote(name))
#     if "." in name:
#         return name

#     # 3) Extension by content-type
#     ext = _ext_from_ctype(resp.headers.get("Content-Type", ""))
#     return f"{name}.{ext}" if ext else (name or "downloaded_image")


# def download_image(source_url: str, save_folder: str | Path = "images", *, max_bytes: int = 50 * 1024 * 1024) -> str:
#     """
#     Download an image (supports Commons 'File:' pages) to `save_folder`.

#     Parameters
#     ----------
#     source_url : str
#         A direct image URL or a https://commons.wikimedia.org/wiki/File:... page URL.
#     save_folder : str | Path
#         Destination folder (created if missing).
#     max_bytes : int
#         Safety cap on download size (default 50 MiB).

#     Returns
#     -------
#     str
#         Full path to the downloaded file.

#     Raises
#     ------
#     RuntimeError : for HTTP or content-type failures.
#     """
#     save_dir = Path(save_folder)
#     save_dir.mkdir(parents=True, exist_ok=True)

#     # Resolve Commons page → Special:FilePath redirector
#     download_url = resolve_commons_url(source_url)

#     # Browser-y headers avoids some 403/anti-bot configs
#     session = requests.Session()
#     session.headers.update({
#         "User-Agent": (
#             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#             "AppleWebKit/537.36 (KHTML, like Gecko) "
#             "Chrome/124.0 Safari/537.36"
#         ),
#         "Referer": "https://commons.wikimedia.org/",
#         "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
#     })

#     with session.get(download_url, stream=True, timeout=30, allow_redirects=True) as r:
#         if r.status_code != 200:
#             raise RuntimeError(f"Failed to download image. Status code: {r.status_code}")

#         ctype = (r.headers.get("Content-Type") or "").lower()
#         if not ctype.startswith("image/"):
#             raise RuntimeError(f"URL did not resolve to an image (Content-Type: {ctype or 'unknown'}).")

#         fname = suggested_filename(download_url, r)
#         dest_path = save_dir / fname

#         # Avoid overwriting existing files: append numeric suffix if needed
#         if dest_path.exists():
#             stem = dest_path.stem
#             ext = dest_path.suffix
#             i = 2
#             while True:
#                 candidate = save_dir / f"{stem}_{i}{ext}"
#                 if not candidate.exists():
#                     dest_path = candidate
#                     break
#                 i += 1

#         # Stream to disk with a size cap
#         total = 0
#         tmp_path = dest_path.with_suffix(dest_path.suffix + ".part")
#         with open(tmp_path, "wb") as f:
#             for chunk in r.iter_content(chunk_size=8192):
#                 if not chunk:
#                     continue
#                 total += len(chunk)
#                 if total > max_bytes:
#                     f.close()
#                     tmp_path.unlink(missing_ok=True)
#                     raise RuntimeError("Download exceeded size limit.")
#                 f.write(chunk)

#         tmp_path.rename(dest_path)
#         return str(dest_path)


# ------------------------------ Simple router ------------------------------

def go_semantic_all() -> None:
    """
    Route to the full semantic view.
    """
    st.session_state["route"] = "semantic_all"
    st.rerun()


def go_home() -> None:
    """
    Route to the home view.
    """
    st.session_state["route"] = "home"
    st.rerun()
