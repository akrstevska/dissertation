#!/usr/bin/env python3
"""Scenario builders: FD, LD, DC, OO, PP, SP, OF families."""
from datetime import datetime, timedelta, timezone
from estate import *
from estate import _rng
import math

S = []


def scn(**kw):
    S.append(kw)
    return kw


def assemble(sid, ft, diff, cap, desc, tests, trig, sub, ns, peers, tel_onu, tel_olt,
             live, sess_auth, gt, note=None, gaps=None):
    md = {"scenario_id": sid, "fault_type": ft, "difficulty": diff,
          "captured_at": iso(cap), "description": desc, "tests": tests}
    if note:
        md["note"] = note
    return {
        "metadata": md, "trigger": trig, "subscriber": sub, "network_state": ns,
        "peers": peers,
        "telemetry": {"onu_series": tel_onu, "olt_series": tel_olt,
                      "availability": {"onu_series_complete": not gaps, "gaps": gaps or []}},
        "snmp_live": live, "session_auth": sess_auth, "ground_truth": gt,
    }


# ================================================================ FD-002
def fd002():
    cap = datetime(2026, 9, 18, 11, 5, tzinfo=timezone.utc)
    K, port, idx = "KV03", 6, 12
    lid, m = onu_mac(), cpe_mac()
    start, tel = healthy_series(cap, rx_base=-24.6, dist=203, bias_base=10.9)
    # oscillating around the degraded boundary rather than a clean slope
    tel["rx_power"] = [r2(-24.6 - 2.2 * math.sin(2 * math.pi * i / 34.0) + _rng.gauss(0, 0.2))
                       for i in range(H)]
    prs, idxs, sidx = make_peers(K, port, lid, -24.62, n_on_port=19, n_listed=7, subject_idx=idx)
    return assemble(
        "FD-002", "fiber_degradation", "medium", cap,
        "RX oscillates around the degraded boundary rather than falling cleanly; a single reading is ambiguous and only the series resolves it.",
        ["Is a trend read from the series rather than from one reading?",
         "Is an oscillating marginal link recognised as degradation?",
         "Are peers used to bound the fault to one customer?"],
        {"type": "customer_complaint",
         "input": {"lineid": lid, "complaint": "Sometimes fine, sometimes unusable, no pattern I can see"}},
        subscriber(K, port, idx, lid, m, model_i=4, profile="profile_40M"),
        {"onu_status": 1, "rx_power": "-22.41", "tx_power": "2.38", "reading_age_minutes": 141,
         "olt_health": healthy_olt_health(K, "2026-09-18"),
         "olt_metrics": olt_metrics(K, 23, 17, 40, 55),
         "router_state": router_state(K, cap, 0.4)},
        prs, tel, olt_series(cap, 23, 17, 40),
        {"onu": {"responds": True, "online": 1, "rx_power": -26.88, "tx_power": 2.36,
                 "auth_flag": "Auth", "exchange": "Finish", "rtt_tq": 67},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 4752000,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {sidx: -26.88}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": sessions(cap, 7, 31, 186, 3.2, 3, "10.5.50.142"),
         "radius": radius(m, lid, "10.5.50.142"),
         "traffic": traffic([870, 640, 910, 520, 780, 460, 690], cur=176, avg=181, peak=520)},
        {"fault_type": "fiber_degradation",
         "root_cause": "Intermittent attenuation in the customer's fibre path, most consistent with a marginal connector or a bend that moves with temperature; the link crosses in and out of usable signal.",
         "severity": "Warning", "affected_scope": "single_customer",
         "affected_lineids": [lid], "affected_customer_count": 1, "service_impact": True,
         "expected_reasoning": [
             "Cached RX of -22.41 dBm is inside the normal band and on its own looks fine",
             "The cached reading is 141 minutes old, so it may not represent current state",
             "Live RX of -26.88 dBm is 4.5 dB worse than cached, a gap far outside the +/-0.3 dBm noise floor",
             "Telemetry shows RX oscillating between roughly -22 and -27 dBm on a sub-daily cycle",
             "TX power, bias current, supply voltage and distance are all flat, so the ONU is healthy",
             "Peers on EPON0/6 read normal, so the PON port and splitter are not involved",
             "Seven sessions in 24h is elevated above the 2-3 baseline and tracks the signal excursions",
             "An oscillating marginal link points to a physical fault that moves, not a fixed loss"],
         "required_evidence": ["rx_series_oscillation", "cached_live_discrepancy", "peers_normal_on_same_port"],
         "expected_remediation": "dispatch_technician",
         "expected_escalation": {"priority": "Warning", "category": "field_service",
                                 "requires_human_review": False, "review_reason": None},
         "distractors": ["The cached RX reading is inside the normal band and invites a no_fault conclusion",
                         "Seven sessions is elevated but sits inside the 2.9% of customers who do 4-7 normally",
                         "Erratic traffic could be read as ordinary usage variation"]})


# ================================================================ FD-003
def fd003():
    cap = datetime(2026, 9, 19, 16, 40, tzinfo=timezone.utc)
    K, port, idx = "VE05", 2, 27
    lid, m = onu_mac(), cpe_mac()
    start, tel = healthy_series(cap, rx_base=-19.6, dist=310, bias_base=11.6)
    tel["rx_power"] = ramp(-19.6, -28.9, 0.15, knee=60)
    tel["speed_kbps"] = [r2(max(0.02, _rng.gauss(5.1, 2.2) * (1.0 if i < 120 else max(0.05, 1 - (i - 120) / 48))))
                         for i in range(H)]
    prs, idxs, sidx = make_peers(K, port, lid, -28.31, n_on_port=31, n_listed=8, subject_idx=idx)
    return assemble(
        "FD-003", "fiber_degradation", "hard", cap,
        "Critical fibre degradation on a customer who also carries an unrelated RADIUS orphan entry; two faults present at once.",
        ["Is the primary fault separated from a coincident unrelated one?",
         "Is the RADIUS mismatch correctly judged not to explain the symptoms?",
         "Is severity driven by the fault with service impact?"],
        {"type": "customer_complaint",
         "input": {"lineid": lid, "complaint": "Completely dead most of the day now"}},
        subscriber(K, port, idx, lid, m, model_i=1, profile="profile_80M"),
        {"onu_status": 1, "rx_power": "-28.31", "tx_power": "2.44", "reading_age_minutes": 19,
         "olt_health": healthy_olt_health(K, "2026-09-19"),
         "olt_metrics": olt_metrics(K, 27, 19, 45, 72),
         "router_state": router_state(K, cap, 0.2)},
        prs, tel, olt_series(cap, 27, 19, 45),
        {"onu": {"responds": True, "online": 1, "rx_power": -28.94, "tx_power": 2.43,
                 "auth_flag": "Auth", "exchange": "Finish", "rtt_tq": 88},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 6220800,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {sidx: -28.94}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": sessions(cap, 14, 52, 44, 0.9, 4, "10.5.50.61"),
         "radius": radius(m, lid, "10.5.50.61", consistent=False, mismatches=[
             {"type": "orphan_radcheck",
              "detail": "A stale radcheck row exists for a previous CPE MAC on this customer's line, left behind after a router swap in June. It does not match the current username and is not consulted during authentication."}]),
         "traffic": traffic([1180, 1090, 940, 610, 240, 88, 31], cur=204, avg=214, peak=680)},
        {"fault_type": "fiber_degradation",
         "root_cause": "Severe attenuation in the customer's fibre path, now at -28.9 dBm and below the critical threshold. The orphan RADIUS entry is a separate, dormant record defect that does not affect authentication.",
         "severity": "Average", "affected_scope": "single_customer",
         "affected_lineids": [lid], "affected_customer_count": 1, "service_impact": True,
         "expected_reasoning": [
             "RX has fallen from -19.6 to -28.9 dBm over the last four days and is now below the -28 critical threshold",
             "Live RX is below cached RX, so degradation has not stabilised",
             "TX power, bias current, supply voltage and distance are flat, ruling out laser degradation and path change",
             "Peers on EPON0/2 are normal, bounding the fault to this customer's own path",
             "Traffic has collapsed from 1180 MB to 31 MB per day in step with the signal loss",
             "A RADIUS orphan entry exists but references a superseded CPE MAC and is not used for authentication",
             "The orphan cannot explain progressive optical loss, so it is a coincident record defect and not the cause",
             "Severity is driven by the optical fault, which has service impact; the record defect has none"],
         "required_evidence": ["rx_trend_over_time", "peers_normal_on_same_port",
                               "radius_orphan_ruled_out_as_cause"],
         "expected_remediation": "dispatch_technician",
         "expected_escalation": {"priority": "Average", "category": "field_service",
                                 "requires_human_review": True,
                                 "review_reason": "A separate orphan RADIUS record should be cleaned up independently of the field repair"},
         "distractors": ["The RADIUS mismatch invites an auth-related diagnosis",
                         "Fourteen sessions in 24h could be read as auth flapping",
                         "Two genuine faults are present and only one has service impact"]})


