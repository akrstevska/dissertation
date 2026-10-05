# Scenario Schema

**Status:** v1 — the contract for the synthetic dataset. MCP servers, agents, and the evaluation harness all build against this.
**Scope:** EPON only. GPON is out of scope for this dissertation.
**Companion docs:** `calibration.md` (where every value comes from), `fault-taxonomy.md` (the fault types and their discriminators).

---

## 1. What a scenario is

A scenario is one JSON file describing the complete observable state of the network at a single moment, plus the known correct answer. It is the synthetic equivalent of one real network event.

Two principles govern every field:

**Agents never see ground truth.** The `ground_truth` section is consumed only by the evaluation harness. No MCP server exposes it, and no agent prompt contains it.

**Every section maps to exactly one MCP server.** A scenario is partitioned by which server serves it. This is what makes the MCP abstraction real rather than decorative — the agent's access to data is constrained by which server it is given, and that constraint is what forces the pipeline to reason rather than read.

| Scenario section | Served by | Data freshness |
|---|---|---|
| `subscriber` | Network Data Server | current, stored |
| `network_state` | Network Data Server | current, stored (polled) |
| `peers` | Network Data Server (CRM view) + Device Probe Server (live view) | both |
| `telemetry` | Telemetry Server | historical time-series |
| `snmp_live` | Device Probe Server | live, on-demand |
| `session_auth` | Session & Auth Server | current + recent history |
| `ground_truth` | **nothing** | evaluation only |

---

## 2. Top-level structure

```json
{
  "metadata": { },
  "trigger": { },
  "subscriber": { },
  "network_state": { },
  "peers": { },
  "telemetry": { },
  "snmp_live": { },
  "session_auth": { },
  "ground_truth": { }
}
```

All sections are required. A section that is not relevant to a scenario is present but may contain nulls — an absent reading is itself a signal, and agents must handle it.

---

## 3. `metadata`

Identifies the scenario and fixes its reference time.

```json
{
  "scenario_id": "FCR-002",
  "fault_type": "olt_health_false_critical",
  "difficulty": "hard",
  "captured_at": "2026-09-21T19:31:34Z",
  "description": "Health check reports all PONs failed on an OLT whose customers are all online and passing traffic.",
  "tests": [
    "Does the pipeline verify an alarm before acting on it?",
    "Does it distinguish a monitoring defect from a service outage?"
  ]
}
```

| Field | Type | Notes |
|---|---|---|
| `scenario_id` | string | `PREFIX-NNN`. Prefix is the fault family (see `fault-taxonomy.md`). Unique across the set. |
| `fault_type` | string | One of the enum in `fault-taxonomy.md`. `no_fault` for the false-alarm controls. |
| `difficulty` | enum | `easy` \| `medium` \| `hard` |
| `captured_at` | ISO 8601 UTC | The scenario's "now". All timestamps and time-series windows are relative to this. |
| `description` | string | One sentence, human-readable. |
| `tests` | array of string | What reasoning capability this scenario probes. Used in Chapter 5 to group results. |

**Difficulty definitions** — these are not vibes, they are structural:

- **easy** — one signal is decisively anomalous, everything else is normal or clearly downstream of it. Correct diagnosis is reachable from the cached layer alone.
- **medium** — the initial signal is consistent with two or more fault types. Disambiguation requires querying a second data layer (live probe, telemetry, or session/auth).
- **hard** — one of: two faults present simultaneously; a cascade where the symptom presents at a different layer than the cause; a data source that actively contradicts another; or an alarm that is itself wrong.

---

## 4. `trigger`

How the pipeline was invoked. This is the only input the Detection Agent receives.

```json
{
  "type": "customer_complaint",
  "input": {
    "lineid": "4C:D7:C8:A1:3F:02",
    "complaint": "Internet keeps dropping since yesterday"
  }
}
```

| `type` | `input` fields | Used for |
|---|---|---|
| `customer_complaint` | `lineid`, `complaint` (free text) | Single-customer faults |
| `scheduled_scan` | `scope` (`olt` \| `router` \| `network`), `target` (host or null) | Sweeps that may find nothing |
| `health_check_alarm` | `olt_host`, `overall_status`, `error_description` | OLT health family — the alarm is the input, and may be wrong |
| `threshold_breach` | `signal`, `lineid` or `olt_host`, `value` | Automated monitoring hit |

