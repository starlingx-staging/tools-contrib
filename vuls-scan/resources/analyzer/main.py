import json

cves = []
cves_valid = []
cves_to_fix = []
cves_to_track = []
cves_w_errors = []

def get_position(token,lines):
    """
    Get the position to search for the token, like CVSS,  in some reports it is
    in column 4th and in some others in 2nd column
    :param lines of the file name cves_report_list.txt
    :return return the CVSS position on the file
    """
    for line in lines:
        line = line.strip()
        if "CVE-ID" in line and "CVSS" in line:
            elements = (line.split("|"))
            count = 0
            for element in elements:
                if token in element.strip():
                    return count
                count +=1

def get_cves_status(cve_id,lines):
    """
    Get the CVEs status : fixed/unfixed
    :return cve_status
    """
    pos = get_position("FIXED",lines)
    for line in lines:
        if "CVE" in line and not "CVE-ID" in line:
            if cve_id in line:
                cve_status = line.strip().split("|")[pos].strip()
                return cve_status

data = {}

with open('localhost.json') as json_file:
    data = json.load(json_file)

for p in data["scannedCves"]:
    cve = {}
    cve["id"] = p.strip()
    cves.append(cve)

for cve in cves:
    cve_id = cve["id"]

    filename = "list.txt"
    with open(filename,'r') as fh:
        lines = fh.readlines()
    cve_status = get_cves_status(cve_id,lines)
    cve["status"] = cve_status
    try:
        nvd2_score = data["scannedCves"][cve_id]["cveContents"]["nvd"]["cvss2Score"]
        cvss2vector  = data["scannedCves"][cve_id]["cveContents"]["nvd"]["cvss2Vector"]
    except:
        cves_w_errors.append(cve)
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
        if cve["status"] == "fixed":
            cves_to_fix.append(cve)
        else:
            cves_to_track.append(cve)

print("\nValid CVEs to take action immediately:\n")
for cve in cves_to_fix:
    print(cve)

print("\nCVEs to track for incoming fix:\n")
for cve in cves_to_track:
    print(cve)

print("\nERROR: CVEs that has no cvss2Score or cvss2Vector:\n")
for cve in cves_w_errors:
    print(cve)

