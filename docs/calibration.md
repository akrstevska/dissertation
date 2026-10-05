# Calibration Reference

**Purpose:** every empirical value used to generate the synthetic dataset, with its source. If a number appears in a scenario, it must be traceable to this document.
**Scope:** EPON only (95.6% of the estate, 260 of 264 OLTs). GPON excluded from the dissertation.
**Measured:** 2026-09-21 / 2026-09-23, TK tenant, production.

**Source tags**
`[Qn]` — live query result, `aztech_query_results.md`
`[HLD]` — `aztech_hld_review.md` (HLD document + Zabbix DB verification)
`[CODE]` — `aztech_data_review.md` or `CheckOLTHealth.php`
`[RUN]` — `critical_olts_21-09-TK.txt`, health check run 2026-09-21
`[DERIVED]` — computed from the above; the derivation is stated

---

## 1. Three corrections to apply before generating anything

These are documented values in the Aztech codebase that measurement proves wrong. A generator or agent prompt that encodes the documented version produces garbage.

### 1.1 The TX power threshold is wrong

`NLQueryService` states TX normal is **−6 to −10 dBm**. Measured reality across 28,285 readings: mean **+2.27 dBm**, 98.23% between 0 and +3 dBm, mode ≈ +2.47. Only **6 readings in the entire network** fall below −6. [Q22]

Triple-confirmed: the database measurement, the OLT's own OPM Diag table (1.73–1.98 dBm), and the customer dashboard (+2.51 dBm). [Q22][HLD]

Encoding −6…−10 as a detection rule flags **~92% of the estate** as abnormal.

**Use instead:** normal `0 … +5 dBm`, suspect `< 0` or `> +5`.

### 1.2 The session baseline is not what a naive threshold would assume

**80.8% of customers open 2–3 sessions per day as normal re-authentication.** [Q11] Flapping begins at 8+, which describes 15 customers in a 30,685-customer network. Any rule that treats 3 disconnects as a fault has a false positive rate above 80%.

### 1.3 `rx_power = "0"` and `NULL` are sentinels, not readings

2,102 rows on RX and 2,400 on TX hold `'0'`. [Q2][Q22] These mean *the poll returned nothing*. Casting them numerically puts them in the "strong" band and silently converts missing data into healthy data. The codebase filters `rx_power != 0` for this reason. [CODE]

---

## 2. Network scale and inventory

| Quantity | Value | Source |
|---|---|---|
| Customer lines total (`deleted=0`) | 35,273 | [Q1] |
| Active (`active=1`) | 30,685 | [Q1] |
| Disabled (`active=0`) | 4,588 | [Q1] |
| OLTs | 264 (260 EPON V1600D) | [Q1][Q5] |
| Routers | 66, all `DHCP-RADIUS` | [Q1][Q6] |
| PON ports in use | 1,757 | [Q9] |
| EPON share | 95.60% (33,721 lines) | [Q4] |

**Scenario scale:** the synthetic estate does not need 264 OLTs. Generate 8–12 OLTs and 4–6 routers, sized and named per the real distributions below. Reuse them across scenarios so the set reads as one coherent network.

---

## 3. Topology

### 3.1 Per-OLT

| Quantity | EPON value | Source |
|---|---|---|
| PON ports per OLT | max **8**, avg 6.7 | [Q21][HLD] |
| Customers per OLT | avg 139.6, EPON max ~349 | [Q21][DERIVED] |
| Endpoints per PON port | max 64 by design, ≤32 in practice, **63 measured max** | [HLD][Q9] |

The three highest-population OLTs in [Q21] (499, 424, 404 customers) are all GPON and out of scope. The largest EPON OLT is `TK_AZ-OLT_SK_BeverliNC-01` at 349 customers across 8 ports. [DERIVED from Q21]

### 3.2 Port occupancy

Mean **19.9** customers per port, sd **14.7**, range 1–63 on EPON. [Q9]

| Customers on port | Ports | Share |
|---|---|---|
| 1–8 | 435 | 25.8% |
| 9–16 | 406 | 24.1% |
| 17–32 | 565 | 33.5% |
| 33–64 | 343 | 20.3% |

(The 8 ports above 64 in [Q9] are GPON at 1:128 — excluded.)

**Generator recipe:** draw port occupancy from the table above. For blast-radius scenarios prefer 17–32, the modal band — large enough for a pattern to be visible, small enough to list peers explicitly.

### 3.3 Interface naming