The trigger carries no diagnosis and no hint. `health_check_alarm` deliberately carries a *claim* (`overall_status: critical`) that the pipeline must verify rather than accept.

---

## 5. `subscriber`

Customer identity and network placement. Mirrors `crm_user_net` joined to `crm_user`, `olt`, `router`, `onu`.

```json
{
  "customer_id": 20418,
  "lineid": "4C:D7:C8:A1:3F:02",
  "mac": "C8:3A:35:7B:11:E4",
  "interface": "EPON0/3:14",
  "olt_id": "10417",
  "olt_host": "TK_AZ-OLT_SK_ANC-08",
  "olt_ip": "10.220.114.5",
  "olt_technology": "EPON",
  "olt_model": "V1600D",
  "router_id": 31,
  "router_name": "TK_Skopje13-ANC01",
  "profile": "profile_20M",
  "active": 1,
  "deleted": 0,
  "onu_model": "Aztech 1G + CATV",
  "onu_type": "Bridge",
  "has_catv": 1,
  "has_voip": 0,
  "catv_service": 1,
  "catv_synced": 1,
  "city": "Skopje",
  "area": "ANC"
}
```

| Field | Type | Constraints |
|---|---|---|
| `customer_id` | int | Synthetic. Never a real ID. |
| `lineid` | string | **ONU MAC.** `AA:BB:CC:DD:EE:FF`, colon-separated, uppercase, 17 chars. OUI from the ONU list in `calibration.md`. |
| `mac` | string | **CPE MAC.** Same format. Equals `radcheck.username`. OUI from the CPE list. Distinct OUI pool from `lineid`. |
| `interface` | string | `EPON{slot}/{port}:{onu}`. Slot is `0`. Port `1`–`8`. ONU index `1`–`64` typical, sparse values to `124` permitted. |
| `olt_id` | string | The `ext_id`. Numeric string. |
| `olt_host` | string | `TK_` prefixed. See naming patterns in `calibration.md`. |
| `olt_ip` | string | `10.220.X.Y` management range. |
| `olt_technology` | const | Always `"EPON"`. |
| `olt_model` | const | Always `"V1600D"`. |
| `router_id` | int | |
| `router_name` | string | `TK_` prefixed. |
| `profile` | enum | Weighted by the real distribution in `calibration.md`. |
| `active` | 0 \| 1 | `bit(1)` in source. `0` = suspended in CRM. |
| `deleted` | 0 \| 1 | Always `0` in scenarios. |
| `onu_model` | string | From the real model list. |
| `onu_type` | enum | `Bridge` \| `Router` — determined by `onu_model`. |
| `has_catv`, `has_voip` | 0 \| 1 | Determined by `onu_model`. Must agree with it. |
| `catv_service` | 0 \| 1 | Whether CATV is subscribed. |
| `catv_synced` | 0 \| 1 | Whether the device state matches. `0` is the drift condition. |
| `city`, `area` | string | Derived from `olt_host`. Cosmetic. |

---

## 6. `network_state`

Current stored values — what the database holds right now. This is the layer the Detection Agent screens on. It can be stale.

```json
{
  "onu_status": 1,
  "rx_power": "-26.40",
  "tx_power": "2.31",
  "reading_age_minutes": 47,

  "olt_health": {
    "olt_ip": "10.220.114.5",
    "olt_host": "TK_AZ-OLT_SK_ANC-08",
    "olt_technology": "EPON",
    "olt_ext_id": "10417",
    "ping_ok": true,
    "snmp_community_ok": true,
    "snmp_response_ok": true,
    "total_pons_tested": 8,
    "healthy_pons": 0,
    "failed_pons_list": ["EPON0/1:1","EPON0/2:1","EPON0/3:1","EPON0/4:1","EPON0/5:1","EPON0/6:1","EPON0/7:1","EPON0/8:1"],
    "error_description": "All PONs failed (8/8)",
    "overall_status": "critical",
    "run_date": "2026-09-21"
  },

  "olt_metrics": {
    "cpu_load": 24,
    "memory_usage": 17,
    "temperature": 41,
    "uptime_days": 83,
    "firmware": "V2.03.78R",
    "firmware_date": "2024-06-11"
  },

  "router_state": {
    "name": "TK_Skopje13-ANC01",
    "model": "CCR2216-1G-12XS-2XQ",
    "os_version": "7.24",
    "last_checkin": "2026-09-21T19:12:00Z",
    "hours_since_checkin": 0.3,
    "heartbeat_status": "ok",
    "cpu_usage": 4,
    "memory_utilization": 0,
    "temperature": 38
  }
}
```

