# LeapSpan

[Deployed contract](https://explorer-studio.genlayer.com/address/0x79dA165D6b19A8C4F63d4a63AE66211a04F07D88) · [Deployment receipt](https://explorer-studio.genlayer.com/transactions/0x36c7aa7b29504d44644fff91a50ca7cc3026d86c66339f720e5d95137ef720d8)

Compute elapsed SI seconds between two ordinary UTC instants across leap seconds. Data ingestion, telemetry reconciliation and archival workflows often carry POSIX labels, whose numerical difference omits an inserted second. LeapSpan pins the source table first, then issues content-addressed interval certificates with an explicit correction and transition trace.

## Consensus and state

Each observation inside GenLayer strict equivalence independently fetches the [IERS leap-second table](https://hpiers.obspm.fr/iers/bul/bulc/Leap_Second.dat) and the [IANA leap-second distribution](https://data.iana.org/time-zones/data/leap-seconds.list). These are two publication channels for the same underlying timekeeping record. Code converts MJD/calendar and NTP records to common POSIX effective instants, checks ordering and unit steps, and requires exact agreement through the earlier expiry. Validators compare the entire canonical series and expiry. Source errors or conflicting observations cannot create a snapshot.

- `refresh() → digest` stores an immutable series and exclusive expiry. Identical canonical source data returns the original digest.
- `certify(digest, start, end) → key` checks both endpoints against the pinned coverage and records `end - start + offset(end) - offset(start)`, with the transitions in `(start, end]`.
- `snapshot(digest)` and `certificate(key)` return JSON or an empty string if absent. Any caller can refresh or certify. A repeat of the same certificate returns the same identifier.

Inputs are whole POSIX seconds from 1972 onward. The UTC label `23:59:60` itself is outside the input encoding. Certificates cover elapsed duration between ordinary endpoints, and exclude the table expiry. This is a historical-data primitive, without clock synchronization or subsecond precision.

## Run

Stable Studionet, chain 61999, RPC `https://studio.genlayer.com/api`. Requires Node.js 22+ and Python 3.

```sh
npm ci
npm test
node scripts/example.mjs
npm run verify
```

The example signs real transactions with a new temporary test wallet. It observes the sources, certifies UTC 2016-12-31 23:59:59 to UTC 2017-01-01 00:00:00, repeats the certificate, and checks rejection at the expiry boundary. Local unit tests use an isolated VM adapter. The read-only verifier checks the deployed address, finalized receipts and stored certificate without issuing new transactions. See [deployment.json](deployment.json) and [evidence.json](evidence.json). The deployment script records a new deployment only if deliberately run in a checkout without an existing deployment record.

MIT licensed.
