# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
from datetime import date
import hashlib
import json
import re

IERS = "https://hpiers.obspm.fr/iers/bul/bulc/Leap_Second.dat"
IANA = "https://data.iana.org/time-zones/data/leap-seconds.list"
EPOCH = date(1970, 1, 1)
NTP_DELTA = 2208988800
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")


def utc_day(year, month, day):
    return (date(year, month, day) - EPOCH).days * 86400


def parse_iers(body):
    expiry = re.search(r"File expires on (\d+) ([A-Za-z]+) (\d+)", body)
    day, month, year = expiry.groups()
    until = utc_day(int(year), MONTHS.index(month) + 1, int(day))
    rows = []
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        mjd, day, month, year, offset = line.split()
        timestamp = utc_day(int(year), int(month), int(day))
        assert mjd == str(timestamp // 86400 + 40587) + ".0"
        rows.append([timestamp, int(offset)])
    return rows, until


def parse_iana(body):
    until = int(re.search(r"(?m)^#@\s+(\d+)", body)[1]) - NTP_DELTA
    rows = []
    for line in body.splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            stamp, offset = map(int, line.split())
            rows.append([stamp - NTP_DELTA, offset])
    return rows, until


def validate(rows, expiry):
    if not 20 <= len(rows) <= 128 or rows[0] != [63072000, 10] or rows[-1][0] >= expiry:
        raise ValueError("table bounds")
    for i, (stamp, offset) in enumerate(rows):
        if stamp % 86400 or (i and (stamp <= rows[i-1][0] or abs(offset - rows[i-1][1]) != 1)):
            raise ValueError("transition")


class LeapSpan(gl.Contract):
    snapshots: TreeMap[str, str]
    certificates: TreeMap[str, str]

    def __init__(self):
        pass

    @gl.public.write
    def refresh(self) -> str:
        def observe():
            try:
                first = gl.nondet.web.get(IERS)
                second = gl.nondet.web.get(IANA)
                if first.status != 200 or second.status != 200:
                    return "SOURCE_HTTP_ERROR"
                if len(first.body) > 32000 or len(second.body) > 32000:
                    return "INVALID_TABLE"
                a, a_expiry = parse_iers(first.body.decode())
                b, b_expiry = parse_iana(second.body.decode())
                validate(a, a_expiry)
                validate(b, b_expiry)
                until = min(a_expiry, b_expiry)
                a_common = [row for row in a if row[0] < until]
                b_common = [row for row in b if row[0] < until]
                if a_common != b_common:
                    return "SOURCES_DISAGREE"
                return json.dumps([a_common, until], separators=(",", ":"))
            except Exception:
                return "INVALID_OR_UNAVAILABLE_TABLE"
        result = gl.eq_principle.strict_eq(observe)
        if not result.startswith("["):
            raise gl.UserError(result)
        key = hashlib.sha256(result.encode()).hexdigest()
        if key not in self.snapshots:
            self.snapshots[key] = result
        return key

    @gl.public.view
    def snapshot(self, digest: str) -> str:
        return self.snapshots[digest] if digest in self.snapshots else ""

    @gl.public.view
    def certificate(self, key: str) -> str:
        return self.certificates[key] if key in self.certificates else ""

    @gl.public.write
    def certify(self, digest: str, start: u64, end: u64) -> str:
        if digest not in self.snapshots:
            raise gl.UserError("UNKNOWN_SNAPSHOT")
        rows, expiry = json.loads(self.snapshots[digest])
        if not rows[0][0] <= start < end < expiry:
            raise gl.UserError("OUTSIDE_SNAPSHOT_OR_REVERSED")
        start_offset = max((row for row in rows if row[0] <= start), key=lambda row: row[0])[1]
        end_offset = max((row for row in rows if row[0] <= end), key=lambda row: row[0])[1]
        identity = f"{digest}:{start}:{end}"
        key = hashlib.sha256(identity.encode()).hexdigest()
        if key not in self.certificates:
            self.certificates[key] = json.dumps({
                "snapshot": digest, "start": int(start), "end": int(end),
                "posix_seconds": int(end - start), "adjustment": end_offset - start_offset,
                "elapsed_seconds": int(end - start + end_offset - start_offset),
                "transitions": [row for row in rows if start < row[0] <= end],
            }, separators=(",", ":"))
        return key
