import logging
import streamlit as st
import requests
import json
from config import settings

# --- Configuration ---
# We'll attempt to discover a reachable backend host, preferring localhost, then 127.0.0.1,
# then whatever is configured in settings.HOST. This handles the common mistake where the
# server is bound to 0.0.0.0 but the client tries to connect to it.
DEFAULT_HOST_TRY_LIST = ["localhost", "127.0.0.1", settings.HOST]
logger = logging.getLogger(__name__)

def find_reachable_host(hosts: list[str], port: int, timeout: float = 1.0) -> str | None:
    """
    Try a list of hosts and return the first one that responds to a GET on the root path.
    Returns the host (string) if reachable, or None if none succeed.
    """
    for host in hosts:
        try:
            url = f"http://{host}:{port}/"
            r = requests.get(url, timeout=timeout)
            if r.status_code == 200:
                logger.debug("Found reachable backend at %s", url)
                return host
        except requests.RequestException:
            logger.debug("Host %s is not reachable (timeout or connection error)", host)
            continue
    return None

def check_hosts_status(hosts: list[str], port: int, timeout: float = 0.8) -> list[dict]:
    """Return reachability status for each host.
    Each entry is {'host': host, 'url': url, 'ok': bool, 'status_code': code or None}
    """
    results = []
    for host in hosts:
        url = f"http://{host}:{port}/"
        try:
            r = requests.get(url, timeout=timeout)
            results.append({"host": host, "url": url, "ok": r.status_code == 200, "status_code": r.status_code})
        except requests.RequestException:
            results.append({"host": host, "url": url, "ok": False, "status_code": None})
    return results

# Attempt to auto-detect a reachable backend host on startup. This is a best-effort check.
detected_host = find_reachable_host(DEFAULT_HOST_TRY_LIST, settings.PORT)
client_host = detected_host if detected_host else ("localhost" if settings.HOST == "0.0.0.0" else settings.HOST)
BACKEND_URL = f"http://{client_host}:{settings.PORT}"
API_URL = f"{BACKEND_URL}/v1/query"
INGEST_URL = f"{BACKEND_URL}/v1/ingest"

st.set_page_config(
    page_title="Financial-Land AI",
    layout="wide",
    initial_sidebar_state="expanded"
)

## --- Sidebar: Document Ingestion ---
with st.sidebar:
    st.header("Document Ingestion")
    uploaded_file = st.file_uploader("Upload Financial Document (PDF/Image)", type=["pdf", "png", "jpg", "jpeg"])
    
    if st.button("Process Document for RAG Index"):
        if uploaded_file is not None:
            # Placeholder for actual file upload/ingestion logic
            try:
                # In a real app: file = uploaded_file.read(); requests.post(INGEST_URL, files={'file': file})
                st.success("Document uploaded and ingestion pipeline started.")
            except requests.RequestException as e:
                logger.exception("Failed to start ingestion: %s", e)
                st.error("Failed to start ingestion. Check backend logs.")
            # In a real app: file = uploaded_file.read(); requests.post(INGEST_URL, files={'file': file})
        else:
            st.warning("Please upload a file first.")

st.title("Financial-Land AI: Intelligence Platform")
st.markdown("Ask complex financial questions based on market data and proprietary documents.")

# Show the detected backend URL and allow re-detection
if detected_host:
    st.success(f"Using backend: {BACKEND_URL} (detected)")
else:
    st.warning(f"Using backend: {BACKEND_URL} — could not auto-detect reachable host; you may need to start the server.")
if st.button("Re-detect backend host"):
    st.experimental_rerun()

if st.button("Test backend connectivity"):
    status_table = check_hosts_status(DEFAULT_HOST_TRY_LIST, settings.PORT)
    for r in status_table:
        if r['ok']:
            st.success(f"{r['url']} reachable (status: {r['status_code']})")
        else:
            st.warning(f"{r['url']} unreachable")

status_table = check_hosts_status(DEFAULT_HOST_TRY_LIST, settings.PORT)
st.caption("Probe results:")
probe_rows = []
for r in status_table:
    status_text = "✅ Reachable" if r['ok'] else "❌ Unreachable"
    probe_rows.append({
        "host": r['host'],
        "url": r['url'],
        "status": status_text,
        "code": r['status_code']
    })
st.table(probe_rows)

# --- Main Query Interface ---
user_query = st.text_area("Your Financial Query:", 
                          placeholder="e.g., What was the net revenue of Company X in Q3 2024, and what is the equivalent in Euros?",
                          height=100)

if st.button("Analyze & Answer", type="primary") and user_query:
    with st.spinner('Agent is processing query and executing tools/RAG...'):
        try:
            # Reattempt host detection at query time to favor any backend that started after
            # Streamlit app loaded or if network conditions changed.
            runtime_detected = find_reachable_host(DEFAULT_HOST_TRY_LIST, settings.PORT)
            if runtime_detected:
                client_host = runtime_detected
                BACKEND_URL = f"http://{client_host}:{settings.PORT}"
                API_URL = f"{BACKEND_URL}/v1/query"
            # Call the FastAPI backend with the user query
            response = requests.post(
                API_URL, 
                json={"query": user_query},
                timeout=30 # Allow 30 seconds for complex queries
            )
            response.raise_for_status()

            data = response.json()

            st.subheader("Final AI Answer 🤖")
            st.markdown(data.get("answer", "No answer received."))

            st.subheader("Traceability & Sources")
            st.caption("This section shows the data sources and logic steps used by the AI Agent.")

            # Display sources and tools used
            if data.get("tools_used"):
                st.code(f"Tools Used: {', '.join(data['tools_used'])}", language="text")

            # NOTE: A robust implementation would return 'sources' from RAG
            # st.markdown(f"**Sources:** {', '.join(data.get('sources', ['No specific document sources found.']))}")
        except requests.exceptions.RequestException as e:
            logger.exception("Request to backend failed: %s", e)
            # Provide an actionable message in the Streamlit UI with exact commands
            st.error(
                "Error connecting to the backend API. Ensure the backend server is running and reachable. "
                f"Tried: {API_URL}. Details: {e}"
            )
            st.warning("Common fixes:")
            st.write("- Start the backend server with the following command (in a separate terminal):")
            st.code("uvicorn main:app --reload --host 0.0.0.0 --port 8000", language="bash")
            st.write("- If running on the same machine, Streamlit will try localhost/127.0.0.1 first. If the server is bound to 0.0.0.0, those should work too")
            st.write("- If you run with 'python main.py' instead of uvicorn, use:")
            st.code("python main.py", language="bash")
            st.write("- Check firewall rules and ensure the port is open (e.g., Windows Firewall).")
            if not detected_host:
                st.info("Tip: I attempted to auto-detect a backend host (tried localhost, 127.0.0.1, and settings.HOST) but could not reach any.")
            if st.button("Re-test backend connection"):
                st.experimental_rerun()
        except json.JSONDecodeError:
            st.error("Invalid response from the API.")