# Fault Taxonomy

**Purpose:** the fault types the system must distinguish, what separates each from its nearest neighbours, and the manifest of 35 scenarios.
**Scope:** EPON only.
**Companions:** `scenario-schema.md` (structure), `calibration.md` (values and sources).

This document has three jobs. It is the enum for `metadata.fault_type` and `ground_truth.fault_type`. It is the manifest for scenario generation. And it is the outline for the RAG knowledge base — each family below becomes one diagnostic document.

---

## 1. Why discriminators are the point

Any single fault is easy to describe. What makes this domain a real test is that faults **share symptoms**. Degraded RX power appears in fibre degradation, splitter failure, PON port trouble and congestion. A customer with no service could have a dead ONU, a cut drop fibre, a failed splitter, a suspended account, or a RADIUS entry that never got written.

So for every family below, the important field is not the symptom list — it is the **discriminator**: the one observation that separates this fault from the thing it most resembles. Those discriminators are what the Diagnosis Agent must actively go and fetch, and they are the reason a pipeline that can probe should beat a single pass over a fixed payload.

Each family states which data layers are required to reach the answer. A fault diagnosable from `network_state` alone is one the monolithic baseline should also get right. A fault requiring `telemetry` plus `snmp_live.pon_probe` is one where architecture should matter.

---

## 2. Fault type enum

```
fiber_degradation
laser_degradation
distance_change
onu_offline
pon_port_failure
splitter_failure
olt_failure
olt_health_false_critical
router_unreachable
radius_missing_entry
radius_suspended_but_serving
radius_lineid_conflict
radius_replication_lag
session_flapping_signal
session_flapping_auth
duplicate_onu_slot
stuck_provisioning_vlan46
catv_drift
pon_congestion
no_fault
```

20 values across 16 families. `no_fault` is a legitimate answer and must be reachable — a pipeline that cannot conclude "nothing is wrong" is not usable.

---

## 3. The families

### 3.1 Fibre degradation — `FD`

Progressive attenuation in the fibre path between splitter and ONU. Bend, damaged connector, degraded splice, water ingress.

**Symptoms.** RX falling over days, typically into −25…−28 (degraded) or below −28 (critical). TX flat at its normal +2.3. Session count elevated as the link drops in and out of usable range. Traffic declining.

**Discriminator.** Peers on the same PON port read normal RX (−19…−22) while this customer does not. Confirms the fault lies downstream of the splitter, in this customer's own path.

**Confusable with.** Laser degradation (separated by TX bias — flat here, rising there). Splitter failure (separated by peers — normal here, also degraded there). Congestion (separated by RX — abnormal here, normal there).

**Layers required.** `telemetry` for the trend, `snmp_live.pon_probe` for the peers. `network_state` alone shows one low number and cannot tell you whether it is falling or whether anyone else is affected.

**Severity** Warning → Average as it crosses into critical RX · **Scope** single_customer · **Remediation** `dispatch_technician`

---

### 3.2 Laser degradation — `LD`

The ONU's transmit laser ageing. It compensates for falling efficiency by drawing more bias current to hold output power constant — until it can't.

**Symptoms.** TX bias current climbing from ~11 mA toward and past 13 mA. TX power flat at +2.3 (the compensation is working, for now). Supply voltage may drift. ONU temperature may rise. RX normal throughout.

**Discriminator.** **Rising bias at constant TX power.** Nothing else produces that combination. Fibre attenuation moves RX and leaves bias alone; this moves bias and leaves RX alone.

**Confusable with.** Fibre degradation (customer reports the same "it's getting worse"; the optical signature is the opposite). Early ONU hardware failure (this is the precursor — a laser at 14 mA is the ONU that goes dark next month).

**Layers required.** `telemetry` only. These signals exist in Zabbix for ~80,000 ONUs and no Aztech code reads them, so a system relying on `crm_user_net` alone is structurally blind to this fault.

**Severity** Warning · **Scope** single_customer · **Remediation** `schedule_onu_replacement`

---

### 3.3 Distance change — `DC`

The measured optical distance to an ONU steps to a new value. Physically this means the fibre path changed: a re-splice, a patch to a different port, or a record pointing at a different device.

**Symptoms.** `distance` steps from one constant to another. RX may shift with it. Everything else normal.

