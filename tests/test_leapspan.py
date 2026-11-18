import json
from types import SimpleNamespace
from unittest import TestCase
from host import load, UserError

gl, mod = load("leapspan")


class LeapSpanTest(TestCase):
    def setUp(self):
        self.contract = mod.LeapSpan()
        self.contract.snapshots = {}
        self.contract.certificates = {}

    def test_source_parsers_normalize_epoch_and_expiry(self):
        iers = "# File expires on 28 June 2027\n41317.0 1 1 1972 10"
        rows, expiry = mod.parse_iers(iers)
        iana = f"#@ {expiry + mod.NTP_DELTA}\n2272060800 10 # initial"
        self.assertEqual(mod.parse_iana(iana), (rows, expiry))
        self.assertEqual(rows, [[63072000, 10]])

    def test_source_failure_preserves_state(self):
        gl.nondet.web.get = lambda _: SimpleNamespace(status=503)
        with self.assertRaisesRegex(UserError, "SOURCE_HTTP_ERROR"):
            self.contract.refresh()
        self.assertEqual(self.contract.snapshots, {})

    def test_cross_source_conflict_preserves_state(self):
        iers = ["# File expires on 1 January 2027"]
        iana = [f"#@ {mod.utc_day(2027,1,1) + mod.NTP_DELTA}"]
        for i in range(20):
            stamp = mod.utc_day(1972 + i, 1, 1)
            iers.append(f"{stamp // 86400 + 40587}.0 1 1 {1972 + i} {10 + i}")
            iana.append(f"{stamp + mod.NTP_DELTA} {27 if i == 19 else 10 + i}")
        data = {mod.IERS:iers, mod.IANA:iana}
        gl.nondet.web.get = lambda url: SimpleNamespace(status=200, body="\n".join(data[url]).encode())
        with self.assertRaisesRegex(UserError, "SOURCES_DISAGREE"):
            self.contract.refresh()
        self.assertEqual(self.contract.snapshots, {})

    def test_arithmetic_boundaries_and_replay(self):
        self.contract.snapshots["known"] = json.dumps([[[63072000, 10], [1483228800, 11]], 1500000000])
        key = self.contract.certify("known", 1483228799, 1483228800)
        self.assertEqual(json.loads(self.contract.certificate(key))["elapsed_seconds"], 2)
        self.assertEqual(self.contract.certify("known", 1483228799, 1483228800), key)
        self.assertEqual(len(self.contract.certificates), 1)
        with self.assertRaisesRegex(UserError, "OUTSIDE_SNAPSHOT"):
            self.contract.certify("known", 1499999999, 1500000000)

    def test_negative_leap_and_boundary_at_start(self):
        self.contract.snapshots["known"] = json.dumps([[[63072000, 10], [1483228800, 9]], 1500000000])
        for start, end, elapsed in [(1483228799, 1483228800, 0), (1483228800, 1483228801, 1)]:
            key = self.contract.certify("known", start, end)
            self.assertEqual(json.loads(self.contract.certificate(key))["elapsed_seconds"], elapsed)