Format `EPON{slot}/{port}:{onu}` — slot always `0`, port `1`–`8`, ONU index `1`–`64` typical. [Q10]

33,528 of 33,529 EPON rows match `EPONN/N:N`. Two rows hold the literal Zabbix macro `{#IFNAME}` — an unresolved template, itself a data defect worth one scenario. [Q10]

ONU indexes are **sparse** — measured max index reaches 124 while per-port counts stay ≤63, so stale entries exist. Do not assume indexes 1…N are contiguous. [HLD]

---

## 4. Identifiers

### 4.1 MAC formats — verified, not assumed

```
crm_user_net.lineid    AA:BB:CC:DD:EE:FF   ONU MAC
crm_user_net.mac       AA:BB:CC:DD:EE:FF   CPE MAC
radcheck.username      AA:BB:CC:DD:EE:FF   == crm_user_net.mac
radcheck.lineid        AA:BB:CC:DD:EE:FF   == crm_user_net.lineid

join: UPPER(crm_user_net.mac) = UPPER(radcheck.username)
```

Colon-separated, uppercase, 17 characters. **Not stripped, not lowercased.** [Q24/Q25]

| Key pair | Match rate |
|---|---|
| `crm.mac` ↔ `radcheck.username` | 99.9% (28,493) |
| `crm.lineid` ↔ `radcheck.lineid` | 92.9% (28,492) |
| `crm.lineid` ↔ `radcheck.username` | 0.0% (5) |

`radcheck.username` is 17 chars for 30,685 of 30,687 rows; two legacy non-MAC logins exist (`testreplikacija`, `hristovski`). [Q25]

The `str_replace(':','',$lineid)` transform in `AbstractReportService` applies to the **PPPoE** path only and does not apply to this DHCP+RADIUS tenant. [Q24][CODE]

Root cause, from the HLD: MikroTik is configured for **"MAC address as Username and Password"**. [HLD §5]

### 4.2 OUI pools

**ONU MACs (`lineid`)** [Q24]

| OUI | Count |
|---|---|
| 4C:D7:C8 | 6,200 |
| 4C:EA:41 | 4,325 |
| 0C:B9:12 | 3,259 |
| 00:A1:07 | 2,607 |
| 1C:EF:03 | 2,593 |
| 80:F1:A8 | 2,575 |
| 4C:46:D1 | 2,311 |
| 78:88:8A | 1,594 |
| B4:64:15 | 1,534 |
| 70:B6:4F | 1,465 |

**CPE MACs (`mac`)** [Q24]

| OUI | Share |
|---|---|
| C8:3A:35 | 5.34% |
| 30:16:9D | 4.44% |
| 0C:B9:12 | 3.28% |
| 80:AF:CA | 3.10% |
| 50:0F:F5 | 3.00% |
| 4C:EA:41 | 2.97% |
| CC:2D:21 | 2.70% |
| 00:EB:D8 | 1.99% |
| 04:95:E6 | 1.76% |
| C0:25:2F | 1.61% |

**Three OUIs appear in both pools** — `0C:B9:12`, `4C:EA:41`, `1C:EF:03` — because the same vendors supply both ONU and CPE. This is real, not an error.

**Generator recipe:** to keep scenarios legible, draw ONU MACs from `{4C:D7:C8, 00:A1:07, 80:F1:A8, 4C:46:D1, 78:88:8A, B4:64:15, 70:B6:4F}` and CPE MACs from `{C8:3A:35, 30:16:9D, 80:AF:CA, 50:0F:F5, CC:2D:21, 00:EB:D8}` — disjoint sets, so a reader can tell at a glance which MAC is which. Randomise the last three octets; guarantee global uniqueness across the scenario set.

### 4.3 OLT naming

All 264 hosts carry the `TK_` prefix. [Q5] Observed patterns:

```
TK_AF_OLT_OH_Bogomilska-05      TK_AZ-OLT_SK_ANC-08
TK_AF-OLT_KV03                  TK_AZ_OLT-VE05
TK_AF-OLT_OH_Budva_01           TK_AZ-OLT_SK-Gradezen-01
TK_AF-OLT_SR01                  TK_AZ-OLT_BT_Jad-04
TK_AF-OLT_PP03                  TK_AZ_OLT-KO-14
```

Structure is `TK_` + operator segment (`AF` / `AZ`) + `OLT` + optional site code (`SK` Skopje, `OH` Ohrid, `BT` Bitola, `VE`, `KV`, `NE`, `KO`, `PP`, `SR`) + area + index. Separators are inconsistent (`-` and `_` both appear, in both positions) — reproduce that inconsistency; it is characteristic of the real estate.

