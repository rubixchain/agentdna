import os, sys, uuid, asyncio
import streamlit as st
import nest_asyncio
from rubix.client import RubixClient
from rubix.querier import Querier
from dotenv import load_dotenv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agentdna import NodeClient
from host.agent import HostAgent

nest_asyncio.apply()
load_dotenv()
HERE = os.path.dirname(__file__)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

node = NodeClient(alias="host")
DEFAULT_BASE_URL = node.get_base_url()

REMOTE_URLS = [
    "http://localhost:10002",
    "http://localhost:10003",
    "http://localhost:10004",
]

# -------------------------
# Host singleton in session
# -------------------------
if "HOST" not in st.session_state:
    loop = asyncio.get_event_loop()
    try:
        st.session_state.HOST = loop.run_until_complete(
            HostAgent.create(remote_agent_addresses=REMOTE_URLS)
        )
    except Exception:
        st.session_state.HOST = HostAgent()

HOST = st.session_state.HOST

# -------------------------
# Streamlit UI
# -------------------------
st.set_page_config(page_title="A2A Host Console", layout="wide")
st.title("Pickleball Court Agent")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "chat" not in st.session_state:
    st.session_state.chat = []


async def consume_stream(q: str, sid: str) -> str:
    final = ""
    async for event in HOST.stream(q, sid):
        if event.get("is_task_complete"):
            final = event.get("content") or event.get("text") or ""
    return final


def run_stream(q: str) -> str:
    return asyncio.get_event_loop().run_until_complete(
        consume_stream(q, st.session_state.session_id)
    )

# 1) Render chat history ONCE
for role, msg in st.session_state.chat:
    if role == "assistant_json":
        st.chat_message("assistant").json(msg)
    else:
        st.chat_message(role).write(msg)

# 2) Single chat_input
prompt = st.chat_input("Type a message for the Host Agent…", key="host_chat_input")

# 3) Handle new input
if prompt:
    st.session_state.chat.append(("user", prompt))

    with st.spinner("Processing Request…"):
        reply = run_stream(prompt)

    st.session_state.chat.append(("assistant", reply))
    st.rerun()

# -------------------------
# Sidebar controls
# -------------------------
st.sidebar.subheader("Controls")

def quick(q: str):
    st.session_state.chat.append(("user", f"(Quick) {q}"))
    with st.spinner("Running…"):
        reply = run_stream(q)
    st.session_state.chat.append(("assistant", reply))
    st.rerun()

st.sidebar.button("Court Availabilities", on_click=lambda: quick("/other next 3 slots"))

st.sidebar.button(
    "New Session",
    on_click=lambda: st.session_state.update(session_id=str(uuid.uuid4()), chat=[])
)

def get_nft_token_from_host() -> str:
    try:
        return HOST.dna.handler.nft_token
    except Exception:
        return ""

nft_id = get_nft_token_from_host()
if not nft_id:
    st.sidebar.write("⚠️ No NFT token available (HOST.dna.handler.nft_token not set)")

def fetch_nft_data(nft_id: str, latest: bool = False) -> dict:
    client = RubixClient(node_url=DEFAULT_BASE_URL, timeout=300)
    rubixQuerier = Querier(client)
    states = rubixQuerier.get_nft_states(
        nft_address=nft_id,
        only_latest_state=latest
    )
    print(f"Total NFT States Retrieved: {states}")
    return states

if not nft_id:
    st.sidebar.write("⚠️ token.txt not found")

latest_only = False

if st.sidebar.button("History Records"):
    if not nft_id:
        st.warning("No NFT ID found in token.txt")
    else:
        with st.spinner("Fetching NFT data…"):
            nft_resp = fetch_nft_data(nft_id, latest_only)
        st.session_state.chat.append(("user", f"(NFT Request) {nft_id}"))
        st.session_state.chat.append(("assistant_json", nft_resp))
        st.rerun()

if "inject_fake" not in st.session_state:
    st.session_state.inject_fake = False

st.sidebar.checkbox("Inject Fake Response", key="inject_fake")
HOST.inject_fake = st.session_state.inject_fake