# ================================================================ LD-001
def ld001():
    cap = datetime(2026, 9, 17, 8, 15, tzinfo=timezone.utc)
    K, port, idx = "JAD04", 4, 8
    lid, m = onu_mac(), cpe_mac()
    start, tel = healthy_series(cap, rx_base=-21.3, dist=77)
    tel["tx_bias_current"] = ramp(11.1, 14.2, 0.15, knee=36)
    tel["supply_voltage"] = ramp(3.44, 3.38, 0.010, knee=36)
    tel["temperature"] = [r2(v + 0.02 * i) for i, v in enumerate(diurnal(23.0, 1.7, 0.3))]
    prs, idxs, sidx = make_peers(K, port, lid, -21.28, n_on_port=26, n_listed=7, subject_idx=idx)
    return assemble(
        "LD-001", "laser_degradation", "medium", cap,
        "ONU transmit laser ageing: bias current climbing past the healthy ceiling while TX power is held constant and RX is untouched.",
        ["Is the bias/TX decoupling recognised?",
         "Is the telemetry layer used at all, given the stored columns look normal?",
         "Is this separated from fibre attenuation?"],
        {"type": "scheduled_scan", "input": {"scope": "olt", "target": ESTATE[K]["host"]}},
        subscriber(K, port, idx, lid, m, model_i=0, profile="profile_20M"),
        {"onu_status": 1, "rx_power": "-21.28", "tx_power": "2.31", "reading_age_minutes": 34,
         "olt_health": healthy_olt_health(K, "2026-09-17"),
         "olt_metrics": olt_metrics(K, 25, 18, 43, 66),
         "router_state": router_state(K, cap, 0.3)},
        prs, tel, olt_series(cap, 25, 18, 43),
        {"onu": {"responds": True, "online": 1, "rx_power": -21.31, "tx_power": 2.30,
                 "auth_flag": "Auth", "exchange": "Finish", "rtt_tq": 51},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 5702400,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {sidx: -21.31}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": sessions(cap, 3, 18, 620, 9.4, 3, "10.5.50.30"),
         "radius": radius(m, lid, "10.5.50.30"),
         "traffic": traffic([1020, 980, 1110, 940, 1060, 1005, 990], cur=198, avg=202, peak=615)},
        {"fault_type": "laser_degradation",
         "root_cause": "The ONU's transmit laser is ageing. Bias current has risen from 11.1 to 14.2 mA over five days to hold output power constant, and supply voltage has drifted down. The optical path itself is unchanged.",
         "severity": "Warning", "affected_scope": "single_customer",
         "affected_lineids": [lid], "affected_customer_count": 1, "service_impact": False,
         "expected_reasoning": [
             "Stored RX and TX values are both inside their healthy bands, so nothing is visible in the current-state layer",
             "Telemetry shows TX bias current rising from 11.1 to 14.2 mA, past the 13.0 mA healthy ceiling",
             "TX power has stayed flat at 2.3 dBm throughout, so the laser is still compensating successfully",
             "Rising bias at constant output power is the signature of laser ageing, not of path loss",
             "RX is flat at -21.3 dBm, so the fibre path is unaffected and this is not fibre degradation",
             "Supply voltage has drifted from 3.44 to 3.38 V and ONU temperature is trending up, both consistent with a stressed transmitter",
             "Sessions and traffic are normal, so there is no service impact yet",
             "This is a precursor: the ONU should be replaced before compensation fails"],
         "required_evidence": ["bias_current_rising", "tx_power_constant", "rx_unaffected"],
         "expected_remediation": "schedule_onu_replacement",
         "expected_escalation": {"priority": "Warning", "category": "field_service",
                                 "requires_human_review": False, "review_reason": None},
         "distractors": ["Every stored value is healthy, inviting a no_fault conclusion",
                         "The customer has not complained and service is unaffected",
                         "Rising ONU temperature could be read as an environmental issue"]})


# ================================================================ LD-002
def ld002():
    cap = datetime(2026, 9, 22, 13, 50, tzinfo=timezone.utc)
    K, port, idx = "PP03", 7, 33
    lid, m = onu_mac(), cpe_mac()
    start, tel = healthy_series(cap, rx_base=-23.9, dist=241)
    tel["rx_power"] = flat(-23.9, 0.28)
    tel["tx_bias_current"] = ramp(11.4, 15.1, 0.18, knee=20)
    tel["supply_voltage"] = ramp(3.45, 3.36, 0.010, knee=20)
    tel["tx_power"] = ramp(2.42, 2.05, 0.04, knee=130)
    prs, idxs, sidx = make_peers(K, port, lid, -23.88, n_on_port=29, n_listed=8, subject_idx=idx)
    return assemble(
        "LD-002", "laser_degradation", "hard", cap,
        "Laser failing with RX sitting in the low-normal band and noisier than usual; presents as 'getting worse' and closely resembles fibre degradation.",
        ["Is laser degradation separated from fibre degradation when both could fit?",
         "Is TX starting to fall recognised as compensation failing rather than path loss?",
         "Is mildly noisy RX correctly judged not to be the cause?"],
        {"type": "customer_complaint",
         "input": {"lineid": lid, "complaint": "Connection has been getting steadily worse over the last week"}},
        subscriber(K, port, idx, lid, m, model_i=3, profile="profile_30M_1M"),
        {"onu_status": 1, "rx_power": "-23.88", "tx_power": "2.09", "reading_age_minutes": 26,
         "olt_health": healthy_olt_health(K, "2026-09-22"),
         "olt_metrics": olt_metrics(K, 22, 17, 41, 38),
         "router_state": router_state(K, cap, 0.5)},
        prs, tel, olt_series(cap, 22, 17, 41),
        {"onu": {"responds": True, "online": 1, "rx_power": -23.95, "tx_power": 2.04,
                 "auth_flag": "Auth", "exchange": "Finish", "rtt_tq": 74},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 3283200,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {sidx: -23.95}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": sessions(cap, 6, 29, 240, 4.1, 3, "10.5.50.171"),
         "radius": radius(m, lid, "10.5.50.171"),
         "traffic": traffic([910, 880, 845, 790, 720, 655, 590], cur=189, avg=196, peak=560)},
        {"fault_type": "laser_degradation",
         "root_cause": "The ONU transmit laser is at end of life. Bias current has risen from 11.4 to 15.1 mA and, over the last two days, output power has begun to fall despite it, meaning compensation is now failing.",
         "severity": "Average", "affected_scope": "single_customer",
         "affected_lineids": [lid], "affected_customer_count": 1, "service_impact": True,
         "expected_reasoning": [
             "The customer reports progressive worsening, which fits both fibre degradation and laser degradation",
             "RX sits at -23.9 dBm in the low-normal band and is noisier than the usual floor, but it is flat with no downward trend",
             "TX bias current has climbed from 11.4 to 15.1 mA, well past the 13.0 mA ceiling",
             "TX power held at 2.42 dBm while bias rose, then began falling to 2.05 dBm in the last two days",
             "Falling output despite maximum bias means the laser can no longer compensate",
             "Supply voltage has drifted from 3.45 to 3.36 V, consistent with a failing transmitter",
             "Distance is constant, so there has been no change to the fibre path",
             "Peers on EPON0/7 are normal, so shared infrastructure is not involved",
             "Flat RX with collapsing TX is a transmitter fault, not path attenuation"],
         "required_evidence": ["bias_current_rising", "tx_power_now_falling", "rx_flat_not_trending"],
         "expected_remediation": "schedule_onu_replacement",
         "expected_escalation": {"priority": "Average", "category": "field_service",
                                 "requires_human_review": False, "review_reason": None},
         "distractors": ["RX in the low-normal band with extra noise invites a fibre degradation diagnosis",
                         "Steadily declining traffic fits either fault equally well",
                         "The complaint wording matches the fibre degradation pattern almost exactly"]})


