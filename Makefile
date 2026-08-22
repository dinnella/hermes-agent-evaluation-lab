.PHONY: check

check:
	python3 scripts/check_docs.py
	python3 scripts/check_actions_policy.py
	python3 scripts/check_mcp_protocol.py
	python3 scripts/check_mitmproxy_policy.py
	bash -n deploy/github-actions/run.sh