**Discriminator.** Distance is **constant per customer** in normal operation — it is the geometry of the fibre run. A step change is not noise and cannot be anything but a physical or record change. It is the cleanest single signal in the entire dataset.

**Confusable with.** Nothing, once you look at it. The difficulty is that nothing currently looks at it.

**Layers required.** `telemetry`.

**Severity** Warning · **Scope** single_customer · **Remediation** `verify_physical_path`

---

### 3.4 ONU offline — `OO`

A single ONU has stopped responding. Power cut at the premises, dead ONU, or a break in the drop fibre.

**Symptoms.** `onu_status: 0`. Live probe returns `online: 0` with `responds: true` — a definite negative. `auth_flag: Unauth`. `exchange: MPCP DEREG`. Sessions stop. Traffic goes to zero.

**Discriminator.** `responds: true` with `online: 0` means the OLT answered and said this ONU is down. That is different from `responds: false`, which means nothing answered at all — see §3.8. Against a port failure, the discriminator is count: one ONU down among healthy peers.

Distinguishing *why* it is offline requires history. RX degrading beforehand points to the fibre drop. A clean flat RX right up to the cut-off points to power loss or a dead ONU.

**Confusable with.** PON port failure (count of affected ONUs). Suspended account (check RADIUS before dispatching anyone). Health-check artifacts (§3.8).

**Layers required.** `snmp_live` to confirm, `telemetry` to attribute cause, `session_auth` to rule out suspension.

**Severity** Average · **Scope** single_customer · **Remediation** `onu_reset` then `dispatch_technician`

---

### 3.5 PON port failure — `PP`

An entire PON port stops serving. OLT port hardware, the feeder fibre, or the primary splitter.

**Symptoms.** All or nearly all ONUs on one `EPON0/N` go offline together. Other ports on the same OLT are fine. OLT ping and SNMP healthy. CPU, memory, temperature normal.

**Discriminator.** Scope, established by probing. Every ONU on one port down, every other port normal. The failure boundary follows the port exactly.

**Confusable with.** OLT failure (separated by whether other ports still work). Splitter failure (separated by whether *all* or only *some* of the port is affected). The false critical in §3.8 — and this is the important one: a real port failure and an OID mismatch can produce the same health-check line.

**Layers required.** `snmp_live.pon_probe` across multiple ports, `peers` for blast radius, `network_state.olt_health` for context.

**Severity** High · **Scope** pon_port · **Remediation** `escalate_infrastructure`

---

### 3.6 Splitter failure — `SP`

A downstream splitter serving a subset of one port's customers fails.

**Symptoms.** A **subset** of one port's ONUs offline simultaneously. The remaining ONUs on the same port are fine. The affected set is contiguous in the physical plant even if their ONU indexes are not.

**Discriminator.** Partial port impact. A port failure takes the whole port; a splitter failure takes a branch. The split between affected and unaffected is the evidence.

**Confusable with.** PON port failure (whole vs part). Coincidental multiple ONU failures — separated by simultaneity: a splitter drops its customers within seconds of each other.

**Layers required.** `snmp_live.pon_probe`, `session_auth` for disconnect timing correlation.

**Severity** High · **Scope** multi_customer · **Remediation** `escalate_infrastructure`

---

### 3.7 OLT failure — `OF`

The OLT itself is down or unreachable.

**Symptoms.** Two variants. **Offline** — ping fails, health check writes `overall_status: offline` with "OLT is not reachable (ping failed)". **SNMP dead** — ping succeeds but `sysUpTime` does not answer, giving `critical` with "SNMP community string not accessible, OLT does not respond to SNMP queries".

Every customer on the OLT is affected in the first case. In the second, service may be entirely unaffected — only monitoring is blind.

**Discriminator.** Ping result separates the two. And critically: **an OLT that fails SNMP but passes ping may be serving every customer perfectly.** Loss of monitoring is not loss of service, and conflating them is exactly the error the next family exists to catch.

**Confusable with.** Router unreachable (separated by whether the OLT answers at all). The false critical (separated by whether ping and SNMP succeed).