### Field rules that matter

`onu_status` — `1` online, `0` offline. EPON only, so no polarity inversion.

`rx_power` and `tx_power` are **strings**, matching the source column type. Two decimals.

**`"0"` and `null` are no-reading sentinels, not values.** They mean the poll failed or returned nothing. They must never be treated as a numeric reading. A generator that emits `"0"` for a healthy line is producing a bug; a generator that emits `"0"` deliberately is producing a *missing data* scenario, which is legitimate and should be labelled as such in ground truth.

**When SNMP fails, the poller writes 0 — it does not stop.** Every stored `onu_status`, power and telemetry value under an OLT that does not answer SNMP reads 0 from the failure hour on, and `reading_age_minutes` stays fresh because the poller keeps writing. `null` in a series is reserved for a genuine collection gap, declared in `availability.gaps`. (Engineer review, October 2026; applied to OF-001 and OF-002.)

`reading_age_minutes` — how stale the cached reading is. This is what makes cached-vs-live discrepancy meaningful. Typical 0–180. Larger values are themselves a signal.

`olt_health` — the record shape is taken verbatim from `CheckOLTHealth::saveOLTCheckResult()`. Three behaviours of that check must be reproduced faithfully:

1. `overall_status` is `critical` **only when every sampled PON failed**. If 7 of 8 failed, the check writes `healthy` with `error_description: null` — while `healthy_pons: 1` and `total_pons_tested: 8` remain in the same record. That contradiction is real and is the basis of a scenario family.
2. `snmp_community_ok` and `snmp_response_ok` are set from a single `sysUpTime` get, so they are **always equal**. Never emit them differing.
3. The check samples **one ONU per PON port** — ONU id 1 if online, else the first online ONU found. A port's verdict rests on one device.

`olt_metrics` — healthy baseline is CPU ≈ 25, memory ≈ 17, temperature ≈ 42. Estate ceilings are CPU 48, memory 76, temperature 68. `firmware` is a discriminator in the false-critical family.

`router_state.heartbeat_status` — `ok` < 2h, `warning` 2–4h, `danger` > 4h, `never` for a router that has never checked in.

---

## 7. `peers`

Other customers on the same PON port and the wider OLT. This is how blast radius is established, and it is deliberately split into a CRM view and a live view because the two can disagree.

```json
{
  "interface_port": "EPON0/3",
  "crm_view": {
    "total_on_port": 22,
    "customers": [
      {"lineid": "4C:EA:41:0B:77:19", "interface": "EPON0/3:1",  "onu_status": 1, "rx_power": "-19.80", "active": 1},
      {"lineid": "0C:B9:12:5C:20:AA", "interface": "EPON0/3:2",  "onu_status": 1, "rx_power": "-21.15", "active": 1},
      {"lineid": "4C:D7:C8:A1:3F:02", "interface": "EPON0/3:14", "onu_status": 1, "rx_power": "-26.40", "active": 1}
    ]
  },
  "olt_population": {
    "total_customers": 298,
    "pon_ports_in_use": 8,
    "customers_per_port": {"EPON0/1": 41, "EPON0/2": 38, "EPON0/3": 22, "EPON0/4": 47, "EPON0/5": 35, "EPON0/6": 40, "EPON0/7": 39, "EPON0/8": 36},
    "onu_online_count": 291,
    "onu_offline_count": 7
  },
  "duplicate_slot_conflict": null
}
```

| Field | Notes |
|---|---|
| `interface_port` | The port prefix, no ONU index. |
| `crm_view.total_on_port` | Full count. Real distribution: mean 19.9, sd 14.7, max 63 on EPON. |
| `crm_view.customers` | A representative subset, not necessarily all. Include enough to establish the pattern — typically 5–10, or all if the port is small. The subject customer must be present. |
| `olt_population` | Summary across the whole OLT. Required for OLT-scope scenarios; still present for single-customer ones. |
| `onu_online_count` / `onu_offline_count` | Must sum to `total_customers`. Network baseline offline rate is 4.85%. |
| `duplicate_slot_conflict` | `null`, or an object listing two or more `lineid`s CRM places on the same `interface`. 644 such interfaces exist in production. |

