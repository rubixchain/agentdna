from agentdna import AgentDNA

dna = AgentDNA(alias="<agent name>", role="remote")

verify_info =  dna.handle(raw_text="<raw_text_received>")

original_message = verify_info["original_message"]
host_block       = verify_info["host_block"]
host_ok          = verify_info["host_ok"]

reply = "Yes! I’m available at 4 PM."

built_resp = dna.build(
    original_message=original_message,
    response=reply,
    host_block=host_block,
)

combined_json = built_resp["combined_json"]