**Note.** `snmp_community_ok` and `snmp_response_ok` are both derived from the same single `sysUpTime` get, so they are always equal and their two error strings always appear together. The check cannot distinguish a wrong community string from a dead agent. Reproduce this faithfully.

**Collector convention.** The poller writes 0 for any value it cannot read. When SNMP fails, every stored `onu_status`, power and telemetry value under the OLT reads 0 from that hour on — so in the SNMP-dead variant stored data shows *every ONU offline* while customers are in service. Only ping, sessions and traffic separate it from the offline variant. A 0 in distance or supply voltage is physically impossible and marks the no-read default. (Engineer review, October 2026.)

**Layers required.** `network_state.olt_health`, `snmp_live.olt`, `peers.olt_population` to establish real impact.

**Severity** Disaster (offline) / Warning (SNMP-only, no service impact) · **Scope** olt · **Remediation** `escalate_infrastructure` / `flag_monitoring_defect`

---

### 3.8 OLT health check false critical — `FC`

The health check reports a critical fault that does not exist. Four distinct mechanisms, all traced to `CheckOLTHealth.php`.

**Mechanism (a) — OID subtree absent.** `checkONUOnlineStatus` reads a hardcoded OID and requires exactly `1`. On a firmware version where that subtree has moved, the call returns "No Such Instance", the function returns early, RX and TX are never attempted, and every sampled ONU on every port fails. Result: "All PONs failed (8/8)" on an OLT whose customers are all online and passing traffic. **Confirmed by Aztech as a firmware issue, not an outage.** Six of ten non-healthy OLTs on the 2026-09-21 run carry this signature.

**Mechanism (b) — all-or-nothing status.** `overall_status` is `critical` only when *every* sampled PON fails. Seven of eight failing produces `healthy` with `error_description: null`, while `healthy_pons: 1` and `total_pons_tested: 8` sit in the same record. A genuine single-port outage affecting up to 63 customers is labelled healthy, and the contradiction lives only in the detail fields.

**Mechanism (c) — one-ONU sampling.** Each port's verdict rests on a single device. A dead sample ONU condemns a healthy port of 30 customers; a healthy sample conceals 30 broken neighbours. False positives and false negatives from the same design choice.

**Mechanism (d) — staleness.** `olt_health_results` had not been written since 2025-11-11 when queried in September 2026. A ten-month-old record presented as current state.

**Discriminator — this is the most important one in the document.**

| | OID mismatch | Genuine mass outage |
|---|---|---|
| `olt.ping_ok` | true | true |
| `olt.snmp_responds` | true | true |
| ONU `responds` | **false, uniformly on every port** | **true** |
| ONU `online` | null — nothing answered | **0 — a definite negative** |
| RX/TX attempted | never reached | reached, may return values |
| CRM `onu_status` | ~95% online | matches the outage |
| Sessions | active, long-running | stopped at the same moment |
| Traffic | normal | zero |

**Uniform non-response with healthy service is a monitoring defect. Definite negatives with dead sessions are an outage.**

**Confusable with.** OLT failure and PON port failure — deliberately. The health record is nearly identical. Every disproving signal lives outside the alarm's own data source.

**Layers required.** All four. This is the scenario family that most sharply tests whether the pipeline verifies a claim before acting on it.

**Severity** Information · **Scope** none · **service_impact** false · **Remediation** `flag_monitoring_defect`

---

### 3.9 Router unreachable — `RU`

A MikroTik BNG stops checking in. Customers behind it lose service regardless of ONU state.

**Symptoms.** `hours_since_checkin` past 2 h (warning) or 4 h (danger). Sessions across many customers on that router end together. ONUs stay online — the optical layer is fine.

**Discriminator.** ONUs online while sessions are dead, affecting customers spread across **multiple OLTs** that share one router. Optical health is irrelevant to the fault; the boundary follows the router, not the fibre plant.

**Confusable with.** OLT failure (separated by ONU optical state and by whether the boundary follows OLT or router). Mass RADIUS failure (separated by whether the router is reachable at all).

**Management path.** Where OLT management runs through the same MikroTik, the OLTs behind it become unreachable too, and the case reads like an OLT failure on several OLTs at once. An OLT that still answers ping and SNMP shows its management does not route through the failed BNG.