# ================================================================ DC-001
def dc001():
    cap = datetime(2026, 9, 16, 10, 30, tzinfo=timezone.utc)
    K, port, idx = "SR01", 3, 17
    lid, m = onu_mac(), cpe_mac()
    start, tel = healthy_series(cap, rx_base=-19.4, dist=112)
    tel["distance"] = [112] * 104 + [268] * (H - 104)
    tel["rx_power"] = [r2(-19.4 + _rng.gauss(0, 0.15)) if i < 104
                       else r2(-22.1 + _rng.gauss(0, 0.15)) for i in range(H)]
    prs, idxs, sidx = make_peers(K, port, lid, -22.08, n_on_port=21, n_listed=7, subject_idx=idx)
    return assemble(
        "DC-001", "distance_change", "medium", cap,
        "Optical distance steps from 112 m to 268 m with a matching RX step; the fibre path changed rather than degraded.",
        ["Is the distance signal read at all?",
         "Is a step change separated from a gradual trend?",
         "Is the RX shift attributed to the path change rather than to attenuation?"],
        {"type": "threshold_breach", "input": {"signal": "rx_power_change", "lineid": lid, "value": -22.08}},
        subscriber(K, port, idx, lid, m, model_i=2, profile="profile_20M"),
        {"onu_status": 1, "rx_power": "-22.08", "tx_power": "2.36", "reading_age_minutes": 58,
         "olt_health": healthy_olt_health(K, "2026-09-16"),
         "olt_metrics": olt_metrics(K, 21, 16, 39, 91),
         "router_state": router_state(K, cap, 0.6)},
        prs, tel, olt_series(cap, 21, 16, 39),
        {"onu": {"responds": True, "online": 1, "rx_power": -22.05, "tx_power": 2.37,
                 "auth_flag": "Auth", "exchange": "Finish", "rtt_tq": 96},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 7862400,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {sidx: -22.05}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": sessions(cap, 3, 17, 658, 12.1, 3, "10.5.50.77"),
         "radius": radius(m, lid, "10.5.50.77"),
         "traffic": traffic([1040, 995, 1080, 1010, 960, 1030, 1000], cur=161, avg=158, peak=470)},
        {"fault_type": "distance_change",
         "root_cause": "The measured optical distance stepped from 112 m to 268 m two and a half days ago, with a matching 2.7 dB RX drop. The fibre path was physically re-routed, most likely a re-splice or a patch onto a different feeder.",
         "severity": "Warning", "affected_scope": "single_customer",
         "affected_lineids": [lid], "affected_customer_count": 1, "service_impact": False,
         "expected_reasoning": [
             "RX dropped from -19.4 to -22.1 dBm, which alone would suggest attenuation",
             "The drop is a single step, not a slope, and RX has been stable at the new level since",
             "Distance stepped from 112 m to 268 m at the same moment",
             "Distance is constant per customer in normal operation, so a step means the physical path changed",
             "The 2.7 dB loss is consistent with 156 m of additional fibre plus a splice",
             "TX power, bias current and supply voltage are all unchanged, so the ONU is not involved",
             "RTT timing quantum of 96 corroborates the longer path",
             "Service is unaffected: sessions and traffic are normal at the new signal level",
             "This is a recorded path change, not a developing fault"],
         "required_evidence": ["distance_step_detected", "rx_step_not_slope", "timing_corroborates_distance"],
         "expected_remediation": "verify_physical_path",
         "expected_escalation": {"priority": "Warning", "category": "field_service",
                                 "requires_human_review": True,
                                 "review_reason": "Confirm the re-route was intentional and update plant records"},
         "distractors": ["The RX drop looks like fibre degradation if distance is not consulted",
                         "The trigger is phrased as an RX threshold breach, pointing at the wrong signal",
                         "Service is unaffected, inviting a no_fault conclusion"]})


# ================================================================ DC-002
def dc002():
    cap = datetime(2026, 9, 20, 7, 20, tzinfo=timezone.utc)
    K, port, idx = "OHSC02", 5, 22
    lid, m = onu_mac(), cpe_mac()
    start, tel = healthy_series(cap, rx_base=-20.8, dist=95)
    tel["distance"] = [95] * 72 + [95] * 0 + [41] * (H - 72)
    tel["rx_power"] = ([r2(-20.8 + _rng.gauss(0, 0.15)) for _ in range(72)] +
                       ramp(-18.2, -26.5, 0.15, n=H - 72))
    prs, idxs, sidx = make_peers(K, port, lid, -26.12, n_on_port=24, n_listed=8, subject_idx=idx)
    return assemble(
        "DC-002", "distance_change", "hard", cap,
        "Distance steps down and RX first improves then begins falling; a re-splice that was done badly, so a path change and a developing fault are stacked.",
        ["Is the distance step found beneath a later RX trend?",
         "Is the sequence of events reconstructed in the right order?",
         "Is the primary cause attributed to the path change rather than to independent attenuation?"],
        {"type": "customer_complaint",
         "input": {"lineid": lid, "complaint": "It was fixed last week and now it is bad again"}},
        subscriber(K, port, idx, lid, m, model_i=6, profile="profile_300M"),
        {"onu_status": 1, "rx_power": "-26.12", "tx_power": "2.41", "reading_age_minutes": 31,
         "olt_health": healthy_olt_health(K, "2026-09-20"),
         "olt_metrics": olt_metrics(K, 24, 18, 42, 29),
         "router_state": router_state(K, cap, 0.3)},
        prs, tel, olt_series(cap, 24, 18, 42),
        {"onu": {"responds": True, "online": 1, "rx_power": -26.58, "tx_power": 2.40,
                 "auth_flag": "Auth", "exchange": "Finish", "rtt_tq": 52},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 2505600,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {sidx: -26.58}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": sessions(cap, 8, 33, 128, 2.4, 4, "10.5.50.209"),
         "radius": radius(m, lid, "10.5.50.209"),
         "traffic": traffic([1160, 1240, 1180, 990, 760, 520, 340], cur=222, avg=218, peak=690)},
        {"fault_type": "distance_change",
         "root_cause": "A re-splice four days ago shortened the path from 95 m to 41 m and initially improved RX from -20.8 to -18.2 dBm. Since then RX has fallen steadily to -26.5 dBm, so the new splice itself is failing.",
         "severity": "Average", "affected_scope": "single_customer",
         "affected_lineids": [lid], "affected_customer_count": 1, "service_impact": True,
         "expected_reasoning": [
             "Current RX of -26.1 dBm is in the degraded band and live RX is worse still at -26.6",
             "The recent RX series shows a clear downward slope, which alone reads as fibre degradation",
             "Looking further back, distance stepped from 95 m to 41 m four days ago",
             "At that same moment RX jumped upward from -20.8 to -18.2 dBm, consistent with a shorter path",
             "So the sequence is: path shortened and improved first, then began degrading from the new baseline",
             "The customer's statement that it was fixed last week corroborates a work visit at that point",
             "TX power, bias current and supply voltage are flat, so the ONU is not implicated",
             "Peers on EPON0/5 are normal, so the fault is in this customer's own path",
             "A splice made four days ago that is now losing 8 dB is a defective splice, not coincidental degradation"],
         "required_evidence": ["distance_step_detected", "rx_improved_then_degraded",
                               "degradation_postdates_path_change"],
         "expected_remediation": "dispatch_technician",
         "expected_escalation": {"priority": "Average", "category": "field_service",
                                 "requires_human_review": True,
                                 "review_reason": "Rework of a splice completed four days ago; the original job should be reviewed"},
         "distractors": ["The recent RX slope is a textbook fibre degradation signature",
                         "The distance step is buried three days back in the series",
                         "Eight sessions in 24h invites a flapping diagnosis"]})