The live counterpart of `crm_view` lives in `snmp_live.pon_probe` — see below. **When those two disagree, that disagreement is the finding.**

---

## 8. `telemetry`

Zabbix time-series. Seven per-ONU optical signals exist in production and are currently unread by any Aztech code. They are the richest evidence available to the Diagnosis Agent and the main reason trend reasoning is possible at all.

```json
{
  "onu_series": {
    "interval": "1h",
    "window_hours": 168,
    "series_start": "2026-09-14T19:00:00Z",
    "rx_power":        [-19.2, -19.3, -19.1, "...", -26.4],
    "tx_power":        [2.49, 2.51, 2.47, "...", 2.31],
    "temperature":     [22.1, 22.4, 21.9, "...", 23.8],
    "distance":        [188, 188, 188, "...", 188],
    "tx_bias_current": [11.2, 11.2, 11.3, "...", 11.4],
    "supply_voltage":  [3.44, 3.44, 3.43, "...", 3.44],
    "speed_kbps":      [4.41, 6.02, 3.88, "...", 0.14]
  },
  "olt_series": {
    "interval": "1h",
    "window_hours": 168,
    "series_start": "2026-09-14T19:00:00Z",
    "cpu_load":    [24, 23, 25, "...", 24],
    "memory_usage":[17, 17, 17, "...", 17],
    "temperature": [41, 41, 42, "...", 41]
  },
  "availability": {
    "onu_series_complete": true,
    "gaps": []
  }
}
```

### Rules

Arrays are **ordered oldest → newest**, length exactly `window_hours / interval`. `null` marks a collection gap; gaps are legitimate and must be listed in `availability.gaps` as `{"signal": "rx_power", "from_index": 40, "to_index": 46}`.

**Baseline stability is the point.** A healthy line drifts ±0.3 dBm on RX and ±0.08 dBm on TX across 24 hours. Synthetic healthy series must be this quiet, otherwise a degradation event has nothing to stand out against and the trend signal is worthless.

`distance` is **constant per customer** in normal operation, in the 6–365 m range. A step change implies a re-splice or a wrong port and is physically meaningful — it is the cleanest discriminator between a fibre-path fault and a CPE fault.

`tx_bias_current`, `supply_voltage` and `temperature` together are the laser-degradation precursor bundle. Healthy ranges: bias 9.5–13.0 mA, supply 3.40–3.46 V, ONU temperature 17–26 °C. Rising bias at constant TX power is the classic ageing signature.

`speed_kbps` is throughput, not link rate. Wide natural variance — do not treat a dip as a fault on its own.

---

## 9. `snmp_live`

What a live SNMP query returns at `captured_at`. This is the verification layer. It may confirm or contradict `network_state`, and the contradiction is frequently the whole scenario.

```json
{
  "onu": {
    "responds": true,
    "online": 1,
    "rx_power": -27.10,
    "tx_power": 2.28,
    "auth_flag": "Auth",
    "exchange": "Finish",
    "rtt_tq": 52
  },

  "olt": {
    "ping_ok": true,
    "snmp_responds": true,
    "sys_uptime_seconds": 7171200,
    "oid_subtree_responds": true
  },

  "pon_probe": {
    "interface_port": "EPON0/3",
    "onus": [
      {"onu_index": 1,  "online": 1, "rx_power": -19.81, "tx_power": 2.50, "responds": true},
      {"onu_index": 2,  "online": 1, "rx_power": -21.14, "tx_power": 2.44, "responds": true},
      {"onu_index": 14, "online": 1, "rx_power": -27.10, "tx_power": 2.28, "responds": true}
    ]
  },

  "vlan_walk": {
    "responds": true,
    "vlans_present": [1, 46, 100, 1011, 1012, 1013, 1014, 1015, 1016, 1017, 1018, 1998, 1999],
    "customer_vlan_expected": 1013,
    "customer_vlan_actual": 1013
  }
}
```