**Management IPs:** `10.220.X.Y`. Observed: `10.220.1.3`, `10.220.22.2`, `10.220.39.3`, `10.220.39.6`, `10.220.57.6`, `10.220.60.15`, `10.220.114.5`. [RUN][HLD] Same `X` implies co-located OLTs, which is useful for site-wide scenarios.

### 4.4 Router naming

`TK_` prefix, three families. [Q6]

```
TK_Skopje01-K.Voda … TK_Skopje16-Madzari02    (numbered city + area)
TK_Bitola01-Bukovski … TK_Bitola09-Nedopirlivi
TK_Router_GE01, TK_Router_KV01, TK_Router_PS01  (site-coded)
TK_AZ_Ohrid_NC, TK_AZ_Bitola_SS02               (operator-prefixed)
```

Models: CCR1036, CCR1072, CCR2004, CCR2116, CCR2216. Confirmed live: `CCR2216-1G-12XS-2XQ`, RouterOS `7.24`. [HLD]

---

## 5. Optical signals

### 5.1 RX power — stored current value

n = 28,583 readings. [Q2]

| Statistic | Value |
|---|---|
| Mean | −20.89 dBm |
| Std dev | 4.42 |
| Min | −40.00 (clamp value) |
| Max | +3.66 (physically implausible) |

| Band | Count | Share |
|---|---|---|
| strong (> −20) | 12,286 | 40.04% |
| normal (−20 … −25) | 11,061 | 36.05% |
| degraded (−25 … −28) | 3,702 | 12.06% |
| critical (≤ −28) | 1,534 | 5.00% |
| no reading (`'0'`/NULL) | 2,102 | 6.85% |

Band boundaries are the ones the codebase uses and are correct. [CODE]

### 5.2 TX power — stored current value

n = 28,285. **See §1.1 — the documented band is wrong.** [Q22]

| Statistic | Value |
|---|---|
| Mean | +2.27 dBm |
| Std dev | 1.23 |
| Min | −95.54 (sentinel-like outlier) |
| Max | +5.58 |

| Band | Count | Share |
|---|---|---|
| < −10 | 4 | 0.01% |
| −10 … −6 | 1 | 0.00% |
| −6 … 0 | 1 | 0.00% |
| **0 … +3** | **27,784** | **98.23%** |
| +3 … +6 | 495 | 1.75% |
| no reading | 2,400 | 7.82% |

**Correct rule for this estate:** normal `0 … +5`, suspect outside it.

### 5.3 Implausible readings

RX reaches +3.66 and TX +5.58; the RX floor of −40.00 is a clamp. [Q2][Q22] Roughly 0.5–1% of generated scenarios should carry a physically impossible reading so that detection agents are tested against them rather than assuming clean input.

---

## 6. ONU telemetry — the seven Zabbix signals

All seven are collected per ONU for ~80,000 devices, and **DMAPI reads none of them**. [HLD §1]

| Signal | Graphs | Read by code? |
|---|---|---|
| Speed | 85,458 | ✗ |
| RX Power | 80,149 | ✗ |
| Temperature | 80,149 | ✗ |
| Distance | 80,149 | ✗ |
| TX Bias Current | 80,149 | ✗ |
| Online | 80,149 | ✓ |
| TX Power | 80,149 | ✗ |
| CATV | 80,146 | ✓ |
| Supply Voltage | 79,755 | ✗ |

`location` table: 168,195 rows, 55,459 distinct ONUs, 277 OLTs, spanning 2024-02-12 → 2026-09-23. History is live and current. [HLD]

### 6.1 Healthy baselines

From the OLT's OPM Diag table, four live EPON ONUs: [HLD §2]

| ONU | Distance m | Temp °C | Supply V | TX Bias mA | TX dBm | RX dBm |
|---|---|---|---|---|---|---|
| EPON0/1:2 | 6 | 23.61 | 3.46 | 11.20 | 1.98 | 1.59 |
| EPON0/3:1 | 6 | 17.32 | 3.40 | 10.80 | 1.73 | −11.16 |
| EPON0/3:2 | 6 | 22.56 | 3.44 | 9.55 | 1.97 | −8.74 |
| EPON0/3:5 | 6 | 26.05 | 3.40 | 13.00 | 1.79 | −10.00 |

