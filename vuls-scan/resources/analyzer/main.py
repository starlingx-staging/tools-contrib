"""
Implement policy based on
https://wiki.openstack.org/wiki/StarlingX/Security/CVE_Support_Policy
Create documentation as pydoc -w cve_policy_filter
"""
import json
import sys
import os

def chec_nvd_link(url):
    """
    If the NVD link exist it will fetch it for the report
    return: True/False if the NVD link exist
    """
    import requests
    ret = False
    try:
        request = requests.get(url)
    except ValueError as error:
        print(error)
        sys.exit(-1)
    else:
        if request.status_code == 200:
            ret = True
        else:
            ret = False
    return ret

def print_html_report(cves_to_fix, cves_to_track, cves_w_errors, title):
    """
    Print the html report
    """
    import jinja2

    template_loader = jinja2.FileSystemLoader(searchpath="./")
    template_env = jinja2.Environment(loader=template_loader)
    template_file = "template.txt"
    template = template_env.get_template(template_file)
    heads = ["cve_id", "status", "cvss2Score", "av", "ac", "au", "ai"]
    output_text = template.render(cves_to_fix=cves_to_fix,\
        cves_to_track=cves_to_track,\
        cves_w_errors=cves_w_errors,\
        heads=heads,\
        title=title)
    report_title = 'report_%s.html' % (title)
    html_file = open(report_title, 'w')
    html_file.write(output_text)
    html_file.close()

def print_report(cves_to_fix, cves_to_track, cves_w_errors):
    """
    Print the txt STDOUT report
    """
    nvd_link = "https://nvd.nist.gov/vuln/detail/"
    print("\nValid CVEs to take action immediately: %d\n" % (len(cves_to_fix)))
    for cve in cves_to_fix:
        print("\n")
        print(cve["id"])
        print("status : " + cve["status"])
        print("cvss2Score : " + str(cve["cvss2Score"]))
        print("Attack Vector: " + cve["av"])
        print("Access Complexity : " + cve["ac"])
        print("Autentication: " + cve["au"])
        print("Availability Impact :" + cve["ai"])
        print("Affected packages:")
        print(cve["affectedpackages"])
        print(cve["summary"])
        if chec_nvd_link(nvd_link + cve["id"]):
            print(nvd_link + cve["id"])

    print("\nCVEs to track for incoming fix: %d \n" % (len(cves_to_track)))
    for cve in cves_to_track:
        cve_line = []
        for key, value in cve.items():
            if key != "summary":
                cve_line.append(key + ":" + str(value))
        print(cve_line)

    print("\nERROR: CVEs that has no cvss2Score or cvss2Vector: %d \n" \
        % (len(cves_w_errors)))
    for cve in cves_w_errors:
        print(cve)


def main():
    """
    main function
    """
    data = {}
    cves = []
    cves_valid = []
    cves_to_fix = []
    cves_to_track = []
    cves_w_errors = []

    if len(sys.argv) < 3:
        print("\nERROR : Missing arguments, the expected arguments are:")
        print("\n   %s <result.json> <title>\n" % (sys.argv[0]))
        print("\n result.json = json file generated from: vuls report -format-json")
        print("\n")
        sys.exit(0)

    if os.path.isfile(sys.argv[1]):
        results_json = sys.argv[1]
    else:
        sys.exit(0)

    title = sys.argv[2]

    try:
        with open(results_json) as json_file:
            data = json.load(json_file)
    except ValueError as error:
        print(error)

    for element in data["scannedCves"]:
        cve = {}
        cve["id"] = str(element.strip())
        cves.append(cve)

    for cve in cves:
        cve_id = cve["id"]
        affectedpackages_list = []
        status_list = []

        try:
            nvd2_score = data["scannedCves"][cve_id]["cveContents"]["nvd"]["cvss2Score"]
            cvss2vector = data["scannedCves"][cve_id]["cveContents"]["nvd"]["cvss2Vector"]
            summary = data["scannedCves"][cve_id]["cveContents"]["nvd"]["summary"]
            affectedpackages = data["scannedCves"][cve_id]["affectedPackages"]

        except KeyError:
            cves_w_errors.append(cve)
        else:
            cve["cvss2Score"] = nvd2_score
            for element in cvss2vector.split("/"):
                if "AV:" in element:
                    _av = element.split(":")[1]
                if "AC:" in element:
                    _ac = element.split(":")[1]
                if "Au:" in element:
                    _au = element.split(":")[1]
                if "A:" in element:
                    _ai = element.split(":")[1]
            cve["av"] = str(_av)
            cve["ac"] = str(_ac)
            cve["au"] = str(_au)
            cve["ai"] = str(_ai)
            cve["summary"] = str(summary)
            for pkg in affectedpackages:
                affectedpackages_list.append(pkg["name"])
                status_list.append(pkg["notFixedYet"])
            cve["affectedpackages"] = affectedpackages_list
            if True in status_list:
                cve["status"] = "unfixed"
            else:
                cve["status"] = "fixed"
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

    print_report(cves_to_fix, cves_to_track, cves_w_errors)
    print_html_report(cves_to_fix, cves_to_track, cves_w_errors, title)

if __name__ == "__main__":
    main()