| Field | Notes |
|---|---|
| `onu.responds` | `false` means the OID returned nothing. Distinct from `online: 0`, which is a definite negative answer. The distinction matters. |
| `onu.online` | `1` \| `0` \| `null` when `responds` is false. |
| `onu.rx_power` / `tx_power` | **Numbers here, not strings.** Live probe values are typed; stored values are strings. Preserve the difference. |
| `onu.auth_flag` | `Auth` \| `Unauth`. An independent offline indicator, useful for cross-checking `online`. |
| `onu.exchange` | `Finish` \| `MPCP DEREG`. `MPCP DEREG` is a real deregistration reason code visible on the OLT. |
| `onu.rtt_tq` | Round-trip timing quantum. Observed 51–99. Correlates with `distance`. |
| `olt.oid_subtree_responds` | **The false-critical discriminator.** `false` means the ONU parameter subtree is absent — a firmware-version mismatch — while the OLT itself is perfectly healthy. When this is `false`, every PON in `pon_probe` returns `responds: false` *uniformly*, and the health check reports "All PONs failed". A genuine outage looks different: `responds` is `true` with `online: 0`, and the pattern is rarely uniform across all eight ports. |
| `pon_probe.onus` | The live view of the port. Compare against `peers.crm_view`. |
| `vlan_walk.customer_vlan_expected` | Derived from the PON port: `1XXY` where `Y` is the port number. |
| `vlan_walk.customer_vlan_actual` | `46` here means stuck provisioning — the CPE never migrated to `1999`/its data VLAN. |

---

## 10. `session_auth`

Sessions, RADIUS state, and traffic.

```json
{
  "sessions": {
    "count_24h": 11,
    "count_7d": 34,
    "avg_duration_minutes": 62,
    "last_disconnect": "2026-09-21T18:04:00Z",
    "recent": [
      {"start": "2026-09-21T18:09:00Z", "end": null, "duration_s": 4920, "ip": "10.5.50.117"},
      {"start": "2026-09-21T16:51:00Z", "end": "2026-09-21T18:04:00Z", "duration_s": 4380, "ip": "10.5.50.117"}
    ]
  },

  "radius": {
    "radcheck_exists": true,
    "username": "C8:3A:35:7B:11:E4",
    "lineid_in_radius": "4C:D7:C8:A1:3F:02",
    "framed_pool": null,
    "assigned_ip": "10.5.50.117",
    "crm_consistent": true,
    "mismatches": []
  },

  "traffic": {
    "download_mb_daily": [980, 1010, 870, 940, 410, 180, 62],
    "upload_mb_daily": [6100, 6240, 5980, 6050, 2800, 1210, 390],
    "monthly_avg_download_mb": 953,
    "monthly_avg_upload_mb": 6199,
    "pon_port_traffic": {"current_mbps": 210, "avg_mbps": 195, "peak_mbps": 640}
  }
}
```

### Session baselines — read this before setting any threshold

The production distribution over 24 hours:

| Sessions/day | Customers | Share |
|---|---|---|
| 1 | 2,090 | 6.8% |
| 2–3 | 24,771 | **80.8%** |
| 4–7 | 889 | 2.9% |
| 8–15 | 11 | 0.04% |
| 15+ | 4 | 0.01% |

**2–3 sessions per day is normal re-authentication, not a fault.** Flapping begins around 8+, which describes 15 customers in the entire network. 4–7 is elevated and worth noting but is not on its own a fault. Mean session length is 11.9 hours.

Any scenario or agent prompt that flags 3 disconnects as flapping is wrong by two orders of magnitude.

### RADIUS rules

`username` **equals `subscriber.mac`** — colon-separated, uppercase, 17 characters. It is not stripped and not lowercased. Production coverage is 99.86%.

`framed_pool` — `null` for normal service, `"pool_Disable_Users"` for suspension.

`assigned_ip` is bound to the pool and is therefore a checkable label:

| Pool | Range | Meaning |
|---|---|---|
| `pool_Users` | 10.5.50.2–254 | standard |
| `pool-Users_FixedIP` | 10.5.51.2–254 | static IP |
| `pool-Users_JavnIP_01` | 10.5.52.2–254 | public IP |
| `pool_Disable_Users` | 10.200.200.2–254 | suspended |

