import re
import json
import requests
import os
import shutil
from collections import defaultdict

def extract_relays_array(js_text):
    # Find where the relays array starts
    start = js_text.find("relays:[")
    if start == -1:
        return None

    sliced = js_text[start + len("relays:"):]
    
    # Match brackets to extract the full array
    bracket_count = 0
    end_index = 0
    for i, c in enumerate(sliced):
        if c == "[":
            bracket_count += 1
        elif c == "]":
            bracket_count -= 1
            if bracket_count == 0:
                end_index = i + 1
                break

    return sliced[:end_index]

def js_to_json(js_array_text):
    # Convert JS-style object to valid JSON
    js_array_text = re.sub(r'([{,]\s*)(\w+)\s*:', r'\1"\2":', js_array_text)
    js_array_text = js_array_text.replace("undefined", "null")
    js_array_text = js_array_text.replace("true", "true").replace("false", "false")
    return js_array_text

def cleanUp():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "fetched")
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

def save(folder, relaysToSave):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "fetched", folder)
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    # Save all
    filename = os.path.join(output_dir, f"all.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(relaysToSave, f, indent=2)
    print(f"Saved {len(relaysToSave)} servers to " + filename)

    # Save by country_code
    grouped = defaultdict(list)
    for relay in relaysToSave:
        country = relay.get("country_code", "UNKNOWN")
        grouped[country].append(relay)
    for country, relays_list in grouped.items():
        filename = os.path.join(output_dir, f"{country}.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(relays_list, f, indent=2)
        print(f"Saved {len(relays_list)} servers to {filename}")

# Fetch the Mullvad Page
url = "https://mullvad.net/en/servers"
html = requests.get(url).text

# Extract All <script> Blocks
script_blocks = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
target_block = next((block for block in script_blocks if "relays:[" in block), None)

if not target_block:
    print("Could not find any <script> block containing relays!")
    exit(1)

raw_array = extract_relays_array(target_block)

if not raw_array:
    print("Could not extract the relays array.")
    exit(1)

json_text = js_to_json(raw_array)

try:
    relays = json.loads(json_text)
except json.JSONDecodeError as e:
    print("JSON parsing error:", e)
    exit(1)

# Remove Old Folder
cleanUp()

# Filter and Save Relays
wireguard_relays = [relay for relay in relays if relay.get("type") == "wireguard"]
active_relays = [relay for relay in wireguard_relays if relay.get("active") == True]

without_messages_relays = [relay for relay in active_relays if relay.get("status_messages") == []]
save("owned_and_rented", without_messages_relays)

owned_relays = [relay for relay in without_messages_relays if relay.get("owned") == True]
save("owned", owned_relays)

rented_relays = [relay for relay in without_messages_relays if relay.get("owned") == False]
save("rented", rented_relays)