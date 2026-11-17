import json
import os
import sys

# Minimal reproduction or check
def test_config():
    config_path = "trader/config.json"
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            cfg = json.load(f)
            # Simulate the check for sec_user_agent
            ua = str(cfg.get("sec_user_agent") or "").strip()
            print(f"User agent found: {ua}")
            return ua
    else:
        print("Config not found")
        return None

if __name__ == "__main__":
    test_config()
