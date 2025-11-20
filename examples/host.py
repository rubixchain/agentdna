from agentdna import AgentDNA

dna = AgentDNA(alias="host", role="host")

built = dna.build(
    original_message="Are you free tomorrow for a game?",
    state={"task_id": "123", "context_id": "abc"},
)

host_json = built["host_json"]

payload = {
    "message": {
        "role": "user",
        "parts": [{"text": host_json}],
    }
}

# ...send payload to a remote agent

result = dna.handle(
    resp_parts="<resp_parts>",
    original_task="Are you free tomorrow?",
    remote_name="karley",
)

verified_messages = result["messages"]
trust_issues      = result["trust_issues"]
nft_result        = result["nft_result"]   