# ================================================================ OO-001
def oo001():
    cap = datetime(2026, 9, 22, 20, 10, tzinfo=timezone.utc)
    K, port, idx = "KV03", 2, 9
    lid, m = onu_mac(), cpe_mac()
    start, tel = healthy_series(cap, rx_base=-20.2, dist=64)
    for k in ("rx_power", "tx_power", "tx_bias_current", "supply_voltage", "temperature", "speed_kbps"):
        tel[k] = cliff(tel[k], 163, None)
    tel["distance"] = cliff(tel["distance"], 163, None)
    prs, idxs, sidx = make_peers(K, port, lid, -20.19, subject_status=0, n_on_port=23,
                                 n_listed=7, subject_idx=idx)
    return assemble(
        "OO-001", "onu_offline", "easy", cap,
        "A single ONU has gone offline with a clean signal history right up to the cut-off; neighbours on the port are unaffected.",
        ["Is a definite offline answer distinguished from no answer at all?",
         "Is suspension ruled out before a technician is dispatched?",
         "Is blast radius correctly bounded to one customer?"],
        {"type": "customer_complaint", "input": {"lineid": lid, "complaint": "No internet at all since this afternoon"}},
        subscriber(K, port, idx, lid, m, model_i=0, profile="profile_20M"),
        {"onu_status": 0, "rx_power": "0", "tx_power": "0", "reading_age_minutes": 11,
         "olt_health": healthy_olt_health(K, "2026-09-22"),
         "olt_metrics": olt_metrics(K, 23, 17, 41, 59),
         "router_state": router_state(K, cap, 0.2)},
        prs, tel, olt_series(cap, 23, 17, 41),
        {"onu": {"responds": True, "online": 0, "rx_power": None, "tx_power": None,
                 "auth_flag": "Unauth", "exchange": "MPCP DEREG", "rtt_tq": None},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 5097600,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {}, online_by_idx={sidx: 0}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": sessions(cap, 1, 14, 712, 5.1, 2, "10.5.50.93"),
         "radius": radius(m, lid, "10.5.50.93"),
         "traffic": traffic([1010, 970, 1040, 990, 1020, 960, 208], cur=170, avg=176, peak=505)},
        {"fault_type": "onu_offline",
         "root_cause": "The ONU has deregistered and stopped responding. Optical readings were entirely normal up to the moment it dropped, with no preceding degradation, which points to loss of power at the premises or a failed ONU rather than a fibre fault.",
         "severity": "Average", "affected_scope": "single_customer",
         "affected_lineids": [lid], "affected_customer_count": 1, "service_impact": True,
         "expected_reasoning": [
             "Stored onu_status is 0 and both power columns hold the '0' no-reading sentinel",
             "Live probe returns responds true with online 0, which is a definite negative rather than an absence of response",
             "Auth flag is Unauth and the exchange state is MPCP DEREG, confirming deregistration on the OLT",
             "Telemetry was flat and healthy at -20.2 dBm right up to the cut-off five hours ago, with no preceding decline",
             "Absence of prior degradation argues against a fibre fault and for power loss or ONU failure",
             "Peers on EPON0/2 are all online with normal readings, so the port, feeder and splitter are fine",
             "RADIUS shows an active entry with no disable pool, so this is not a suspension",
             "Traffic stopped today after six normal days"],
         "required_evidence": ["definite_offline_not_no_response", "clean_signal_history_before_cutoff",
                               "suspension_ruled_out"],
         "expected_remediation": "onu_reset",
         "expected_escalation": {"priority": "Average", "category": "field_service",
                                 "requires_human_review": False, "review_reason": None},
         "distractors": ["The '0' power values could be misread as a strong signal if the sentinel is not recognised",
                         "A single offline ONU on a large OLT is within the 4.85% background rate"]})


# ================================================================ OO-002
def oo002():
    cap = datetime(2026, 9, 21, 6, 45, tzinfo=timezone.utc)
    K, port, idx = "GRAD01", 7, 31
    lid, m = onu_mac(), cpe_mac()
    start, tel = healthy_series(cap, rx_base=-22.0, dist=188)
    tel["rx_power"] = ramp(-22.0, -31.4, 0.15, knee=40)[:150] + [None] * (H - 150)
    for k in ("tx_power", "tx_bias_current", "supply_voltage", "temperature", "speed_kbps"):
        tel[k] = cliff(tel[k], 150, None)
    tel["distance"] = cliff(tel["distance"], 150, None)
    prs, idxs, sidx = make_peers(K, port, lid, "0", subject_status=0, n_on_port=27,
                                 n_listed=8, subject_idx=idx)
    prs["crm_view"]["customers"] = [
        c if c["lineid"] != lid else {**c, "rx_power": "0"} for c in prs["crm_view"]["customers"]]
    return assemble(
        "OO-002", "onu_offline", "medium", cap,
        "ONU offline after four days of progressive signal loss; the history distinguishes a fibre break from a power cut.",
        ["Is the cause of the outage attributed using history rather than current state?",
         "Is a fibre break separated from power loss or ONU failure?",
         "Is the correct remediation chosen given the cause?"],
        {"type": "customer_complaint", "input": {"lineid": lid, "complaint": "Been getting worse for days, now nothing"}},
        subscriber(K, port, idx, lid, m, model_i=1, profile="profile_40M"),
        {"onu_status": 0, "rx_power": "0", "tx_power": "0", "reading_age_minutes": 8,
         "olt_health": healthy_olt_health(K, "2026-09-21"),
         "olt_metrics": olt_metrics(K, 26, 18, 43, 47),
         "router_state": router_state(K, cap, 0.2)},
        prs, tel, olt_series(cap, 26, 18, 43),
        {"onu": {"responds": True, "online": 0, "rx_power": None, "tx_power": None,
                 "auth_flag": "Unauth", "exchange": "MPCP DEREG", "rtt_tq": None},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 4060800,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {}, online_by_idx={sidx: 0}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": sessions(cap, 2, 24, 96, 18.2, 3, "10.5.50.55"),
         "radius": radius(m, lid, "10.5.50.55"),
         "traffic": traffic([980, 870, 640, 410, 180, 44, 0], cur=194, avg=203, peak=590)},
        {"fault_type": "onu_offline",
         "root_cause": "The ONU dropped after four days of progressive optical loss, falling from -22.0 to -31.4 dBm before it stopped registering. The preceding decline indicates a failing fibre path that has now broken, not a power cut.",
         "severity": "Average", "affected_scope": "single_customer",
         "affected_lineids": [lid], "affected_customer_count": 1, "service_impact": True,
         "expected_reasoning": [
             "ONU is offline with responds true and online 0, a definite negative",
             "Telemetry shows RX declining from -22.0 to -31.4 dBm over four days before the series ends",
             "The decline crossed the -28 dBm critical threshold roughly a day before the ONU dropped",
             "A progressive decline ending in loss of registration indicates a failing fibre path, not an abrupt power loss",
             "By contrast, a power cut or ONU failure would show a flat healthy signal right up to the cut-off",
             "TX power and bias current were stable throughout, so the laser was not the cause",
             "Peers on EPON0/7 are online with normal readings, bounding the fault to this customer's path",
             "RADIUS is clean, so this is not a suspension",
             "Daily traffic decayed to zero in step with the signal loss"],
         "required_evidence": ["progressive_decline_before_dropout", "definite_offline_not_no_response",
                               "peers_normal_on_same_port"],
         "expected_remediation": "dispatch_technician",
         "expected_escalation": {"priority": "Average", "category": "field_service",
                                 "requires_human_review": False, "review_reason": None},
         "distractors": ["An ONU reset is the reflex remediation for an offline ONU and will not help here",
                         "The telemetry series ends partway through, which could be read as a collection gap"]},
        gaps=[{"signal": "rx_power", "from_index": 150, "to_index": 167}])


