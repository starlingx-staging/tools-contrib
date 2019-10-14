"""
Implement policy based on
https://wiki.openstack.org/wiki/StarlingX/Security/CVE_Support_Policy

Document as pydoc -w cve_policy_filter

Vulscan generates two files, please save them as:

VULS scan report full text <date> ->  cves_report_full.txt
VULS scan report format list <date> -> cves_report_list.txt

Run this script as  python cve_policy_filter.py

"""
import os
import sys

cves_report_full_file = "cves_report_full.txt"
cves_report_list_file = "cves_report_list.txt"
cves_report_old_list_file = "cves_report_old_list_file.txt"
cves_report_old_full_file = "cves_report_old_full_file.txt"

def get_new_cves(cve_ids,old_cve_ids):
    new_cves = (list(set(cve_ids) - set(old_cve_ids)))
    print("\nNew CVEs from last report:\n")
    for cve_id in new_cves:
        cve = {}
        cvss = float(get_cvss(cve_id,cves_report_list_file))
        av,ac,au,ai = get_base_vector(cve_id,cves_report_full_file)
        cve_status = get_cves_status(cve_id,cves_report_list_file)
        cve["id"] = cve_id
        cve["cvss"] = cvss
        cve["av"] = av
        cve["ac"] = ac
        cve["au"] = au
        cve["ai"] = ai
        cve["status"] = cve_status
        print(cve)

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

def get_cvss(cve_id,filename):
    """
    Get the CVSS score of a CVE
    CVSS, Common Vulnerability Scoring System, is a vulnerability
    scoring system designed to provide an open and standardized method for
    rating IT vulnerabilities.
    :param filename: The name of the file with the CVEs metadata
    :param cve_id: ID of the CVE is necesary to get the CVSS score
    :return: return the CVSS score
    """
    with open(filename,'r') as fh:
        lines = fh.readlines()
        pos = get_position("CVSS",lines)
        for line in lines:
            line = line.strip()
            if "CVE" in line and not "CVE-ID" in line:
                if cve_id in (line.split("|")[1]):
                    cvss = (line.split("|")[pos])
                    return cvss

def get_cves_status(cve_id,filename):
    """
    Get the CVEs status : fixed/unfixed
    :return cve_status
    """
    cve_ids = []
    with open(filename,'r') as fh:
        lines = fh.readlines()
        pos = get_position("FIXED",lines)
        for line in lines:
            if "CVE" in line and not "CVE-ID" in line:
                if cve_id in line:
                    cve_status = line.strip().split("|")[pos].strip()
                    return cve_status

def get_cves_id(filename):
    """
    Get the CVEs ids from the vulscan document
    :param filename: The name of the file with the CVEs metadata
    :return: return the CVE ids as array
    """
    cve_ids = []
    with open(filename,'r') as fh:
        lines = fh.readlines()
        for line in lines:
            if "CVE" in line and not "CVE-ID" in line:
                cve_id = (line.strip().split("|")[1])
                if cve_id not in cve_ids:
                    cve_ids.append(cve_id.strip())
    return cve_ids

def get_base_vector(cve_id,filename):
    """
    Get Base Metrics vector:
    Attack-vector: Context by which vulnerability exploitation is possible.
    Attack-complexity: Conditions that must exist in order to exploit
    Authentication: Num of times that attacker must authenticate to exploit
    Availability-impact: Impact on the availability of the target system.
    return: Attack-vector/ Access-complexity/Authentication/Availability-impact
    """
    with open(filename,'r') as fh:
        vector = None
        av = None
        ac = None
        au = None
        ai = None
        lines = fh.readlines()
        count = 0
        cveid_position = 0
        for line in lines:
            count = count + 1
            if cve_id in line and ("UNFIXED" in line or "FIXED" in line):
                cveid_position = count
            if "nvd" in line and "Au" in line and count < (cveid_position + 10):
                vector = line.split("|")[2].strip()
                break
        if vector:
            for element in vector.split("/"):
                if "AV:" in element:
                    av = element.split(":")[1]
                if "AC:" in element:
                    ac = element.split(":")[1]
                if "Au:" in element:
                    au = element.split(":")[1]
                if "A:" in element:
                    ai = element.split(":")[1]
        return av,ac,au,ai


def get_last_warning_cves():

    cves_warning = []
    cves_report_list_file = cves_report_old_list_file
    cves_report_full_file = cves_report_old_full_file
    cve_ids = get_cves_id(cves_report_list_file)
    for cve_id in cve_ids:
        cve = {}
        cvss = float(get_cvss(cve_id,cves_report_list_file))
        av,ac,au,ai = get_base_vector(cve_id,cves_report_full_file)
        cve_status = get_cves_status(cve_id,cves_report_list_file)

        cve["id"] = cve_id
        cve["cvss"] = cvss
        cve["av"] = av
        cve["ac"] = ac
        cve["au"] = au
        cve["ai"] = ai
        cve["status"] = cve_status

        if  cvss >= 7.0 \
        and av == "N" \
        and ac == "L" \
        and ("N" in au or "S" in au) \
        and ("P" in ai or "C" in ai):
            cves_warning.append(cve)

    return cves_warning


if __name__ == '__main__':

    cves_valid = []
    cves_warning = []
    cves_warning_old = []

    if not os.path.isfile(cves_report_list_file) or \
    not os.path.isfile(cves_report_full_file):
        print("ERROR: cves_report_full.txt and \
        cves_report_list.txt must exist")
        sys.exit(-1)

    cve_ids = get_cves_id(cves_report_list_file)
    old_cve_ids = get_cves_id(cves_report_old_list_file)
    get_new_cves(cve_ids,old_cve_ids)

    cves_warning_old = get_last_warning_cves()
    print("\nCVEs that we had to track from last report\n")
    for cve in cves_warning_old:
        cve_id = (cve["id"].strip())
        cve_status = get_cves_status(cve_id,cves_report_list_file)
        if cve_status == "fixed":
            print(cve)

    for cve_id in cve_ids:
        cve = {}

        cvss = float(get_cvss(cve_id,cves_report_list_file))
        av,ac,au,ai = get_base_vector(cve_id,cves_report_full_file)
        cve_status = get_cves_status(cve_id,cves_report_list_file)

        cve["id"] = cve_id
        cve["cvss"] = cvss
        cve["av"] = av
        cve["ac"] = ac
        cve["au"] = au
        cve["ai"] = ai
        cve["status"] = cve_status

        """
        Following rules from:
        https://wiki.openstack.org/wiki/StarlingX/Security/CVE_Support_Policy
        """
        if  cvss >= 7.0 \
        and av == "N" \
        and ac == "L" \
        and ("N" in au or "S" in au) \
        and ("P" in ai or "C" in ai):
            if cve_status == "fixed":
                cves_valid.append(cve)
            else:
                cves_warning.append(cve)

    print("\nValid CVEs to take action immediately:\n")
    for cve in cves_valid:
        print(cve)

    print("\nCVEs to track for incoming fix:\n")
    for cve in cves_warning:
        print(cve)