A customer with `active: 0` in CRM but an IP in `10.5.50.0/24` is **suspended but still being served** — 218 real cases. The IP makes the label verifiable without trusting either system's status flag.

`mismatches` — array of `{"type": "...", "detail": "..."}`. Types: `missing_radcheck` (39 real), `orphan_radcheck` (2,193 real), `disabled_not_pooled` (218 real), `lineid_conflict`, `replication_lag`.

### Traffic caveat

Direction labels are **suspect in the source data** — production shows upload far exceeding download (6,199 vs 953 MB/day mean), which is backwards for residential access, because `traffic_download` is populated from `acctinputoctets` (traffic *into* the NAS, i.e. customer upload). Scenarios reproduce the labels as they appear in production, inversion included. Agents should not treat the absolute direction as reliable evidence; the *trend* is what carries signal.

---

## 11. `ground_truth`

Consumed only by the evaluation harness.

```json
{
  "fault_type": "olt_health_false_critical",
  "root_cause": "OLT firmware version does not expose the ONU parameter OID subtree; the health check reads every sampled PON as failed while the OLT and all customers are operating normally.",
  "severity": "Information",
  "affected_scope": "none",
  "affected_lineids": [],
  "affected_customer_count": 0,
  "service_impact": false,

  "expected_reasoning": [
    "Health check reports critical with all 8 PONs failed",
    "OLT ping and SNMP sysUpTime both succeed — device is up",
    "Live probe shows oid_subtree_responds false, uniformly across all ports",
    "No ONU returns responds:true with online:0 — nothing is definitively offline",
    "CRM shows 291 of 298 ONUs online, consistent with the 4.85% network baseline",
    "Sessions are active and long-running; traffic is normal",
    "Uniform non-response with healthy service indicates an OID/firmware mismatch, not an outage"
  ],

  "required_evidence": [
    "olt_uptime_confirms_no_reboot",
    "oid_subtree_non_response_is_uniform",
    "customers_online_and_passing_traffic"
  ],

  "expected_remediation": "flag_monitoring_defect",
  "expected_escalation": {
    "priority": "Information",
    "category": "monitoring",
    "requires_human_review": true,
    "review_reason": "Health check tooling produces false criticals on this firmware version"
  },

  "distractors": [
    "The critical alarm invites an OLT-failure diagnosis",
    "Seven genuinely offline ONUs on the OLT are unrelated background noise at the normal rate"
  ]
}
```

| Field | Scoring use |
|---|---|
| `fault_type` | Binary match against `diagnosis.fault_type`. |
| `root_cause` | Scored 0 / 0.5 / 1 against `diagnosis.root_cause`. |
| `severity` | Binary match. Six-level scale, §12. |
| `affected_scope` | Binary. `none` \| `single_customer` \| `pon_port` \| `olt` \| `router` \| `multi_customer`. |
| `affected_lineids` | Set comparison — precision and recall on blast radius. |
| `service_impact` | Binary. **Separate from severity.** A critical-looking alarm with no service impact is precisely what the false-critical family tests. |
| `expected_reasoning` | Ordered steps. Evidence coverage = fraction appearing in the agent's evidence chain. |
| `required_evidence` | The subset that is non-negotiable. Reaching the right answer without these is a lucky guess and is scored separately. |
| `expected_remediation` | Binary match against `remediation.action`. |
| `expected_escalation` | Field-wise comparison. |
| `distractors` | Not scored. Documents what the scenario is designed to mislead on; used in failure analysis. |

`required_evidence` is the field that separates reasoning from pattern-matching. Track it — a configuration that lands the right `fault_type` while missing every required evidence item is guessing, and that distinction belongs in Chapter 5.

---

## 12. Severity model

Zabbix's six-level scale, adopted rather than invented. It is already the operators' vocabulary and it reconciles the three inconsistent scales in the Aztech codebase (`ok/warning/danger`, `healthy/critical/offline`, `success/warning/danger`).

| Level | Use |
|---|---|
| `Not classified` | Cannot be determined from available data |
| `Information` | No service impact; noteworthy state (monitoring defects, data drift) |
| `Warning` | Degradation, service still usable |
| `Average` | Single customer out of service |
| `High` | PON port or multi-customer outage |
| `Disaster` | OLT or router down; large-scale loss |