**The never-checked-in case is not a fault.** Two routers in production have no check-in record ever. That is an unprovisioned monitoring row, not an outage — `heartbeat_status: never` with customers served normally. It is a false-alarm control.

**Layers required.** `network_state.router_state`, `session_auth`, `snmp_live` to show optical health is intact.

**Severity** Disaster (real) / Information (never-checked-in) · **Scope** router / none · **Remediation** `escalate_infrastructure` / `flag_monitoring_defect`

---

### 3.10 RADIUS — missing entry — `RA`

A customer is provisioned in CRM but has no `radcheck` row, so authentication fails. 39 real cases.

**Symptoms.** ONU online, optical signals perfect, but no active session and no IP. `radcheck_exists: false`. Traffic zero.

**Discriminator.** Healthy physical layer with absent authentication state. Everything optical says the customer is connected; everything session-related says they were never let on.

**Confusable with.** ONU offline (separated immediately by ONU status). Suspension (separated by whether the entry is *missing* versus *present and pooled*).

**Root cause.** Step 4 of the authentication flow — the DHCP script that creates the RADIUS user failed.

**Layers required.** `session_auth` plus `snmp_live` to establish the physical layer is fine.

**Severity** Average · **Scope** single_customer · **Remediation** `create_radius_entry` (automated)

---

### 3.11 RADIUS — suspended but serving — `RA`

CRM says disabled; RADIUS never moved them to the suspension pool. 218 real cases.

**Symptoms.** `subscriber.active: 0`, `framed_pool: null`, `assigned_ip` in `10.5.50.0/24`. Active sessions. Normal traffic.

**Discriminator.** **The IP address makes it verifiable without trusting either system's flag.** A suspended customer belongs in `10.200.200.0/24`. An address in `10.5.50.0/24` is proof of live service regardless of what any status field claims.

**Confusable with.** A normal active customer — unless you check `active` against the pool. A stale CRM record — separated by whether sessions are genuinely flowing.

**Severity** Warning — business impact rather than service impact · **Scope** single_customer · **service_impact** false · **Remediation** `apply_disable_pool` (automated)

---

### 3.12 RADIUS — lineid conflict / orphan — `RA`

`radcheck.lineid` disagrees with `crm_user_net.lineid` for the same CPE MAC, or a RADIUS entry exists with no active CRM customer. 2,193 orphans in production.

**Symptoms.** Line ID is an authentication parameter alongside the CPE MAC. When `radcheck.lineid` does not match the installed ONU, the next DHCP exchange (lease, renew, or the reconnect after a swap) is rejected and the customer loses service. Healthy optics, no session since that point, zero traffic. CRM and RADIUS give different answers to the same question.

**Discriminator.** Cross-system key comparison. `crm.mac` ↔ `radcheck.username` matches at 99.9%; `crm.lineid` ↔ `radcheck.lineid` at only 92.9%. The gap is the defect. An ONU swap where CRM was updated and RADIUS was not produces exactly this.

**Confusable with.** Missing entry (§3.10) — same outage, but here the row exists. Replication lag (§3.13) — same outage, but here both RADIUS servers agree and are both wrong. Duplicate slot (§3.16) — both are identity confusion, but that one is CRM-internal and this one is cross-system.

**Correction (engineer review, October 2026).** The first version had authentication still succeeding, with only accounting misattributed. A lineid mismatch disables the user at the next DHCP exchange; the scenario now models the outage.

**Severity** Average · **Scope** single_customer · **Remediation** `manual_review` — the installed device should be confirmed before the RADIUS record is rewritten

---

### 3.13 RADIUS — replication lag — `RA`

Primary and Secondary FreeRADIUS replicate master–slave in both directions. A change applied to one has not reached the other. It matters once the MikroTik fails over to the server that is out of sync.

**Symptoms.** A clean authentication failure, not flapping. When the session next drops and the MikroTik asks RADIUS, a failover to an unsynchronised secondary rejects the customer, who then stays down. Normal session history up to that point, no session since, zero traffic. No physical-layer fault whatsoever.

**Discriminator.** **The row is correct on one server and stale on the other, and the outage starts after failover.** No single query reveals it — you have to ask both sides and compare.

**Confusable with.** Missing entry (separated by the row existing). Lineid conflict (separated by the primary being correct and matching CRM). An ONU or CPE fault — which is what this gets misdiagnosed as in practice.