| Signal | Healthy range |
|---|---|
| Distance | 6 – 365 m, **constant per customer** |
| Temperature | 17 – 26 °C |
| Supply voltage | 3.40 – 3.46 V |
| TX bias current | 9.5 – 13.0 mA |
| TX power | +1.7 – +2.5 dBm |

### 6.2 Noise floor — the most important number in this document

From one customer's 24-hour window: [HLD §2]

| Signal | last | min | avg | max | Spread |
|---|---|---|---|---|---|
| RX | −19.07 | −19.47 | −19.2531 | −18.90 | **0.57 dBm** |
| TX | 2.51 | 2.42 | 2.4996 | 2.57 | **0.15 dBm** |

**A healthy line drifts ±0.3 dBm on RX and ±0.08 dBm on TX over 24 hours.**

Synthetic healthy series must be this quiet. If baseline noise is generated wider than this, a degradation event has nothing to stand out against, trend reasoning becomes impossible, and the telemetry layer — the main advantage the multi-agent pipeline has over the monolithic baseline — is destroyed. This single parameter determines whether the evaluation measures anything.

### 6.3 Distance

Constant per customer in normal operation. 6 m (in-building) to 365 m observed. [HLD §2]

A **step change** implies a re-splice or a wrong port and is the cleanest available discriminator between a fibre-path fault and a CPE fault. Generate as a flat line with zero noise; a change is always meaningful.

### 6.4 Speed

Throughput, not link rate. Two observed profiles: [HLD §2]

```
avg 4.44 Kbps · min 136 bps · 60.2 Kbps · max 1.07 Mbps
avg 9.18 Kbps · min 144 bps · 1.1 Mbps · max 6.48 Mbps
```

Wide natural variance. A dip is not evidence of a fault on its own.

### 6.5 Laser degradation signature

`tx_bias_current` + `supply_voltage` + `temperature` are classic ageing precursors. [HLD §1]

**Rising bias current at constant TX power** is the signature: the laser compensates for reduced efficiency by drawing more current to hold output. Generate as bias climbing from ~11 mA toward and past 13 mA over days while TX power stays flat near +2.3 and RX stays normal. Distinguishes cleanly from fibre attenuation, where RX falls and bias does not move.

---

## 7. OLT device metrics

From live `host_variable`, 284 hosts. [HLD §6]

| Metric | Range | Healthy baseline |
|---|---|---|
| CPU Load | 0 – 48 % | ≈ 25 % |
| Memory Usage | 0 – 76 % | ≈ 17 % |
| Temperature | 0 – 68 °C | ≈ 42 °C |
| Uptime | up to 91 days | — |
| Firmware | e.g. `V2.03.78R` | — |

Two confirmed real hosts: one at CPU 23%, memory 16%, uptime 6d 6h; `TK_AF-OLT_SR01` (10.220.1.3) at temperature 42 °C, CPU 25%, memory 17%, uptime 83 days. [HLD §6]

**Router metrics** [HLD §6] — CPU 0–9% (75 routers), memory utilization 0%, temperature 0–64 °C (62 routers).

**Firmware is the false-critical discriminator.** §11 explains why. Assign the affected OLTs a version that differs from the healthy ones.

---

## 8. Router heartbeat

64 of 66 routers fresh (< 2 h). Two have **never** checked in: `TK_Skopje15-Madzari01`, `TK_Skopje16-Madzari02`. [Q20]

| Status | Threshold | Source |
|---|---|---|
| `ok` | < 2 h | [CODE] |
| `warning` | 2 – 4 h | [CODE] |
| `danger` | > 4 h | [CODE] |
| `never` | no record | [Q20] |

A router that has never checked in is **not** a fault — it is an unprovisioned monitoring record. Worth one scenario as a false-alarm control.

---

## 9. Sessions

### 9.1 Distribution over 24 hours [Q11]

| Sessions/day | Customers | Share | Interpretation |
|---|---|---|---|
| 1 | 2,090 | 6.8% | normal |
| **2–3** | **24,771** | **80.8%** | **normal re-auth baseline** |
| 4–7 | 889 | 2.9% | elevated, not a fault alone |
| 8–15 | 11 | 0.04% | flapping |
| 15+ | 4 | 0.01% | severe flapping |

### 9.2 Duration [Q12]

n = 378,747 over 7 days. Min 1 s, max 87,000 s (24.2 h), mean 42,856 s = **11.9 hours**.

### 9.3 Observed flapping tail [Q13]