# ================================================================ OO-003
def oo003():
    cap = datetime(2026, 9, 21, 19, 45, tzinfo=timezone.utc)
    K, port, idx = "KO14", 4, 12
    lid, m = onu_mac(), cpe_mac()
    start, tel = healthy_series(cap, rx_base=-21.6, dist=133)
    for k in ("rx_power", "tx_power", "tx_bias_current", "supply_voltage", "temperature", "speed_kbps"):
        tel[k] = cliff(tel[k], 158, None)
    tel["distance"] = cliff(tel["distance"], 158, None)
    prs, idxs, sidx = make_peers(K, port, lid, "0", subject_status=0, n_on_port=25,
                                 n_listed=7, subject_idx=idx)
    prs["crm_view"]["customers"] = [
        c if c["lineid"] != lid else {**c, "rx_power": "0"} for c in prs["crm_view"]["customers"]]
    e = ESTATE[K]
    return assemble(
        "OO-003", "onu_offline", "hard", cap,
        "A genuinely offline ONU on an OLT that is simultaneously reporting a false critical health alarm; two findings must be separated.",
        ["Is a real single-customer fault separated from a concurrent false alarm?",
         "Is the OLT alarm correctly dismissed without also dismissing the real fault?",
         "Are two different scopes held apart in one diagnosis?"],
        {"type": "customer_complaint", "input": {"lineid": lid, "complaint": "Nothing since about 4pm"}},
        subscriber(K, port, idx, lid, m, model_i=0, profile="profile_20M"),
        {"onu_status": 0, "rx_power": "0", "tx_power": "0", "reading_age_minutes": 14,
         "olt_health": {**healthy_olt_health(K, "2026-09-21"), "healthy_pons": 0,
                        "failed_pons_list": [f"EPON0/{i}:1" for i in range(1, e["ports"] + 1)],
                        "error_description": f"All PONs failed ({e['ports']}/{e['ports']})",
                        "overall_status": "critical"},
         "olt_metrics": olt_metrics(K, 23, 18, 43, 44),
         "router_state": router_state(K, cap, 0.3)},
        prs, tel, olt_series(cap, 23, 18, 43),
        {"onu": {"responds": True, "online": 0, "rx_power": None, "tx_power": None,
                 "auth_flag": "Unauth", "exchange": "MPCP DEREG", "rtt_tq": None},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 3801600,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {}, online_by_idx={sidx: 0}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": sessions(cap, 1, 16, 688, 3.6, 2, "10.5.50.121"),
         "radius": radius(m, lid, "10.5.50.121"),
         "traffic": traffic([1000, 1060, 980, 1020, 950, 1010, 260], cur=158, avg=163, peak=480)},
        {"fault_type": "onu_offline",
         "root_cause": "This customer's ONU has genuinely deregistered, with a clean signal history up to the cut-off. The OLT's concurrent critical health alarm is a separate false positive: the live probe answers normally for every other ONU on the port, so the health check result does not reflect the device state.",
         "severity": "Average", "affected_scope": "single_customer",
         "affected_lineids": [lid], "affected_customer_count": 1, "service_impact": True,
         "expected_reasoning": [
             "The customer's ONU returns responds true with online 0, a definite offline answer",
             "Signal history was flat and healthy until the cut-off four hours ago, so power loss or ONU failure is indicated",
             "The OLT health record separately reports critical with all PONs failed",
             "However the live probe answers normally for every other ONU on EPON0/4, returning real RX and TX values",
             "OLT ping and SNMP both succeed, uptime is 44 days, and CPU, memory and temperature are at baseline",
             "If the OLT or its PON ports had genuinely failed, no ONU would be responding and many more customers would be offline",
             "CRM shows the OLT's offline count consistent with the normal background rate, not a mass outage",
             "The health alarm is therefore a false critical and must not be conflated with this customer's real fault",
             "Two findings coexist: one genuine single-customer outage and one monitoring defect"],
         "required_evidence": ["definite_offline_not_no_response", "peers_respond_normally",
                               "olt_alarm_contradicted_by_probe"],
         "expected_remediation": "onu_reset",
         "expected_escalation": {"priority": "Average", "category": "field_service",
                                 "requires_human_review": True,
                                 "review_reason": "A concurrent false critical health alarm on this OLT should be raised separately with monitoring"},
         "distractors": ["The critical OLT alarm invites attributing the customer outage to an OLT failure",
                         "Dismissing the alarm too readily risks also dismissing the genuine customer fault",
                         "Only one customer is affected despite an alarm claiming the whole OLT"]})


# ================================================================ PP-001
def pp001():
    cap = datetime(2026, 9, 19, 9, 5, tzinfo=timezone.utc)
    K, port = "VSB02", 2, 
    port = 2
    lid, m = onu_mac(), cpe_mac()
    idx = 4
    start, tel = healthy_series(cap, rx_base=-20.9, dist=157)
    for k in ("rx_power", "tx_power", "tx_bias_current", "supply_voltage", "temperature", "speed_kbps"):
        tel[k] = cliff(tel[k], 160, None)
    tel["distance"] = cliff(tel["distance"], 160, None)
    peer_status = {}
    prs, idxs, sidx = make_peers(K, port, lid, "0", subject_status=0, n_on_port=24,
                                 n_listed=8, subject_idx=idx)
    prs["crm_view"]["customers"] = [{**c, "onu_status": 0, "rx_power": "0"}
                                    for c in prs["crm_view"]["customers"]]
    affected = [c["lineid"] for c in prs["crm_view"]["customers"]]
    prs["olt_population"]["onu_offline_count"] = 24 + 3
    prs["olt_population"]["onu_online_count"] = ESTATE[K]["cust"] - 27
    return assemble(
        "PP-001", "pon_port_failure", "easy", cap,
        "Every ONU on one PON port has gone offline simultaneously while the other ports on the OLT are unaffected.",
        ["Is blast radius established by probing rather than assumed?",
         "Is port scope separated from OLT scope?",
         "Is simultaneity recognised as evidence of a shared cause?"],
        {"type": "scheduled_scan", "input": {"scope": "olt", "target": ESTATE[K]["host"]}},
        subscriber(K, port, idx, lid, m, model_i=0, profile="profile_20M"),
        {"onu_status": 0, "rx_power": "0", "tx_power": "0", "reading_age_minutes": 7,
         "olt_health": {**healthy_olt_health(K, "2026-09-19"), "healthy_pons": 2,
                        "failed_pons_list": ["EPON0/2:1"], "total_pons_tested": 3},
         "olt_metrics": olt_metrics(K, 22, 17, 40, 77),
         "router_state": router_state(K, cap, 0.3)},
        prs, tel, olt_series(cap, 22, 17, 40),
        {"onu": {"responds": True, "online": 0, "rx_power": None, "tx_power": None,
                 "auth_flag": "Unauth", "exchange": "MPCP DEREG", "rtt_tq": None},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 6652800,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {}, online_by_idx={i: 0 for i in idxs}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": sessions(cap, 1, 13, 702, 6.4, 2, "10.5.50.44"),
         "radius": radius(m, lid, "10.5.50.44"),
         "traffic": traffic([960, 1010, 940, 1000, 980, 1030, 312], cur=12, avg=148, peak=430)},
        {"fault_type": "pon_port_failure",
         "root_cause": "All 24 customers on EPON0/2 lost service within the same minute. The OLT is healthy and its other two ports are serving normally, so the fault is confined to this PON port: the port optics, the feeder fibre or the primary splitter.",
         "severity": "High", "affected_scope": "pon_port",
         "affected_lineids": affected, "affected_customer_count": len(affected),
         "service_impact": True,
         "expected_reasoning": [
             "The subject ONU is offline with responds true and online 0",
             "Probing the rest of EPON0/2 shows every ONU returning the same definite offline answer",
             "All of them stopped within the same minute, which rules out coincidence",
             "OLT ping and SNMP succeed, uptime is 77 days, and CPU, memory and temperature are at baseline",
             "The other two PON ports on this OLT are serving customers normally",
             "The failure boundary follows the port exactly, so the fault is the port and not the OLT",
             "Signal history on the subject was flat and healthy until the cut-off, so this is not progressive degradation",
             "PON port traffic has collapsed from its usual level to near zero",
             "A whole port failing at once points to port optics, the feeder or the primary splitter"],
         "required_evidence": ["all_onus_on_port_offline", "other_ports_healthy", "simultaneous_dropout"],
         "expected_remediation": "escalate_infrastructure",
         "expected_escalation": {"priority": "High", "category": "infrastructure",
                                 "requires_human_review": False, "review_reason": None},
         "distractors": ["The health check still reports the OLT healthy because two of three ports pass",
                         "A single-customer complaint would frame this as an individual fault"]})


