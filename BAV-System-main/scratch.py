import urllib.request
import json
import sqlite3

conn = sqlite3.connect("bav.db")
c = conn.cursor()
c.execute("SELECT id FROM proposals ORDER BY id DESC LIMIT 1")
row = c.fetchone()
conn.close()

if row:
    pid = row[0]
    data = json.dumps({"proposal_id": pid}).encode('utf-8')
    req = urllib.request.Request("http://127.0.0.1:8000/proposal/validate-by-id", data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as res:
            print(res.status)
            print(res.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(e.code)
        print(e.read().decode('utf-8'))
else:
    print("No proposals found")