**Correction (engineer review, October 2026).** The first version had replication lag producing repeated disconnection and recovery. It does not: failover to an unsynced server rejects the customer outright.

**Layers required.** `session_auth` at depth, plus explicitly ruling out `telemetry` and `snmp_live`. This is the hardest fault in the set and the one a single-pass diagnosis is least likely to reach.

**Severity** Average · **Scope** single_customer · **Remediation** `escalate_radius_infrastructure`

---

### 3.14 Session flapping — signal-related — `SF`

Repeated disconnect/reconnect driven by marginal optical signal.

**Symptoms.** 8–26 sessions in 24 h against a 2–3 baseline. Sharply shortened durations against an 11.9 h mean. RX degraded or oscillating around a threshold boundary.

**Discriminator.** **Flapping plus degraded RX, with clean RADIUS.** The optical signal explains the sessions.

**Confusable with.** Auth-related flapping — the session pattern is identical and the optical layer is what separates them.

**Note.** 4–7 sessions per day is elevated but occurs in 2.9% of customers and is not on its own a fault. Use it as a distractor in scenarios whose real fault lies elsewhere. The empirical ceiling is 26 — do not generate 50.

**Severity** Warning · **Scope** single_customer · **Remediation** `dispatch_technician`

---

### 3.15 Session flapping — auth-related — `SF`

The same session pattern, produced by authentication problems instead.

**Symptoms.** Identical disconnect counts. **RX and TX entirely normal.** Reconnects succeed every time, so authentication works; something in the RADIUS reply ends each session. The modelled mechanism is a per-user `Session-Timeout` in `radreply`, which cuts every session at the same length — durations are uniform, unlike signal flapping.

**Discriminator.** **Flapping with a clean optical layer.** The absence of an optical explanation is itself the evidence — it forces the search into `session_auth`. Uniform durations equal to a reply attribute name the mechanism.

**Correction (engineer review, October 2026).** The first version used two `radcheck` rows for one username, resolved by whichever was reached first. `username` carries a unique index, so duplicates are near-impossible, and FreeRADIUS rejects outright when they exist rather than picking one. RADIUS defects that reject a customer cause outages, not flapping.

**Confusable with.** Signal-related flapping, obviously, and this pair is the cleanest test in the set of whether the pipeline checks a second layer before concluding. A diagnosis that stops at "sessions are flapping, must be signal" fails here, and that is a realistic failure because it is the common human assumption too.

**Severity** Average · **Scope** single_customer · **Remediation** depends on the underlying RADIUS fault

---

### 3.16 Duplicate ONU slot — `DS`

CRM places two or more live customers on the same physical interface. **644 such interfaces in production, 1,296 customers, worst case three on one slot.** Physically impossible — one slot holds one ONU.

**Symptoms.** Two `lineid` values sharing one `interface`, both `active: 1`. The live probe shows one ONU at that index. Optical readings cannot be attributed with confidence.

**Discriminator.** CRM view versus live probe. `peers.crm_view` lists two customers on `EPON0/3:14`; `snmp_live.pon_probe` shows one ONU. The `lineid` returned by the live probe identifies which record is real.

**Confusable with.** A stale record that was never deleted. The two are hard to separate without history — which is itself worth writing about, since a correct diagnosis here may be "insufficient evidence to determine which record is live" and that is a legitimate answer.

**Severity** Warning · **Scope** multi_customer · **service_impact** false · **Remediation** `manual_review`

---

### 3.17 Stuck provisioning — VLAN 46 — `SV`

A CPE ships on factory-default VLAN 46. TR-069/ACS is supposed to migrate it to the provisioned management VLAN 1999 and its data VLAN `1XXY`. When that never happens, the CPE is physically connected but logically stranded.

**Symptoms.** `vlan_walk.customer_vlan_actual: 46` against an expected `1XXY`. ONU online with good optical readings. No session or partial connectivity. Often a recently provisioned customer.

**Discriminator.** VLAN mismatch with a healthy physical layer. The customer is present on the fibre and absent from the network.

**Confusable with.** RADIUS missing entry — both give a healthy physical layer and no service. The VLAN walk separates them, and reaching for it is not the obvious first move.

