import json

def get_fromid(obj, key, id):
    try:
        return [x[key] for x in obj].index(id)
    except ValueError:
        return None

def save_json(obj, file):
    f = open(file+".json", "w")
    json.dump(obj, f, indent=4)
    f.close()

def add_stat(jsonarr, key, init):
    newarr = []
    for user in jsonarr:
        n = dict()
        for k in list(user.keys()):
            if k == "stats":
                n[key] = init
            n[k] = user[k]
        newarr.append(n)
    return newarr