# ================================================================ PP-002
def pp002():
    cap = datetime(2026, 9, 20, 22, 30, tzinfo=timezone.utc)
    K, port, idx = "JAD04", 6, 15
    lid, m = onu_mac(), cpe_mac()
    start, tel = healthy_series(cap, rx_base=-19.9, dist=88)
    for k in ("rx_power", "tx_power", "tx_bias_current", "supply_voltage", "temperature", "speed_kbps"):
        tel[k] = cliff(tel[k], 164, None)
    tel["distance"] = cliff(tel["distance"], 164, None)
    prs, idxs, sidx = make_peers(K, port, lid, "0", subject_status=0, n_on_port=29,
                                 n_listed=8, subject_idx=idx)
    stale = idxs[0]
    prs["crm_view"]["customers"] = [{**c, "onu_status": 0, "rx_power": "0"}
                                    for c in prs["crm_view"]["customers"]]
    affected = [c["lineid"] for c in prs["crm_view"]["customers"]
                if int(c["interface"].split(":")[1]) != stale]
    prs["olt_population"]["onu_offline_count"] = 29 + 9
    prs["olt_population"]["onu_online_count"] = ESTATE[K]["cust"] - 38
    return assemble(
        "PP-002", "pon_port_failure", "medium", cap,
        "A PON port has failed, but one ONU on it had already been offline for three days for an unrelated reason; the affected set must be stated correctly.",
        ["Is the pre-existing outage excluded from the blast radius?",
         "Is dropout timing used to separate the two events?",
         "Is the affected customer count reported accurately?"],
        {"type": "threshold_breach", "input": {"signal": "mass_onu_offline",
                                               "olt_host": ESTATE[K]["host"], "value": 29}},
        subscriber(K, port, idx, lid, m, model_i=3, profile="profile_30M_1M"),
        {"onu_status": 0, "rx_power": "0", "tx_power": "0", "reading_age_minutes": 5,
         "olt_health": {**healthy_olt_health(K, "2026-09-20"), "healthy_pons": 7,
                        "failed_pons_list": ["EPON0/6:1"]},
         "olt_metrics": olt_metrics(K, 25, 18, 42, 70),
         "router_state": router_state(K, cap, 0.2)},
        prs, tel, olt_series(cap, 25, 18, 42),
        {"onu": {"responds": True, "online": 0, "rx_power": None, "tx_power": None,
                 "auth_flag": "Unauth", "exchange": "MPCP DEREG", "rtt_tq": None},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 6048000,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {}, online_by_idx={i: 0 for i in idxs}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": sessions(cap, 1, 15, 694, 1.3, 2, "10.5.50.183"),
         "radius": radius(m, lid, "10.5.50.183"),
         "traffic": traffic([1080, 1020, 1110, 990, 1050, 1000, 640], cur=8, avg=231, peak=700)},
        {"fault_type": "pon_port_failure",
         "root_cause": "EPON0/6 has failed, taking 28 of its 29 customers offline simultaneously 80 minutes ago. The twenty-ninth ONU had already been offline for three days from an unrelated individual fault and is not part of this event.",
         "severity": "High", "affected_scope": "pon_port",
         "affected_lineids": affected, "affected_customer_count": len(affected),
         "service_impact": True,
         "expected_reasoning": [
             "Every ONU on EPON0/6 now returns responds true with online 0",
             "28 of the 29 stopped within the same minute, 80 minutes ago",
             "One ONU on the port last held a session three days ago, so it was already down before this event",
             "That ONU's separate history excludes it from this incident's affected set",
             "OLT ping and SNMP succeed and the other seven ports are serving normally",
             "The failure boundary follows EPON0/6 exactly",
             "PON port traffic has collapsed from 231 Mbps average to 8 Mbps",
             "The affected count is 28, not 29"],
         "required_evidence": ["all_onus_on_port_offline", "pre_existing_outage_excluded",
                               "other_ports_healthy"],
         "expected_remediation": "escalate_infrastructure",
         "expected_escalation": {"priority": "High", "category": "infrastructure",
                                 "requires_human_review": False, "review_reason": None},
         "distractors": ["The trigger states 29 offline, inviting that number to be reported as the blast radius",
                         "All 29 look identical in current state and only history separates them"]})


# ================================================================ PP-003
def pp003():
    cap = datetime(2026, 9, 21, 19, 31, 34, tzinfo=timezone.utc)
    K, port, idx = "PP03", 3, 7
    lid, m = onu_mac(), cpe_mac()
    e = ESTATE[K]
    start, tel = healthy_series(cap, rx_base=-20.4, dist=176)
    for k in ("rx_power", "tx_power", "tx_bias_current", "supply_voltage", "temperature", "speed_kbps"):
        tel[k] = cliff(tel[k], 155, None)
    tel["distance"] = cliff(tel["distance"], 155, None)
    prs, idxs, sidx = make_peers(K, port, lid, "0", subject_status=0, n_on_port=30,
                                 n_listed=8, subject_idx=idx)
    prs["crm_view"]["customers"] = [{**c, "onu_status": 0, "rx_power": "0"}
                                    for c in prs["crm_view"]["customers"]]
    prs["olt_population"]["onu_offline_count"] = e["cust"] - 12
    prs["olt_population"]["onu_online_count"] = 12
    return assemble(
        "PP-003", "pon_port_failure", "hard", cap,
        "A genuine OLT-wide outage carrying a health record identical in wording to the known false critical; the opposite conclusion is required.",
        ["Is a real outage distinguished from the false-critical signature?",
         "Is responds:true with online:0 recognised as a definite negative?",
         "Is the pipeline resistant to learning that health alarms are always wrong?"],
        {"type": "health_check_alarm",
         "input": {"olt_host": e["host"], "overall_status": "critical",
                   "error_description": f"All PONs failed ({e['ports']}/{e['ports']})"}},
        subscriber(K, port, idx, lid, m, model_i=0, profile="profile_20M"),
        {"onu_status": 0, "rx_power": "0", "tx_power": "0", "reading_age_minutes": 9,
         "olt_health": {**healthy_olt_health(K, "2026-09-21"), "healthy_pons": 0,
                        "failed_pons_list": [f"EPON0/{i}:1" for i in range(1, e["ports"] + 1)],
                        "error_description": f"All PONs failed ({e['ports']}/{e['ports']})",
                        "overall_status": "critical"},
         "olt_metrics": olt_metrics(K, 31, 22, 47, 0),
         "router_state": router_state(K, cap, 0.2)},
        prs, tel, olt_series(cap, 31, 22, 47),
        {"onu": {"responds": True, "online": 0, "rx_power": None, "tx_power": None,
                 "auth_flag": "Unauth", "exchange": "MPCP DEREG", "rtt_tq": None},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 2820,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {}, online_by_idx={i: 0 for i in idxs}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": sessions(cap, 1, 14, 698, 0.8, 2, "10.5.50.66"),
         "radius": radius(m, lid, "10.5.50.66"),
         "traffic": traffic([1020, 1090, 980, 1040, 1010, 1060, 410], cur=4, avg=228, peak=690)},
        {"fault_type": "pon_port_failure",
         "root_cause": "The OLT rebooted 47 minutes ago and its PON ports have not brought subscribers back. All ports are genuinely down: every ONU answers the probe with a definite offline state, sessions ended together at the reboot, and traffic has stopped.",
         "severity": "Disaster", "affected_scope": "olt",
         "affected_lineids": [], "affected_customer_count": e["cust"] - 12,
         "service_impact": True,
         "expected_reasoning": [
             "The health record wording is identical to the known false-critical signature, so it cannot be trusted either way",
             "The live probe is decisive: every ONU returns responds true with online 0",
             "That is a definite negative from the OLT, not an absence of response, so the OID subtree is present and answering",
             "oid_subtree_responds is true, which rules out the firmware mismatch mechanism",
             "OLT sys_uptime is 2820 seconds, meaning it rebooted 47 minutes ago",
             "CRM shows only 12 of 236 ONUs online, far outside the 4.85% background rate",
             "Sessions across the OLT ended together at the reboot and traffic has fallen to near zero",
             "This is a genuine OLT-wide outage that happens to produce the same health record as the false positive",
             "The discriminator is the probe response type, not the alarm text"],
         "required_evidence": ["definite_offline_not_no_response", "oid_subtree_responds_true",
                               "olt_recently_rebooted", "customers_not_passing_traffic"],
         "expected_remediation": "escalate_infrastructure",
         "expected_escalation": {"priority": "Disaster", "category": "infrastructure",
                                 "requires_human_review": False, "review_reason": None},
         "distractors": ["The alarm text is word for word the same as the known false critical",
                         "Ping and SNMP both succeed, which is also true in the false-critical case",
                         "A pipeline that has learned to distrust this alarm will dismiss a real outage"]})


