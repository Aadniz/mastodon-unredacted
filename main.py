#!/usr/bin/env python3

import json
import os
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

fully_supported = []
partially_supported = []

cancel = False
sorted_instances = sorted([d for d in data["instances"] if d["users"] is not None], key=lambda d: d['users'], reverse=True)
for instance in sorted_instances:
    if cancel == True:
        break
    domain = instance["name"]
    print(f"[ ] Checking {domain} ...", end="")

    succsesses = 0

    for unblocked_domain in domains.keys():
        # Makes no sense to check towards itself
        if unblocked_domain == domain:
            continue

        username = domains[unblocked_domain]
        url = f"https://{domain}/api/v1/accounts/lookup?acct={username}%40{unblocked_domain}"
        print(f" Testing {url}", end="")

        try:
            response = requests.get(url, timeout=15, allow_redirects=True)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"\r[x] Checking {domain} ... Response failed" + " "*(len(url)+9))
            continue
        except KeyboardInterrupt as e:
            print("Cancelling the rest, and finishing...")
            cancel = True
            break

        if not is_json(response.text):
            print(f"\r[x] Checking {domain} ...  Response not a JSON" + " "*(len(url)+9))
            continue

        json_resp = response.json()
        if "username" not in json_resp:
            print(f"\r[x] Checking {domain} ...  \"username\" key missing in JSON response" + " "*(len(url)+9))
            continue
        if json_resp["username"] != username:
            print(f"\r[x] Checking {domain} ...  username not equal to supposed username" + " "*(len(url)+9))
            continue

        succsesses += 1
        print(f"\r[✓] Checking {domain} ..." + " "*(len(url)+9))

    if succsesses == len(domains):
        fully_supported.append(domain)
    if succsesses > 0:
        partially_supported.append(domain)


print("\n\nFully supported Mastodon instanced:")
for domain in fully_supported:
    print("  " + domain)

print("\nPartially supported Mastodon instanced:")
for domain in partially_supported:
    print("  " + domain)
