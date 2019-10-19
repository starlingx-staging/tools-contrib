import json

cves = []
cves_valid = []
cves_warning = []

with open('localhost.json') as json_file:
    data = json.load(json_file)
    for p in data["scannedCves"]:
        cve = {}
        cve["id"] = p.strip()
        cves.append(cve)

    for cve in cves:
        cve_id = cve["id"]
        try:
            nvd2_score = data["scannedCves"][cve_id]["cveContents"]["nvd"]["cvss2Score"]
            cvss2vector  = data["scannedCves"][cve_id]["cveContents"]["nvd"]["cvss2Vector"]
        except:
            print("%s has no cvss2Score or cvss2Vector" % (cve_id))
        else:
            cve["cvss2Score"] = nvd2_score
            for element in cvss2vector.split("/"):
                if "AV:" in element:
                    av = element.split(":")[1]
                if "AC:" in element:
                    ac = element.split(":")[1]
                if "Au:" in element:
                    au = element.split(":")[1]
                if "A:" in element:
                    ai = element.split(":")[1]
            cve["av"] = av
            cve["ac"] = ac
            cve["au"] = au
            cve["ai"] = ai
            cves_valid.append(cve)

for cve in cves_valid:
    if cve["cvss2Score"] >= 7.0\
    and cve["av"] == "N" \
    and cve["ac"] == "L" \
    and ("N" in cve["au"] or "S" in cve["au"]) \
    and ("P" in cve["ai"] or "C" in cve["ai"]):
        print(cve)