**Severity and `service_impact` are independent.** A false critical is `Information` with `service_impact: false`. A genuine PON failure is `High` with `service_impact: true`. Conflating them is the error the false-critical family exists to detect.

---

## 13. Identifier and naming conventions

| Thing | Pattern | Example |
|---|---|---|
| ONU MAC (`lineid`) | Uppercase, colon, 17 ch. OUI from ONU pool. | `4C:D7:C8:A1:3F:02` |
| CPE MAC (`mac`) | Same format. OUI from CPE pool. **Never reuse an ONU OUI.** | `C8:3A:35:7B:11:E4` |
| RADIUS username | Identical to `mac`. No stripping, no lowercasing. | `C8:3A:35:7B:11:E4` |
| Interface | `EPON0/{port}:{onu}`, port 1–8 | `EPON0/3:14` |
| PON port prefix | `EPON0/{port}` | `EPON0/3` |
| OLT host | `TK_` + site code + `-OLT_` or `_OLT-` + area + index | `TK_AZ-OLT_SK_ANC-08` |
| OLT management IP | `10.220.X.Y` | `10.220.114.5` |
| Router name | `TK_` + location + index | `TK_Skopje13-ANC01` |
| Customer data VLAN | `1XXY` — `XX` OLT id, `Y` PON port | `1013` |
| Scenario file | `{PREFIX}-{NNN}-{difficulty}.json` | `FCR-002-hard.json` |

Reserved VLANs: `1` parking, `46` factory CPE management, `100` OLT management, `1998` voice, `1999` provisioned CPE management.

Synthetic MACs must not collide with each other across the scenario set. The last three octets are randomised; OUIs are drawn from the real distributions in `calibration.md`.

---

## 14. Validation rules

`scenarios/validate_scenarios.py` enforces these. A scenario that fails any of them is not usable.

**Structural**
- All nine top-level sections present
- `scenario_id` unique across the set
- `fault_type` in the taxonomy enum
- Every timestamp ISO 8601 UTC and ≤ `captured_at`

**Format**
- MACs match `^([0-9A-F]{2}:){5}[0-9A-F]{2}$`
- `interface` matches `^EPON0/[1-8]:\d{1,3}$`
- `olt_technology` is `EPON`; `olt_model` is `V1600D`
- Stored powers are strings with two decimals; live powers are numbers

**Physical plausibility**
- `rx_power` in −40.0 … +3.7, or the `"0"`/`null` sentinel
- `tx_power` in −10.0 … +5.6, or sentinel. Healthy is **0 … +5**, centred near +2.3 — *not* the −6…−10 band documented in `NLQueryService`, which is wrong and would flag 92% of the estate
- `distance` 6 … 365 m, constant unless the scenario is `distance_change`
- `tx_bias_current` 9.5 … 13.0 mA healthy
- `supply_voltage` 3.40 … 3.46 V healthy
- ONU `temperature` 17 … 26 °C healthy
- OLT `cpu_load` ≤ 48, `memory_usage` ≤ 76, `temperature` ≤ 68

**Internal consistency**
- `peers.olt_population.onu_online_count + onu_offline_count == total_customers`
- `customers_per_port` sums to `total_customers`
- `pon_ports_in_use` ≤ 8
- Every `crm_view.customers[].interface` starts with `interface_port`
- The subject `lineid` appears in `crm_view.customers`
- `snmp_community_ok == snmp_response_ok` always
- `healthy_pons + len(failed_pons_list) == total_pons_tested`
- `overall_status == "critical"` **iff** `healthy_pons == 0` and `total_pons_tested > 0`
- `has_catv` / `has_voip` agree with `onu_model`
- `radius.username == subscriber.mac`
- If `framed_pool == "pool_Disable_Users"` then `assigned_ip` ∈ 10.200.200.0/24
- Telemetry array lengths == `window_hours / interval`
- `ground_truth.affected_customer_count == len(affected_lineids)` unless scope is `olt`/`router`

**Calibration**
- Every value traceable to a range or distribution in `calibration.md`
- Healthy telemetry series stay within the stated noise floor (RX ±0.3, TX ±0.08 per 24 h)
- Session counts consistent with the real distribution unless the scenario is a flapping case

---

## 15. Worked minimal example

