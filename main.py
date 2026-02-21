#!/usr/bin/env python3

import json
import os
import time
import requests
from datetime import datetime

def is_json(myjson):
  try:
    json.loads(myjson)
  except ValueError as e:
    return False
  return True

script_dir = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(script_dir, "list.json")


if not os.path.exists(json_path):
    print("Downloading list.json from instances.social...")
    try:
        response = requests.get("https://instances.social/list.json?q%5Bmin_users%5D=&q%5Bmax_users%5D=&strict=true&_=" + str(int(datetime.now().timestamp() * 1000)), timeout=600)
        response.raise_for_status()

        with open(json_path, 'w', encoding='utf-8') as file:
            file.write(response.text)
        print("Done")

    except requests.exceptions.RequestException as e:
        print(f"Download failed: {e}")
        exit(1)


print("Which Mastodon instances should not be banned?")
print("Please provide the domain of the Mastodon instances, press <ENTER> without entering any value when done")
domains = {}
while True:
    if len(domains) > 0:
        print("Added to unblock list: " + ", ".join(domains))
    domain = input("> ")
    domain = domain.strip()
    if domain == "":
        if len(domains) > 0:
            break
        print("Unblock list cannot be empty")
    if " " in domain:
        for value in domain.split():
            domains[value] = None
    else:
        domains[domain] = None

# Get an endpoint to cross test unblocked domains
for domain in domains.keys():
    try:
        print(f"Trying to locate random user from: {domain} ...")
        response = requests.get(f"https://{domain}/api/v2/instance", timeout=20)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Request failed towards {domain}: {e}")
        print(f"Skipping {domain}")
        continue
    data = response.json()
    if "contact" in data and "account" in data["contact"] and "username" in data["contact"]["account"] and type(data["contact"]["account"]["username"]) == str:
        print("Found contact: " + data["contact"]["account"]["username"])
        domains[domain] = data["contact"]["account"]["username"]
    else:
        print("Found no users")
        print(f"Skipping {domain}")
        continue

# Now test literally every single other Mastodon instance, and see if these users on these instances are not found.
try:
    with open(json_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
except Exception as e:
    print(f"Error: {e}")
    print(f"You might need to download the list.json from: https://instances.social/list.json?q%5Bmin_users%5D=&q%5Bmax_users%5D=&strict=true&_=1771617725926")
if not data:
    exit(1)

checked_instances = {}

cancel = False
sorted_instances = sorted([d for d in data["instances"] if d["users"] is not None], key=lambda d: d['users'], reverse=True)
for instance in sorted_instances:
    domain = instance["name"]
    checked_instances[domain] = {
        "unblock_score": 0,
        "elapsed": 99.99
    }
    if cancel == True:
        break

    for unblocked_domain in domains.keys():
        print(f"[ ] Checking {unblocked_domain} -> {domain} ... ", end="")
        # Makes no sense to check towards itself
        if unblocked_domain == domain:
            checked_instances[domain]["unblock_score"] += 1
            print(f"\r[✓]")
            continue

        username = domains[unblocked_domain]
        url = f"https://{domain}/api/v1/accounts/lookup?acct={username}%40{unblocked_domain}"

        try:
            start = time.time()
            response = requests.get(url, timeout=15, allow_redirects=True)
            response.raise_for_status()
            checked_instances[domain]["elapsed"] = time.time() - start
        except requests.exceptions.RequestException as e:
            print(f"Response failed\r[x]" )
            continue
        except KeyboardInterrupt as e:
            print("Cancelling the rest, and finishing...\r[-]")
            cancel = True
            break

        if not is_json(response.text):
            print(f"Response not a JSON\r[x]")
            continue

        json_resp = response.json()
        if "acct" not in json_resp:
            print(f"\"acct\" key missing in JSON response\r[x]")
            continue
        if json_resp["acct"].lower() != f"{username}@{unblocked_domain}":
            print(f"acct not equal to supposed acct, {json_resp['acct'].lower()} != {username}@{unblocked_domain}\r[x]")
            continue

        checked_instances[domain]["unblock_score"] += 1
        print(f"\r[✓]")

print("\n\nResult")
filtered_instances = sorted([{"domain": domain, **scores} for domain, scores in checked_instances.items()], key=lambda x: (-x["unblock_score"], x["elapsed"]))
for instance in filtered_instances:
    print(f"{instance['unblock_score']} - {round(instance['elapsed']*1000)}ms {instance['domain']}")