Disconnects in 24 h for the worst ten customers: 26, 26, 25, 17, 15, 10, 10, 9, 9, 9.

**26 is the empirical ceiling.** Do not generate 50 or 100 — it is outside anything the network has produced.

**Generator recipe:** healthy customers get 2–3 sessions with ~11.9 h mean duration. Signal-related flapping gets 8–26 sessions with sharply shortened durations. Elevated-but-normal gets 4–7 — useful as a distractor in scenarios where the real fault lies elsewhere.

---

## 10. Traffic

### 10.1 Distribution, last 7 days [Q14]

| Band | Download entries | Upload entries |
|---|---|---|
| < 100 MB | 67,757 | 35,697 |
| 100–500 MB | 73,317 | 12,730 |
| 500 MB–1 GB | 27,552 | 12,971 |
| 1–3 GB | 18,476 | 38,533 |
| 3–10 GB | 5,436 | 59,926 |
| 10 GB+ | 2,306 | 34,987 |

### 10.2 Per-customer averages, 30 days [Q15]

| Direction | Min | Max | Mean | Customers |
|---|---|---|---|---|
| Download | 0.0 | 220,283 MB | **952.6 MB** | 29,447 |
| Upload | 0.0 | 1,352,097 MB | **6,198.9 MB** | 29,447 |

### 10.3 The direction labels are inverted

Upload exceeds download 6.5:1, which is backwards for residential access. `LogSession.traffic_download` is populated from `acctinputoctets`, which in RADIUS means traffic *into the NAS* — i.e. customer **upload**. [Q14][CODE]

**Reproduce the inversion as it exists in production.** It is a real data-quality defect and part of the environment the agents must cope with. Agents should not treat absolute direction as reliable evidence; the **trend** carries the signal.

---

## 11. OLT health check — behaviour and defects

Behaviour is taken from `CheckOLTHealth.php` directly. [CODE] Reproducing it faithfully matters because four scenarios depend on its failure modes.

### 11.1 Decision sequence

```
1. ping -c 3 -W 2          → fail ⇒ offline, "OLT is not reachable (ping failed)"
2. SNMP get sysUpTime      → fail ⇒ critical, "SNMP community string not accessible,
                                               OLT does not respond to SNMP queries"
3. sample ONE ONU per PON port (id 1 if online, else first online found)
4. per sample: read online OID; if it returns 1, read RX and TX OIDs
5. all sampled PONs failed ⇒ critical, "All PONs failed (N/N)"
   otherwise                ⇒ healthy, error_description = null
```

### 11.2 Four defects to reproduce

**(a) `snmp_community_ok` and `snmp_response_ok` are always equal.** Both derive from one `sysUpTime` get. The two error strings always appear together, exactly as the November data shows. The check cannot distinguish a wrong community string from an unresponsive agent. [CODE][Q19]

**(b) All-or-nothing status.** `overall_status` is `critical` only when `count(failedPons) === count(testUsers)`. **7 of 8 PONs failing yields `healthy` with `error_description: null`** — while `healthy_pons: 1` and `total_pons_tested: 8` sit in the same record. A genuine single-port outage affecting up to 63 customers is labelled healthy, and the contradiction is visible only in the detail fields. [CODE]

**(c) One-ONU sampling.** Each port's verdict rests on a single device. A dead sample ONU condemns a healthy port of 30 customers; a healthy sample hides 30 broken neighbours. [CODE]

**(d) Hardcoded OID subtree.** `checkONUOnlineStatus` reads `1.3.6.1.4.1.37950.1.1.5.12.1.25.1.4.{slot}.{onu}` and requires exactly `1`. On a firmware version where that subtree is absent, the call returns "No Such Instance", the function returns early, RX and TX are never attempted, and **every sampled ONU on every port fails** → "All PONs failed (8/8)" on a healthy OLT with all customers in service. **Confirmed by Aztech as a firmware version issue, not an outage.** [CODE][RUN]

### 11.3 Real run data

| Run | Healthy | Critical | Offline |
|---|---|---|---|
| 2025-10-01 | 188 | 5 | 13 |
| 2025-10-06 | 188 | 19 | 7 |
| 2025-11-11 | 214 | 12 | 7 |
| 2026-09-21 | — | 6 | 4 |

[Q19][RUN]

Of the 12 criticals in November, 10 read "All PONs failed" with ping and SNMP both OK — the signature of defect (d). [Q19]