**Layers required.** `snmp_live.vlan_walk`, plus `session_auth` to rule out the RADIUS explanation.

**Severity** Average · **Scope** single_customer · **Remediation** `trigger_acs_provisioning`

---

### 3.18 CATV drift — `CD`

Stored CATV service state disagrees with the device. 84 real cases — 52 subscribed but unsynced, 32 unsubscribed but unsynced.

**Symptoms.** `catv_service: 1` with `catv_synced: 0`, or the reverse. Data service entirely unaffected.

**Discriminator.** State mismatch on a single service dimension with nothing else wrong.

**Severity** Information · **Scope** single_customer · **service_impact** partial · **Remediation** `resync_catv` (automated)

---

### 3.19 PON congestion — `CG`

A PON port's shared capacity is saturated. Everyone on the port is slow; nobody is down.

**Symptoms.** High `pon_port_traffic.current_mbps` against its average. Multiple customers on the port reporting slowness. **All optical signals normal.** Sessions stable. Traffic high, not low.

**Discriminator.** **Multi-customer degradation with a clean optical layer and elevated traffic.** Every fault-driven degradation reduces traffic; congestion raises it. The direction of the traffic anomaly is the tell.

**Confusable with.** Splitter degradation affecting several customers — separated by optical readings and by traffic direction.

**Severity** Warning · **Scope** pon_port · **Remediation** `capacity_planning`

---

### 3.20 No fault — `NF`

Nothing is wrong. The pipeline must be able to say so and stop.

**Symptoms.** All signals within normal bands. Possibly one mildly unusual value — 4–7 sessions, RX at −24.5, a few offline ONUs on a large OLT consistent with the 4.85% baseline.

**Discriminator.** Every anomaly has a normal explanation. The point is to test the threshold discipline established in `calibration.md` §1: 2–3 sessions is baseline, TX at +2.3 is healthy, and 14 offline ONUs on a 298-customer OLT is an ordinary Tuesday.

**Severity** Not classified · **Scope** none · **service_impact** false · **Remediation** `no_action`

---

## 4. Discriminator matrix

The single observation that separates each confusable pair. This table is the core content of both the RAG knowledge base and the Diagnosis Agent's prompt.

| Pair | Discriminator |
|---|---|
| fibre degradation ↔ laser degradation | RX falls with flat bias · bias rises with flat RX |
| fibre degradation ↔ splitter failure | peers normal · peers also affected |
| fibre degradation ↔ congestion | RX abnormal, traffic falling · RX normal, traffic rising |
| fibre degradation ↔ distance change | RX slope over days · distance step, RX stable |
| ONU offline ↔ PON port failure | one ONU down among healthy peers · all ONUs on the port down |
| ONU offline ↔ suspension | RADIUS clean · `framed_pool` set or CRM inactive |
| PON port failure ↔ splitter failure | whole port · subset of port |
| PON port failure ↔ OLT failure | other ports healthy · all ports affected |
| **PON port failure ↔ false critical** | **`responds: true` with `online: 0` · `responds: false` uniformly** |
| OLT failure ↔ false critical | ping or SNMP fails · both succeed |
| OLT offline ↔ OLT SNMP-dead | ping fails · ping succeeds, SNMP does not |
| OLT failure ↔ router unreachable | ONUs unreachable · ONUs online, sessions dead |
| OLT offline ↔ OLT SNMP-dead, in stored data | both read all-zero · only ping, sessions and traffic separate them |
| router unreachable ↔ never-checked-in | heartbeat went stale · no record ever, customers served |
| flapping signal ↔ flapping auth | RX degraded, durations vary · RX normal, durations uniform, reply attribute |
| flapping ↔ RADIUS rejection | reconnects succeed · customer rejected and stays down |
| RADIUS missing ↔ lineid conflict ↔ replication lag | no row · row with wrong lineid · row stale on the secondary only |
| RADIUS missing ↔ stuck provisioning | no `radcheck` row · `radcheck` fine, VLAN is 46 |
| RADIUS missing ↔ suspension | entry absent · entry present and pooled |
| suspension ↔ suspended-but-serving | IP in 10.200.200.0/24 · IP in 10.5.50.0/24 |
| duplicate slot ↔ lineid conflict | CRM-internal collision · CRM ↔ RADIUS disagreement |
| any fault ↔ no fault | value outside the calibrated band · value inside it |