# ================================================================ SP-001
def sp001():
    cap = datetime(2026, 9, 18, 17, 25, tzinfo=timezone.utc)
    K, port, idx = "ANC08", 6, 19
    lid, m = onu_mac(), cpe_mac()
    start, tel = healthy_series(cap, rx_base=-22.7, dist=294)
    for k in ("rx_power", "tx_power", "tx_bias_current", "supply_voltage", "temperature", "speed_kbps"):
        tel[k] = cliff(tel[k], 161, None)
    tel["distance"] = cliff(tel["distance"], 161, None)
    prs, idxs, sidx = make_peers(K, port, lid, "0", subject_status=0, n_on_port=34,
                                 n_listed=9, subject_idx=idx)
    down_idxs = [i for i in idxs if i >= idx - 4][:5]
    if sidx not in down_idxs:
        down_idxs.append(sidx)
    custs = []
    for c in prs["crm_view"]["customers"]:
        i = int(c["interface"].split(":")[1])
        custs.append({**c, "onu_status": 0, "rx_power": "0"} if i in down_idxs else c)
    prs["crm_view"]["customers"] = custs
    affected = [c["lineid"] for c in custs if c["onu_status"] == 0]
    prs["olt_population"]["onu_offline_count"] = 11 + 14
    prs["olt_population"]["onu_online_count"] = ESTATE[K]["cust"] - 25
    return assemble(
        "SP-001", "splitter_failure", "hard", cap,
        "Eleven of thirty-four customers on one PON port drop together while the rest of the port keeps working; a branch has failed, not the port.",
        ["Is partial port impact separated from whole-port failure?",
         "Is simultaneity used to rule out coincidental individual faults?",
         "Is the affected set reported as a subset rather than the whole port?"],
        {"type": "threshold_breach", "input": {"signal": "mass_onu_offline",
                                               "olt_host": ESTATE[K]["host"], "value": 11}},
        subscriber(K, port, idx, lid, m, model_i=4, profile="profile_40M"),
        {"onu_status": 0, "rx_power": "0", "tx_power": "0", "reading_age_minutes": 6,
         "olt_health": healthy_olt_health(K, "2026-09-18"),
         "olt_metrics": olt_metrics(K, 24, 17, 41, 85),
         "router_state": router_state(K, cap, 0.4)},
        prs, tel, olt_series(cap, 24, 17, 41),
        {"onu": {"responds": True, "online": 0, "rx_power": None, "tx_power": None,
                 "auth_flag": "Unauth", "exchange": "MPCP DEREG", "rtt_tq": None},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 7344000,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {}, online_by_idx={i: 0 for i in down_idxs}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": sessions(cap, 1, 15, 706, 2.1, 2, "10.5.50.158"),
         "radius": radius(m, lid, "10.5.50.158"),
         "traffic": traffic([1030, 980, 1060, 1000, 1020, 970, 520], cur=134, avg=196, peak=600)},
        {"fault_type": "splitter_failure",
         "root_cause": "Eleven of the thirty-four customers on EPON0/6 lost service within the same minute while the remaining twenty-three continue normally. A shared downstream splitter branch has failed; the PON port itself is still working.",
         "severity": "High", "affected_scope": "multi_customer",
         "affected_lineids": affected, "affected_customer_count": len(affected),
         "service_impact": True,
         "expected_reasoning": [
             "Probing EPON0/6 shows eleven ONUs offline and twenty-three still online with normal RX and TX",
             "Because part of the port is still serving, the port optics and feeder fibre are working",
             "The eleven failures occurred within the same minute, which rules out unrelated individual faults",
             "A simultaneous partial loss on a working port indicates a shared element downstream of the port",
             "That element is a splitter branch serving those eleven customers",
             "OLT ping, SNMP, CPU, memory and temperature are all normal, so the OLT is not involved",
             "The health check still reports the OLT healthy, which is correct here but only because the port has surviving ONUs",
             "PON port traffic has fallen but not collapsed, consistent with losing a third of the port",
             "The affected set is the eleven, not the whole port"],
         "required_evidence": ["subset_of_port_affected", "surviving_onus_on_same_port",
                               "simultaneous_dropout"],
         "expected_remediation": "escalate_infrastructure",
         "expected_escalation": {"priority": "High", "category": "infrastructure",
                                 "requires_human_review": False, "review_reason": None},
         "distractors": ["Eleven simultaneous outages could be read as a PON port failure if the surviving ONUs are not probed",
                         "The OLT health check reports healthy, inviting a no_fault conclusion",
                         "The affected ONU indexes are not contiguous, obscuring the shared branch"]})