**Error strings — use verbatim:**
```
"All PONs failed (8/8)"
"SNMP community string not accessible, OLT does not respond to SNMP queries"
"OLT is not reachable (ping failed)"
```

Real affected hosts from the 2026-09-21 run, with PON counts: [RUN]
```
TK_AF_OLT_OH_Bogomilska-05  10.220.57.6   7/7
TK_AZ-OLT_SK_ANC-08         10.220.114.5  8/8
TK_AZ-OLT_BT_SS_03-05       10.220.39.6   4/4
TK_AZ-OLT_BT_SS_03-02       10.220.39.3   7/7
TK_AZ-OLT_test01            10.220.22.2   1/1
TK_AZ_OLT-KO-14             10.220.60.15  7/7
```

Note the PON counts vary (1, 4, 7, 8) — `total_pons_tested` counts ports that yielded a sample, not the physical port count.

---

## 12. RADIUS

### 12.1 Coverage [Q16]

| Metric | Value |
|---|---|
| Active customers with a MAC | 28,532 |
| Distinct `radcheck` usernames | 30,686 |
| Matched | 28,493 |
| **Missing from RADIUS** | **39** |
| **Orphan in RADIUS** | **2,193** |
| Coverage | 99.86% |

### 12.2 Suspension state [Q17][Q18]

| Metric | Value |
|---|---|
| `framed_pool` empty | 28,659 |
| `framed_pool = pool_Disable_Users` | 2,038 |
| CRM-disabled with a MAC (excl. `profile_CATV`) | 1,588 |
| — also pooled (consistent) | 1,370 |
| — **not pooled (still being served)** | **218** |
| Pooled but CRM active or absent | 668 |
| Consistency | 86.27% |

### 12.3 IP pools [HLD §4]

| Pool | Range | Meaning |
|---|---|---|
| `pool_Users` | 10.5.50.2 – 254 | standard |
| `pool-Users_FixedIP` | 10.5.51.2 – 254 | static IP |
| `pool-Users_JavnIP_01` | 10.5.52.2 – 254 | public IP |
| `pool_Disable_Users` | **10.200.200.2 – 254** | suspended |

Bridges: `bridge-ONU_Users` (10.5.50.1/24, 10.5.51.1/24, 10.5.52.1/24), `bridge-TR69` (10.5.101.1/24), `bridge-VoIP` (10.5.102.1/24), `bridge-Disable Users` (10.200.200.1/24), `bridge-Managment` (10.226.1.1/24).

**The IP makes suspension verifiable without trusting any status flag.** A customer with `active: 0` in CRM holding an address in `10.5.50.0/24` is provably still being served. This is the ground truth mechanism for the 218 cases.

### 12.4 Authentication flow [HLD §5]

```
1. CPE connects
2. DHCP from local MikroTik pool
3. DHCP script checks for pre-existing temporary users
4. Script creates/updates UserMAC in RADIUS
5. MikroTik → Access-Request → PRIMARY FreeRADIUS
6. FreeRADIUS evaluates radcheck + radreply
7. DB queried for username, password, pools, static IPs
8. Authorization policies applied
9. Accept/Reject → MikroTik
10. On Accept: accounting starts, rate limits + pool + IP applied
```

Failure points, each a candidate scenario: step 3 stale temporary user; step 4 script failure → the 39 missing entries; step 6 wrong `Framed-Pool` → the 218 cases; step 9 reject flood.

**High availability:** Primary + Secondary FreeRADIUS, each with its own database, **master–slave replication in both directions**. MikroTik fails over to Secondary when Primary is unreachable. [HLD §5]

This produces two scenarios that no single signal reveals: silent failover, and **replication lag** — a customer enabled on master but not yet on slave authenticates inconsistently depending on which server answers.

---

## 13. Service profiles and ONU models

### 13.1 Profiles [Q7]

| Profile | Share |
|---|---|
| `profile_20M` | 55.67% |
| `profile_40M` | 15.28% |
| `profile_30M_1M` | 10.64% |
| `profile_CATV` | 6.32% |
| `profile_80M` | 5.71% |
| `profile_300M` | 4.90% |
| `profile_100M` | 0.58% |
| `profile_VOIP_CATV` | 0.45% |
| `profile_1G` | 0.39% |
| `profile_1G-Backup` | 0.05% |
| `profile_VOIP` | 0.02% |

Draw weighted. `profile_20M` should dominate, as it does in production.

### 13.2 ONU models [Q8]