---

## 5. Data layer requirements

Which layers a correct diagnosis requires. This is the structural basis of the difficulty grading, and the hypothesis the evaluation tests: **agent advantage should grow with the number of layers required.**

| Fault | `network_state` | `telemetry` | `snmp_live` | `session_auth` |
|---|:---:|:---:|:---:|:---:|
| fiber_degradation | ✓ | **✓** | **✓** | ✓ |
| laser_degradation | | **✓** | | |
| distance_change | | **✓** | | |
| onu_offline | ✓ | ✓ | **✓** | ✓ |
| pon_port_failure | ✓ | | **✓** | ✓ |
| splitter_failure | | | **✓** | **✓** |
| olt_failure | ✓ | | **✓** | ✓ |
| **olt_health_false_critical** | **✓** | **✓** | **✓** | **✓** |
| router_unreachable | ✓ | | ✓ | **✓** |
| radius_missing_entry | ✓ | | ✓ | **✓** |
| radius_suspended_but_serving | ✓ | | | **✓** |
| radius_lineid_conflict | ✓ | | | **✓** |
| **radius_replication_lag** | ✓ | ✓ | ✓ | **✓** |
| session_flapping_signal | ✓ | **✓** | | **✓** |
| session_flapping_auth | ✓ | **✓** | | **✓** |
| duplicate_onu_slot | ✓ | | **✓** | |
| stuck_provisioning_vlan46 | ✓ | | **✓** | **✓** |
| catv_drift | ✓ | | ✓ | |
| pon_congestion | ✓ | ✓ | | **✓** |
| no_fault | ✓ | ✓ | ✓ | ✓ |

Bold marks a layer without which the correct answer is unreachable.

---

## 6. Scenario manifest — 35 scenarios

| ID | Fault type | Difficulty | What it tests |
|---|---|---|---|
| **FD-001** | fiber_degradation | easy | Degradation distinguished from outage; blast radius bounded to one customer |
| **FD-002** | fiber_degradation | medium | Trend required — a single RX reading is ambiguous |
| **FD-003** | fiber_degradation | hard | Compound: degradation plus an unrelated RADIUS mismatch on the same customer |
| **LD-001** | laser_degradation | medium | Bias/TX decoupling recognised; telemetry layer exercised |
| **LD-002** | laser_degradation | hard | Presents as "getting worse" alongside mild RX noise; must not be called fibre degradation |
| **DC-001** | distance_change | medium | Distance step detected at all |
| **DC-002** | distance_change | hard | Distance step plus RX shift; must attribute to path change, not attenuation |
| **OO-001** | onu_offline | easy | Definite negative recognised; suspension ruled out |
| **OO-002** | onu_offline | medium | Cause attribution — RX history separates fibre break from power loss |
| **OO-003** | onu_offline | hard | Offline ONU on an OLT that also has a false critical alarm |
| **PP-001** | pon_port_failure | easy | Port-scope blast radius established by probing |
| **PP-002** | pon_port_failure | medium | One ONU on the port was already offline before the event |
| **PP-003** | pon_port_failure | hard | Health record identical to FC-001; must reach the opposite conclusion |
| **SP-001** | splitter_failure | hard | Subset-of-port separated from whole-port failure |
| **OF-001** | olt_failure | easy | Ping failure, genuine outage, full OLT scope |
| **OF-002** | olt_failure | medium | SNMP dead but ping fine — stored data reads all-offline, service intact |
| **FC-001** | olt_health_false_critical | easy | Alarm contradicted by customer state; false critical identified |
| **FC-002** | olt_health_false_critical | hard | Mechanism (b): 7 of 8 PONs failed, labelled healthy, null error string |
| **FC-003** | olt_health_false_critical | hard | Mechanism (c): one dead sample ONU condemns a healthy port |
| **FC-004** | olt_health_false_critical | hard | Mechanism (d): ten-month-old health record presented as current |
| **RU-001** | router_unreachable | easy | Router-scope outage with ONUs optically healthy |
| **RU-002** | no_fault | medium | Never-checked-in router; monitoring gap, not an outage |
| **RA-001** | radius_missing_entry | easy | Healthy physical layer with absent auth state |
| **RA-002** | radius_suspended_but_serving | medium | IP range proves live service against CRM's inactive flag |
| **RA-003** | radius_lineid_conflict | medium | Cross-system key mismatch after an ONU swap; rejected since |
| **RA-004** | radius_replication_lag | hard | Rejected after failover to an unsynced secondary; primary looks correct |
| **SF-001** | session_flapping_signal | medium | Flapping attributed to its optical cause |
| **SF-002** | session_flapping_auth | hard | Flapping on clean optics from a per-user Session-Timeout; must search the auth layer |
| **DS-001** | duplicate_onu_slot | medium | CRM view contradicts live probe |
| **DS-002** | duplicate_onu_slot | hard | Three customers on one slot; may conclude insufficient evidence |
| **SV-001** | stuck_provisioning_vlan46 | medium | VLAN mismatch found with a healthy physical layer |
| **SV-002** | stuck_provisioning_vlan46 | hard | Presents identically to RA-001; VLAN walk is the separator |
| **CD-001** | catv_drift | easy | Service-state mismatch with no data impact |
| **CG-001** | pon_congestion | medium | Multi-customer slowness with normal optics and rising traffic |
| **NF-001** | no_fault | easy | Scheduled scan over normal values; pipeline stops cleanly |

