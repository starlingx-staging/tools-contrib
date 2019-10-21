import sys
import json
import os

cves_a = []
cves_b = []
cves_w_errors = []
cves_valid = []

def get_vector(cve_id,data):
    cve = {}
    cve["id"] = cve_id
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
        cve["av"] = str(av)
        cve["ac"] = str(ac)
        cve["au"] = str(au)
        cve["ai"] = str(ai)
        print(cve)
        cves_valid.append(cve)

def main():
    data = {}

    if len(sys.argv) < 4:
        print("\nERROR : Missing arguments, the expected arguments are:")
        print("\n   %s <result_a.json> <result_b.json> <title>\n" % (sys.argv[0]) )
        print("\n result_a.json = json file generated from: vuls report -format-json")
        print("\n result_b.json = json file generated from: vuls report -format-json")
        print("\n")
        sys.exit(0)

    if os.path.isfile(sys.argv[1]):
        result_a_json = sys.argv[1]
    else:
        sys.exit(0)
    if os.path.isfile(sys.argv[2]):
        result_b_json = sys.argv[2]
    else:
        sys.exit(0)
    title = sys.argv[3]

    try:
        with open(result_a_json) as json_file:
            data_a = json.load(json_file)
        with open(result_b_json) as json_file:
            data_b = json.load(json_file)
    except ValueError as e:
        print(e)

    for p in data_a["scannedCves"]:
        cve = {}
        cve["id"] = str(p.strip())
        cves_a.append(cve)

    for p in data_b["scannedCves"]:
        cve = {}
        cve["id"] = str(p.strip())
        cves_b.append(cve)


    list_a = []
    list_b = []

    for cve_a in cves_a:
        list_a.append(cve_a["id"])

    for cve_b in cves_b:
        list_b.append(cve_b["id"])

    diff_list = (list(set(list_a) - set(list_b)))

    for cve_id in diff_list:
        if cve_id in list_a:
            get_vector(cve_id,data_a)
        if cve_id in list_b:
            get_vector(cve_id,data_b)

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

if __name__ == "__main__":
    main()