| Model | Type | CATV | VoIP | Count |
|---|---|---|---|---|
| Aztech 1G + CATV | Bridge | 1 | 0 | 22,158 |
| JM 1G + CATV + WiFi + POTs | Router | 1 | 1 | 4,266 |
| Aztech 1G | Bridge | 0 | 0 | 3,705 |
| Aztech 2GE + WiFi(dual band) + POTs + CATV | Router | 1 | 1 | 1,208 |
| Infel 1G + CATV | Bridge | 1 | 0 | 1,140 |
| JM 1G + CATV | Bridge | 1 | 0 | 774 |
| Raisecom 1G | Bridge | 0 | 0 | 594 |
| JM 1G | Bridge | 0 | 0 | 504 |
| Aztech 1G + CATV-xPON | Bridge | 1 | 0 | 410 |
| Aztech 1G + CATV + WiFi + POTs | Router | 1 | 1 | 300 |

`has_catv` and `has_voip` are determined by the model and **must agree with it**. A Bridge ONU with `has_voip = 1` is invalid except for `Huawei 1G + POTs`.

ONU type strings visible on the OLT: `2GE+1POTS+8WiFi+CATV`, `1GE+CATV`, `1GE`. [HLD §7]

---

## 14. VLANs [HLD §3]

| VLAN | Purpose |
|---|---|
| 1 | Parking / blackhole; **not permitted on uplinks** |
| 46 | **Factory-default** CPE management (as shipped) |
| 100 | OLT local management |
| **1XXY** | Data VLAN per PON port — `XX` = OLT id, `Y` = port (e.g. 1011–1018) |
| 1998 | Voice |
| 1999 | **Provisioned** CPE management |

12 production VLANs per OLT. One customer VLAN per PON port, deliberately, to cap MAC-table load.

Router VLAN interface naming: `vlan1011-AZ_OLT01-PON1` — encodes VLAN, OLT and port in one string.

**VLAN 46 → 1999 is a ready-made scenario.** A CPE ships on 46; TR-069/ACS migrates it to 1999 during provisioning. A CPE still on 46 is stuck provisioning — unambiguous, and requires correlating ACS state, OLT VLAN and DHCP to diagnose.

---

## 15. Other state

### 15.1 ONU online status [Q3]

| Status | Count | Share |
|---|---|---|
| 1 = online | 29,198 | 95.15% |
| 0 = offline | 1,487 | 4.85% |

**Baseline offline rate is 4.85%.** An OLT of 298 customers carries ~14 offline ONUs on a perfectly normal day. Background noise, not a fault — and an important distractor for OLT-scope scenarios.

(The polarity inversion documented for GPON/V1600G does not apply; EPON only.)

### 15.2 ONU authentication table [HLD §7]

Fields available on the OLT but not stored by DMAPI:

| Field | Values |
|---|---|
| `Status` | Online, Offline |
| `RTT(TQ)` | 51, 52, 53, 98, 99 observed |
| `Auth Flag` | Auth, Unauth |
| `Exchange` | **Finish**, **MPCP DEREG** |
| `Auth Mode` | None |

`MPCP DEREG` is a real deregistration reason code observed on a real offline ONU. `Auth Flag = Unauth` is a second, independent offline indicator. `RTT(TQ)` correlates with Distance.

### 15.3 CATV [Q23]

| `catv_service` | `catv_synced` | Count | Share |
|---|---|---|---|
| 1 | 1 | 21,978 | 71.62% |
| 0 | 1 | 8,623 | 28.10% |
| **1** | **0** | **52** | 0.17% |
| **0** | **0** | **32** | 0.10% |

84 drift cases total.

`catv_service`, `catv_synced`, `active`, `deleted`, `onu_status` are all `bit(1)` — cast to unsigned or they render as unprintable bytes. [Q23]

### 15.4 Zabbix severity [HLD §6]

Six levels: `Not classified`, `Information`, `Warning`, `Average`, `High`, `Disaster`. 95 triggers, 4,801 items, 11 hosts at capture. Active problems were all "Unreachable by ICMP ping", durations ~12 h 22 m. Notification channels configured: Mail, SMS, Jira, MS Teams.

DMAPI never reads Zabbix triggers.

---

## 16. Known production defects — with real counts

Each of these is a documented condition in the live network, which means the corresponding scenario has empirical grounding rather than being invented.