# ================================================================ OF-001
def of001():
    cap = datetime(2026, 9, 22, 4, 15, tzinfo=timezone.utc)
    K, port, idx = "MADZ01", 3, 11
    lid, m = onu_mac(), cpe_mac()
    e = ESTATE[K]
    start, tel = healthy_series(cap, rx_base=-21.1, dist=119)
    for k in ("rx_power", "tx_power", "tx_bias_current", "supply_voltage", "temperature", "speed_kbps"):
        tel[k] = cliff(tel[k], 166, None)
    tel["distance"] = cliff(tel["distance"], 166, None)
    prs, idxs, sidx = make_peers(K, port, lid, "0", subject_status=0, n_on_port=23,
                                 n_listed=7, subject_idx=idx)
    prs["crm_view"]["customers"] = [{**c, "onu_status": 0, "rx_power": "0"}
                                    for c in prs["crm_view"]["customers"]]
    prs["olt_population"]["onu_offline_count"] = e["cust"]
    prs["olt_population"]["onu_online_count"] = 0
    return assemble(
        "OF-001", "olt_failure", "easy", cap,
        "An OLT has stopped responding to ping entirely; every customer behind it is out of service.",
        ["Is an unreachable OLT distinguished from a port or customer fault?",
         "Is the blast radius correctly extended to the whole OLT?",
         "Is severity set to match the scale of impact?"],
        {"type": "health_check_alarm",
         "input": {"olt_host": e["host"], "overall_status": "offline",
                   "error_description": "OLT is not reachable (ping failed)"}},
        subscriber(K, port, idx, lid, m, model_i=0, profile="profile_20M"),
        {"onu_status": 0, "rx_power": "0", "tx_power": "0", "reading_age_minutes": 118,
         "olt_health": {"olt_ip": e["ip"], "olt_host": e["host"], "olt_technology": "EPON",
                        "olt_ext_id": e["ext"], "ping_ok": False, "snmp_community_ok": False,
                        "snmp_response_ok": False, "total_pons_tested": 0, "healthy_pons": 0,
                        "failed_pons_list": [],
                        "error_description": "OLT is not reachable (ping failed)",
                        "overall_status": "offline", "run_date": "2026-09-22"},
         "olt_metrics": {"cpu_load": 0, "memory_usage": 0, "temperature": 0,
                         "uptime_days": 0, "firmware": e["fw"], "firmware_date": "2024-06-11"},
         "router_state": router_state(K, cap, 0.2)},
        prs, tel, olt_series(cap, 0, 0, 0),
        {"onu": {"responds": False, "online": None, "rx_power": None, "tx_power": None,
                 "auth_flag": None, "exchange": None, "rtt_tq": None},
         "olt": {"ping_ok": False, "snmp_responds": False, "sys_uptime_seconds": None,
                 "oid_subtree_responds": None},
         "pon_probe": pon_probe(port, idxs, {}, responds_by_idx={i: False for i in idxs}),
         "vlan_walk": {"responds": False, "vlans_present": [],
                       "customer_vlan_expected": vlan_for(K, port), "customer_vlan_actual": None}},
        {"sessions": sessions(cap, 1, 14, 704, 2.0, 2, "10.5.50.102"),
         "radius": radius(m, lid, "10.5.50.102"),
         "traffic": traffic([990, 1040, 960, 1010, 980, 1020, 190], cur=0, avg=141, peak=420)},
        {"fault_type": "olt_failure",
         "root_cause": "The OLT is not reachable by ICMP and does not answer SNMP. All 139 customers behind it lost service two hours ago. The device is down, powered off, or isolated from the management and transport network.",
         "severity": "Disaster", "affected_scope": "olt",
         "affected_lineids": [], "affected_customer_count": e["cust"],
         "service_impact": True,
         "expected_reasoning": [
             "Ping to the OLT fails, so the health check stopped before any SNMP test was attempted",
             "The live probe confirms neither ICMP nor SNMP answers",
             "No ONU on the OLT responds, and no probe returns a definite online or offline state",
             "This differs from the firmware mismatch case, where ping and SNMP both succeed",
             "All 139 customers on the OLT are offline and sessions ended together two hours ago",
             "Optical readings are stale by 118 minutes, consistent with polling stopping when the device went down",
             "The upstream router is still checking in normally, so the fault is the OLT and not the router",
             "Traffic through the OLT has fallen to zero",
             "Unreachable by both ICMP and SNMP with total customer loss is a device or transport failure"],
         "required_evidence": ["ping_and_snmp_both_fail", "all_customers_affected",
                               "router_still_reachable"],
         "expected_remediation": "escalate_infrastructure",
         "expected_escalation": {"priority": "Disaster", "category": "infrastructure",
                                 "requires_human_review": False, "review_reason": None},
         "distractors": ["Zero values in olt_metrics could be read as healthy low utilisation",
                         "Stale cached readings might be mistaken for current state"]})


# ================================================================ OF-002
def of002():
    cap = datetime(2026, 9, 17, 14, 55, tzinfo=timezone.utc)
    K, port, idx = "KO14", 6, 20
    lid, m = onu_mac(), cpe_mac()
    e = ESTATE[K]
    start, tel = healthy_series(cap, rx_base=-20.0, dist=201)
    for k in ("rx_power", "tx_power", "temperature", "tx_bias_current", "supply_voltage"):
        tel[k] = tel[k][:120] + [None] * (H - 120)
    prs, idxs, sidx = make_peers(K, port, lid, -20.03, n_on_port=22, n_listed=7, subject_idx=idx)
    return assemble(
        "OF-002", "olt_failure", "medium", cap,
        "An OLT answers ping but not SNMP; monitoring has gone blind while every customer behind it is still in service.",
        ["Is loss of monitoring separated from loss of service?",
         "Is service_impact judged independently of alarm severity?",
         "Is the customer-facing conclusion drawn from customer-facing evidence?"],
        {"type": "health_check_alarm",
         "input": {"olt_host": e["host"], "overall_status": "critical",
                   "error_description": "SNMP community string not accessible, OLT does not respond to SNMP queries"}},
        subscriber(K, port, idx, lid, m, model_i=1, profile="profile_40M"),
        {"onu_status": 1, "rx_power": "-20.03", "tx_power": "2.38", "reading_age_minutes": 2880,
         "olt_health": {"olt_ip": e["ip"], "olt_host": e["host"], "olt_technology": "EPON",
                        "olt_ext_id": e["ext"], "ping_ok": True, "snmp_community_ok": False,
                        "snmp_response_ok": False, "total_pons_tested": 0, "healthy_pons": 0,
                        "failed_pons_list": [],
                        "error_description": "SNMP community string not accessible, OLT does not respond to SNMP queries",
                        "overall_status": "critical", "run_date": "2026-09-17"},
         "olt_metrics": {"cpu_load": 0, "memory_usage": 0, "temperature": 0,
                         "uptime_days": 0, "firmware": e["fw"], "firmware_date": "2025-11-28"},
         "router_state": router_state(K, cap, 0.3)},
        prs, tel, {"interval": "1h", "window_hours": H,
                   "series_start": iso(cap - timedelta(hours=H - 1)),
                   "cpu_load": [int(max(0, min(48, _rng.gauss(23, 3)))) for _ in range(120)] + [None] * 48,
                   "memory_usage": [int(max(0, min(76, _rng.gauss(18, 1.5)))) for _ in range(120)] + [None] * 48,
                   "temperature": [int(max(0, min(68, _rng.gauss(43, 2)))) for _ in range(120)] + [None] * 48},
        {"onu": {"responds": False, "online": None, "rx_power": None, "tx_power": None,
                 "auth_flag": None, "exchange": None, "rtt_tq": None},
         "olt": {"ping_ok": True, "snmp_responds": False, "sys_uptime_seconds": None,
                 "oid_subtree_responds": None},
         "pon_probe": pon_probe(port, idxs, {}, responds_by_idx={i: False for i in idxs}),
         "vlan_walk": {"responds": False, "vlans_present": [],
                       "customer_vlan_expected": vlan_for(K, port), "customer_vlan_actual": None}},
        {"sessions": sessions(cap, 2, 15, 688, 16.4, 3, "10.5.50.73"),
         "radius": radius(m, lid, "10.5.50.73"),
         "traffic": traffic([1010, 1060, 980, 1030, 1000, 1070, 1020], cur=174, avg=169, peak=510)},
        {"fault_type": "olt_failure",
         "root_cause": "The OLT's SNMP agent has stopped answering while the device continues to forward traffic. Ping succeeds, customers are authenticated and passing normal traffic, and only the monitoring path is broken.",
         "severity": "Warning", "affected_scope": "olt",
         "affected_lineids": [], "affected_customer_count": 0,
         "service_impact": False,
         "expected_reasoning": [
             "The health check reports critical, but its two SNMP flags come from a single sysUpTime read and are always equal, so the wording distinguishes nothing",
             "Ping succeeds, so the device is powered and reachable on the management network",
             "No SNMP query answers, so no ONU can be probed and no device metrics can be collected",
             "Telemetry for both the ONU and the OLT stops 48 hours ago, matching when SNMP failed",
             "Cached optical readings are 2880 minutes old for the same reason",
             "Customer-facing evidence is intact: sessions are active with normal durations and daily traffic is unchanged across all seven days",
             "Service therefore continues normally; what has been lost is visibility, not connectivity",
             "The correct conclusion is a monitoring-path failure on a serving OLT, not a customer outage"],
         "required_evidence": ["ping_succeeds_snmp_fails", "customers_passing_traffic",
                               "telemetry_stopped_at_same_time"],
         "expected_remediation": "escalate_infrastructure",
         "expected_escalation": {"priority": "Warning", "category": "monitoring",
                                 "requires_human_review": True,
                                 "review_reason": "SNMP agent or community configuration on a serving OLT; no customer impact but the estate is unmonitored"},
         "distractors": ["A critical alarm on a whole OLT invites a Disaster severity",
                         "Zeroed olt_metrics could be read as a failing device",
                         "Every probe returns no response, which resembles the firmware mismatch signature"]})


BUILDERS = [fd002, fd003, ld001, ld002, dc001, dc002,
            oo001, oo002, oo003, pp001, pp002, pp003, sp001, of001, of002]