Trimmed for readability — real scenarios carry full telemetry arrays and peer lists.

```json
{
  "metadata": {
    "scenario_id": "FD-001",
    "fault_type": "fiber_degradation",
    "difficulty": "easy",
    "captured_at": "2026-09-20T14:20:00Z",
    "description": "Single customer with steadily worsening RX power; port neighbours unaffected.",
    "tests": ["Is degradation distinguished from an outage?", "Is blast radius correctly bounded to one customer?"]
  },
  "trigger": {
    "type": "customer_complaint",
    "input": {"lineid": "4C:D7:C8:A1:3F:02", "complaint": "Internet is slow and cuts out"}
  },
  "subscriber": { "...": "see §5" },
  "network_state": {
    "onu_status": 1,
    "rx_power": "-26.40",
    "tx_power": "2.31",
    "reading_age_minutes": 47,
    "olt_health": {"overall_status": "healthy", "ping_ok": true, "snmp_community_ok": true, "snmp_response_ok": true, "total_pons_tested": 8, "healthy_pons": 8, "failed_pons_list": [], "error_description": null, "run_date": "2026-09-20"},
    "olt_metrics": {"cpu_load": 24, "memory_usage": 17, "temperature": 41, "uptime_days": 83, "firmware": "V2.03.78R"},
    "router_state": {"heartbeat_status": "ok", "hours_since_checkin": 0.4}
  },
  "peers": { "...": "port neighbours at -19 to -22, all online" },
  "telemetry": { "...": "rx_power drifting -19.2 → -26.4 over 168h; tx, distance, bias, voltage all flat" },
  "snmp_live": {
    "onu": {"responds": true, "online": 1, "rx_power": -27.10, "tx_power": 2.28, "auth_flag": "Auth", "exchange": "Finish", "rtt_tq": 52},
    "olt": {"ping_ok": true, "snmp_responds": true, "sys_uptime_seconds": 7171200, "oid_subtree_responds": true},
    "pon_probe": { "...": "neighbours normal, subject at -27.1" },
    "vlan_walk": {"responds": true, "customer_vlan_expected": 1013, "customer_vlan_actual": 1013}
  },
  "session_auth": {
    "sessions": {"count_24h": 11, "count_7d": 34, "avg_duration_minutes": 62},
    "radius": {"radcheck_exists": true, "framed_pool": null, "assigned_ip": "10.5.50.117", "crm_consistent": true, "mismatches": []},
    "traffic": {"download_mb_daily": [980, 1010, 870, 940, 410, 180, 62]}
  },
  "ground_truth": {
    "fault_type": "fiber_degradation",
    "root_cause": "Progressive attenuation in the fibre path between the splitter and the ONU.",
    "severity": "Warning",
    "affected_scope": "single_customer",
    "affected_lineids": ["4C:D7:C8:A1:3F:02"],
    "affected_customer_count": 1,
    "service_impact": true,
    "expected_reasoning": [
      "RX has fallen from -19.2 to -27.1 dBm over seven days against a ±0.3 dBm noise floor",
      "Live RX is below cached RX — degradation is ongoing, not settled",
      "TX power, distance, bias current and supply voltage are all flat — the ONU laser is healthy",
      "Port neighbours read -19 to -22 dBm — the PON port and splitter are fine",
      "Session count of 11 in 24h is far above the 2-3 baseline and tracks the signal loss",
      "Declining traffic is consistent with marginal connectivity"
    ],
    "required_evidence": ["rx_trend_over_time", "peers_normal_on_same_port", "tx_and_bias_stable"],
    "expected_remediation": "dispatch_technician",
    "expected_escalation": {"priority": "Warning", "category": "field_service", "requires_human_review": false, "review_reason": null},
    "distractors": ["Session flapping invites an auth-related diagnosis", "Traffic decline alone could suggest congestion"]
  }
}
```

---

## 16. Open items

- `graylog_events` section — deferred. The HLD's Graylog chapter is empty, and no field mapping exists. Noted as future work; MPCP deregistration is already available through `snmp_live.onu.exchange`.
- `acs` section (GenieACS/TR-069 fault state) — deferred for the same reason. A fifth data source with a documented REST API, but no production sample available.
- Both are recorded in Chapter 6 as extensions available to the production system.