| Defect | Real count | Source |
|---|---|---|
| Interfaces carrying >1 live customer | **644** (1,296 customers, worst 3 on one slot) | [HLD §3] |
| CRM-disabled but still served | **218** | [Q18] |
| Orphan `radcheck` entries | **2,193** | [Q16] |
| Missing `radcheck` entries | **39** | [Q16] |
| CATV sync drift | **84** | [Q23] |
| Routers never checked in | **2** | [Q20] |
| Unresolved `{#IFNAME}` interface macro | **2** | [Q10] |
| OLT health false criticals (firmware/OID) | 6 of 10 non-healthy on 2026-09-21 | [RUN] |
| `olt_health_results` staleness before rerun | 10 months (last 2025-11-11) | [Q19] |

---

## 17. Generator recipes

### 17.1 A healthy customer

```
profile          weighted draw, §13.1 (profile_20M ~56%)
onu_model        weighted draw, §13.2; has_catv/has_voip must agree
lineid           ONU OUI pool, §4.2, random last 3 octets
mac              CPE OUI pool, §4.2, random last 3 octets
interface        EPON0/{1-8}:{1-64}
rx_power         N(−20.89, 4.42), clipped to [−28, −18]
tx_power         N(+2.3, 0.4), clipped to [0, +5]
onu_status       1
sessions_24h     2 or 3
session_duration ~11.9 h mean
distance         constant, U(6, 365)
temperature      U(17, 26)
supply_voltage   U(3.40, 3.46)
tx_bias_current  U(9.5, 13.0)
radius           radcheck exists, framed_pool null, IP in 10.5.50.0/24
```

### 17.2 A healthy telemetry series

```
rx_power[t]  = rx_base + N(0, 0.15)      # ±0.3 over 24h
tx_power[t]  = tx_base + N(0, 0.04)   # ±0.08 over 24h
distance[t]  = constant, zero noise
bias[t]      = bias_base + N(0, 0.15)
voltage[t]   = voltage_base + N(0, 0.01)
temperature[t] = temp_base + diurnal(±2 °C) + N(0, 0.3)
```

Tight noise is mandatory — see §6.2.

### 17.3 A PON port population

```
occupancy    draw from §3.2 histogram, prefer 17–32 for blast-radius cases
onu_indexes  sparse — sample from 1..64, do not use contiguous 1..N
peers        5–10 listed, or all if occupancy < 10; subject must be included
peer rx      N(−20.89, 4.42) clipped; must be normal unless the scenario says otherwise
```

### 17.4 An OLT

```
pon_ports         1–8, typically 6–8
customers         sum of per-port occupancy, target 100–350
onu_offline_count round(total × 0.0485), jittered ±40%
cpu_load          N(25, 4), clip [0, 48]
memory_usage      N(17, 3), clip [0, 76]
temperature       N(42, 5), clip [0, 68]
uptime_days       U(1, 91)
firmware          "V2.03.78R" for healthy; a different version for OID-mismatch scenarios
```

### 17.5 Degradation events

| Fault | Signature |
|---|---|
| Fibre degradation | RX falls over days; TX, bias, voltage, distance flat; peers normal |
| Laser degradation | bias rises past 13 mA; TX flat; RX normal; temperature may rise |
| Distance change | step change in distance; everything else normal |
| ONU offline | `online: 0`, `responds: true`, `auth_flag: Unauth`, `exchange: MPCP DEREG` |
| PON port failure | multiple ONUs `online: 0` with `responds: true`; OLT healthy |
| OID/firmware mismatch | every ONU `responds: false` **uniformly**; no RX/TX attempted; customers online in CRM and passing traffic |
| Session flapping (signal) | 8–26 sessions/24 h, short durations, RX degraded |
| Session flapping (auth) | 8–26 sessions/24 h, RX normal, RADIUS mismatch present |
| Suspended but serving | `active: 0`, `framed_pool: null`, IP in 10.5.50.0/24 |
| Duplicate slot | two `lineid`s on one `interface` in CRM; live probe shows one |
| Stuck provisioning | `customer_vlan_actual: 46`, expected `1XXY` |

---

## 18. Deferred

| Source | Why | Status |
|---|---|---|
| Graylog | HLD §3.6 is an empty heading — no streams, no index names, no field mapping | Future work. MPCP deregistration is already reachable via `snmp_live.onu.exchange`. |
| GenieACS / TR-069 | Documented REST NBI on 7557 with a Faults tab, but no production sample available | Future work. Would supply CPE-side reachability and TR-143 active diagnostics. |
| Zabbix triggers | 95 triggers exist and fire; DMAPI never reads them | Noted in Chapter 6 as available signal. |