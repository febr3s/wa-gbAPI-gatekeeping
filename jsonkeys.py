import json, sys

with open(sys.argv[1]) as f:
    data = json.load(f)

def show(obj, depth=0):
    prefix = "  " * depth
    if isinstance(obj, dict):
        for key in obj:
            print(prefix + key)
            show(obj[key], depth + 1)
    elif isinstance(obj, list):
        print(prefix + "[]")
        keys_seen = set()
        for item in obj:
            if isinstance(item, dict):
                keys_seen.update(item.keys())
        if keys_seen:
            show(dict.fromkeys(keys_seen), depth + 1)
        else:
            # Check for nested arrays
            for item in obj:
                if isinstance(item, list):
                    show(item, depth)
                    break

if isinstance(data, list):
    show(data, 0)
else:
    show(data, 0)