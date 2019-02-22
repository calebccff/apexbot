import json

def get_fromid(obj, key, id):
    try:
        return [x[key] for x in obj].index(id)
    except ValueError:
        return None

async def save_json(obj, file):
    f = open(file+".json", "w")
    json.dump(obj, f, indent=4)
    f.close()