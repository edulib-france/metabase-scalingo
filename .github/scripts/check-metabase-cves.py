#!/usr/bin/env python3
"""Report NVD CVEs that affect a given Metabase version.

Reads the version from .metabase-version (or argv[1]) and matches it against
the CPE version ranges NVD publishes for the metabase:metabase product. Prints
one Markdown line per matching CVE and exits 1 when there is at least one.
"""
import json, os, re, sys, time, urllib.request

API = ("https://services.nvd.nist.gov/rest/json/cves/2.0"
       "?virtualMatchString=cpe:2.3:a:metabase:metabase&resultsPerPage=2000")


def parse(version):
    """'v0.63.18' -> (0, 63, 18); unparsable parts are dropped."""
    nums = re.findall(r"\d+", version or "")
    return tuple(int(n) for n in nums)


def pad(a, b):
    n = max(len(a), len(b))
    return a + (0,) * (n - len(a)), b + (0,) * (n - len(b))


def cmp(a, b):
    a, b = pad(a, b)
    return (a > b) - (a < b)


def oss(match):
    """True for an open-source CPE entry.

    NVD states the edition in the sw_edition field: '-' for the open-source
    build (versions 0.x), 'enterprise' for the enterprise one (1.x). Without
    this filter, a 0.x version compares as lower than every 1.x range and every
    enterprise-only CVE looks like a hit.
    """
    fields = match.get("criteria", "").split(":")
    return len(fields) > 9 and fields[9] in ("-", "*")


def affected(match, version):
    """True when `version` falls inside one CPE match's range."""
    if not match.get("vulnerable") or not oss(match):
        return False

    fields = match.get("criteria", "").split(":")
    exact = fields[5] if len(fields) > 5 else "*"
    bounds = {k: match.get(k) for k in (
        "versionStartIncluding", "versionStartExcluding",
        "versionEndIncluding", "versionEndExcluding") if match.get(k)}

    if not bounds:
        # No range at all: only an exact version (or a wildcard) is stated.
        return exact in ("*", "-") or parse(exact) == version

    if "versionStartIncluding" in bounds and cmp(version, parse(bounds["versionStartIncluding"])) < 0:
        return False
    if "versionStartExcluding" in bounds and cmp(version, parse(bounds["versionStartExcluding"])) <= 0:
        return False
    if "versionEndIncluding" in bounds and cmp(version, parse(bounds["versionEndIncluding"])) > 0:
        return False
    if "versionEndExcluding" in bounds and cmp(version, parse(bounds["versionEndExcluding"])) >= 0:
        return False
    return True


def severity(cve):
    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        for metric in cve.get("metrics", {}).get(key, []):
            data = metric.get("cvssData", {})
            return data.get("baseSeverity") or metric.get("baseSeverity") or "?", data.get("baseScore")
    return "?", None


def main():
    raw = sys.argv[1] if len(sys.argv) > 1 else open(".metabase-version").read()
    raw = next((l for l in (re.sub(r"#.*", "", l).strip() for l in raw.splitlines()) if l), "")
    version = parse(raw)
    if not version:
        sys.exit(f"Could not read a version from {raw!r}")

    request = urllib.request.Request(API, headers={"User-Agent": "edulib-metabase-cve-check"})
    key = os.environ.get("NVD_API_KEY")
    if key:
        request.add_header("apiKey", key)

    # NVD rate-limits anonymous callers and returns the odd 503: retry rather
    # than report "no vulnerabilities" - or fail the run - on a hiccup.
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.load(response)
            break
        except Exception as error:  # noqa: BLE001 - any failure is worth a retry
            if attempt == 3:
                sys.exit(f"Could not read the NVD API: {error}")
            time.sleep(6 * (attempt + 1))

    hits = []
    for item in data.get("vulnerabilities", []):
        cve = item["cve"]
        if cve.get("vulnStatus") == "Rejected":
            continue
        matches = [m for node in cve.get("configurations", [])
                   for node in node.get("nodes", [])
                   for m in node.get("cpeMatch", [])
                   if "metabase:metabase" in m.get("criteria", "")]
        if any(affected(m, version) for m in matches):
            level, score = severity(cve)
            summary = cve["descriptions"][0]["value"].split(". ")[0][:160]
            hits.append((level, score or 0, cve["id"], summary))

    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "?": 4}
    hits.sort(key=lambda h: (order.get(h[0], 5), -h[1]))

    # First line doubles as the title of the issue the workflow opens.
    print(f"Metabase {raw}: {len(hits)} known CVE(s)")
    print()
    if hits:
        print(f"NVD lists these CVEs as affecting the version pinned in "
              f"`.metabase-version` ({raw}):")
        print()
        for level, score, cve_id, summary in hits:
            print(f"- **{level}**"
                  f"{f' ({score})' if score else ''} "
                  f"[{cve_id}](https://nvd.nist.gov/vuln/detail/{cve_id}) — {summary}")
        print()
        print("Upgrading is a one-line change to `.metabase-version`; "
              "Renovate may already have opened a pull request for it.")
    else:
        print(f"None of the {data.get('totalResults')} CVEs NVD publishes for "
              f"Metabase affect {raw}.")
    print()
    print("Source: NVD, open-source editions only (enterprise releases are "
          "versioned 1.x and tracked separately).")

    sys.exit(1 if hits else 0)


if __name__ == "__main__":
    main()
