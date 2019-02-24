import requests, json
r=requests.get("https://public-api.tracker.gg/apex/v1/standard/profile/5/konvex2000", headers={"TRN-Api-Key": "62979e1c-f8bd-4fe9-a07e-ea9213155850"})
print(r.headers)
data = r.json()
f = open("test.json", "w")
json.dump(data, f, indent=4)
f.close()