### Difficulty distribution

| | Count | Share |
|---|---|---|
| easy | 9 | 26% |
| medium | 13 | 37% |
| hard | 13 | 37% |

### Coverage per family

| Family | Scenarios | Family | Scenarios |
|---|---|---|---|
| fiber_degradation | 3 | radius (4 types) | 4 |
| laser_degradation | 2 | session_flapping | 2 |
| distance_change | 2 | duplicate_onu_slot | 2 |
| onu_offline | 3 | stuck_provisioning | 2 |
| pon_port_failure | 3 | catv_drift | 1 |
| splitter_failure | 1 | pon_congestion | 1 |
| olt_failure | 2 | no_fault | 2 |
| false_critical | 4 | router_unreachable | 1 |

Two or more scenarios per family for 13 of 16 families, which is enough for the per-fault-type breakdown in Chapter 5 to carry meaning rather than noise.

---

## 7. Deliberate design choices

**Four scenarios on the false critical.** More than any other family, because it is the sharpest available test of the research question. The alarm claims a critical outage; the truth is that nothing is wrong. Every disproving signal lives outside the alarm's own data source. A system that verifies before concluding gets it right; a system that reads and answers does not. PP-003 is its mirror — a genuine outage wearing an identical health record — so a pipeline cannot pass the family by learning to distrust health alarms categorically.

**Paired look-alikes.** SF-001/SF-002, SV-002/RA-001, FC-001/PP-003, DS-001/RA-003. Each pair shares a symptom profile and diverges on one observation. These pairs are where architecture should show, and where failure analysis will be most informative.

**`no_fault` is reachable.** Two scenarios, plus OF-002 and FC-* where the answer is "no service impact". A pipeline that cannot conclude nothing is wrong will manufacture faults, and its false positive rate is as much a result as its accuracy.

**Real counts behind the defects.** 644 duplicate slots, 218 suspended-but-serving, 2,193 orphans, 39 missing entries, 84 CATV drifts, 6 false criticals in one run. These scenarios model documented production conditions rather than invented ones, and that distinction belongs in the methodology chapter.

---

## 8. RAG knowledge base mapping

Each family becomes one diagnostic document, structured per `scenario-schema.md`. Sixteen family documents plus three cross-cutting ones:

| Document | Content |
|---|---|
| 17. Discriminator reference | §4 of this document, expanded with worked examples |
| 18. Calibrated thresholds | The corrected bands from `calibration.md` §1 — TX 0…+5, session baseline 2–3, `'0'` sentinels |
| 19. Health check behaviour and defects | The four mechanisms in §3.8, with the `responds` vs `online` distinction stated explicitly |

Document 18 matters more than it looks. It is where the corrected thresholds live, and the RAG-on versus RAG-off comparison partly measures whether having them changes diagnostic accuracy — which is a concrete, quantifiable finding about retrieval-augmented reasoning in an operational domain.