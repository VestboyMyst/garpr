import requests

RANKINGS_URL = "http://garsh0p.no-ip.biz:5100/norcal/rankings"

r = requests.get(RANKINGS_URL)
ranking = r.json()['ranking']

for line in ranking:
    print "%s\t%s\t%s" % (line['rank'], line['name'], round(line['rating'], 3))
