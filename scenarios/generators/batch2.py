#!/usr/bin/env python3
"""Scenario builders: FC, RU, RA, SF, DS, SV, CD, CG, NF families."""
import math
from datetime import datetime, timedelta, timezone
from estate import *
from estate import _rng
from batch1 import assemble


# ================================================================ FC-002
def fc002():
    cap = datetime(2026, 9, 19, 13, 10, tzinfo=timezone.utc)
    K, port, idx = "VE05", 7, 5
    e = ESTATE[K]
    lid, m = onu_mac(), cpe_mac()
    start, tel = healthy_series(cap, rx_base=-21.4, dist=166)
    for k in ("rx_power", "tx_power", "tx_bias_current", "supply_voltage", "temperature", "speed_kbps"):
        tel[k] = cliff(tel[k], 159, None)
    tel["distance"] = cliff(tel["distance"], 159, None)
    prs, idxs, sidx = make_peers(K, port, lid, "0", subject_status=0, n_on_port=31,
                                 n_listed=8, subject_idx=idx)
    prs["crm_view"]["customers"] = [{**c, "onu_status": 0, "rx_power": "0"}
                                    for c in prs["crm_view"]["customers"]]
    affected = [c["lineid"] for c in prs["crm_view"]["customers"]]
    prs["olt_population"]["onu_offline_count"] = 31 + 12
    prs["olt_population"]["onu_online_count"] = e["cust"] - 43
    failed = [f"EPON0/{i}:1" for i in range(1, e["ports"] + 1) if i != 7]
    return assemble(
        "FC-002", "olt_health_false_critical", "hard", cap,
        "[mechanism_b] Seven of eight PONs failed, so the health check wrote 'healthy' with a null error string while a genuine port outage runs underneath it.",
        ["Is the all-or-nothing status rule recognised?",
         "Are the detail fields compared against the summary label?",
         "Is a real outage found despite a healthy verdict?"],
        {"type": "scheduled_scan", "input": {"scope": "olt", "target": e["host"]}},
        subscriber(K, port, idx, lid, m, model_i=0, profile="profile_20M"),
        {"onu_status": 0, "rx_power": "0", "tx_power": "0", "reading_age_minutes": 9,
         "olt_health": {**healthy_olt_health(K, "2026-09-19"), "healthy_pons": 1,
                        "failed_pons_list": failed, "total_pons_tested": 8,
                        "error_description": None, "overall_status": "healthy"},
         "olt_metrics": olt_metrics(K, 26, 19, 44, 68),
         "router_state": router_state(K, cap, 0.3)},
        prs, tel, olt_series(cap, 26, 19, 44),
        {"onu": {"responds": True, "online": 0, "rx_power": None, "tx_power": None,
                 "auth_flag": "Unauth", "exchange": "MPCP DEREG", "rtt_tq": None},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 5875200,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {}, online_by_idx={i: 0 for i in idxs}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": sessions(cap, 1, 15, 691, 1.7, 2, "10.5.50.119"),
         "radius": radius(m, lid, "10.5.50.119"),
         "traffic": traffic([1040, 1000, 1080, 1020, 990, 1050, 430], cur=6, avg=219, peak=660)},
        {"fault_type": "olt_health_false_critical",
         "root_cause": "The health check marks an OLT critical only when every sampled PON fails. Seven of eight failed here, so it wrote 'healthy' with a null error description while healthy_pons stood at 1 of 8 in the same record. A genuine multi-port outage is running underneath a healthy verdict.",
         "severity": "High", "affected_scope": "olt",
         "affected_lineids": [], "affected_customer_count": 43,
         "service_impact": True,
         "expected_reasoning": [
             "The health record reports overall_status healthy with a null error description",
             "The same record holds healthy_pons 1 against total_pons_tested 8, and seven entries in failed_pons_list",
             "The summary label contradicts the detail fields inside one record",
             "The check sets critical only when every sampled PON fails, so seven of eight yields healthy by design",
             "Probing confirms every ONU on EPON0/7 returns responds true with online 0, a definite negative",
             "oid_subtree_responds is true, so this is not the firmware mismatch mechanism",
             "43 of 272 customers on the OLT are offline, far above the 4.85% background rate",
             "Sessions ended together and PON traffic has collapsed from 219 to 6 Mbps",
             "This is a genuine multi-port outage that the health check's status rule conceals"],
         "required_evidence": ["healthy_label_contradicts_detail_fields",
                               "definite_offline_not_no_response",
                               "customers_not_passing_traffic"],
         "expected_remediation": "escalate_infrastructure",
         "expected_escalation": {"priority": "High", "category": "infrastructure",
                                 "requires_human_review": True,
                                 "review_reason": "The health check reported healthy during a seven-port outage; the status rule needs correcting"},
         "distractors": ["The health record says healthy, inviting a no_fault conclusion",
                         "A scheduled scan with no complaint gives no reason to look harder",
                         "The fault type is a health check defect but the service impact is real"]},
        gaps=[{"signal": "rx_power", "from_index": 159, "to_index": 167}])


# ================================================================ FC-003
def fc003():
    cap = datetime(2026, 9, 16, 15, 40, tzinfo=timezone.utc)
    K, port, idx = "OHSC02", 3, 1
    e = ESTATE[K]
    lid, m = onu_mac(), cpe_mac()
    start, tel = healthy_series(cap, rx_base=-22.2, dist=210)
    for k in ("rx_power", "tx_power", "tx_bias_current", "supply_voltage", "temperature", "speed_kbps"):
        tel[k] = cliff(tel[k], 84, None)
    tel["distance"] = cliff(tel["distance"], 84, None)
    prs, idxs, sidx = make_peers(K, port, lid, "0", subject_status=0, n_on_port=28,
                                 n_listed=8, subject_idx=idx)
    return assemble(
        "FC-003", "olt_health_false_critical", "hard", cap,
        "[mechanism_c] One dead sample ONU condemns a healthy PON port: the check tests ONU id 1 per port, and on this port ONU 1 is the only one that is down.",
        ["Is the one-ONU sampling design recognised?",
         "Is the rest of the port probed rather than the sample trusted?",
         "Is the real single-customer fault reported without inflating its scope?"],
        {"type": "health_check_alarm",
         "input": {"olt_host": e["host"], "overall_status": "critical",
                   "error_description": f"All PONs failed ({e['ports']}/{e['ports']})"}},
        subscriber(K, port, idx, lid, m, model_i=2, profile="profile_20M"),
        {"onu_status": 0, "rx_power": "0", "tx_power": "0", "reading_age_minutes": 13,
         "olt_health": {**healthy_olt_health(K, "2026-09-16"), "healthy_pons": 0,
                        "failed_pons_list": [f"EPON0/{i}:1" for i in range(1, e["ports"] + 1)],
                        "error_description": f"All PONs failed ({e['ports']}/{e['ports']})",
                        "overall_status": "critical"},
         "olt_metrics": olt_metrics(K, 23, 17, 41, 33),
         "router_state": router_state(K, cap, 0.4)},
        prs, tel, olt_series(cap, 23, 17, 41),
        {"onu": {"responds": True, "online": 0, "rx_power": None, "tx_power": None,
                 "auth_flag": "Unauth", "exchange": "MPCP DEREG", "rtt_tq": None},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 2851200,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {}, online_by_idx={sidx: 0}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": sessions(cap, 1, 12, 699, 81.0, 2, "10.5.50.140"),
         "radius": radius(m, lid, "10.5.50.140"),
         "traffic": traffic([980, 1020, 960, 400, 0, 0, 0], cur=188, avg=182, peak=545)},
        {"fault_type": "olt_health_false_critical",
         "root_cause": "The health check samples one ONU per PON port, preferring ONU id 1. On several ports the id 1 ONU happens to be offline for individual reasons, so each port is marked failed and the OLT is reported critical. The ports and the OLT are serving normally; one customer is genuinely offline.",
         "severity": "Information", "affected_scope": "single_customer",
         "affected_lineids": [lid], "affected_customer_count": 1,
         "service_impact": True,
         "expected_reasoning": [
             "The alarm claims all seven PONs failed on this OLT",
             "The failed_pons_list names ONU index 1 on every port, which is the check's preferred sample",
             "Probing the rest of EPON0/3 shows 27 of 28 ONUs online with normal RX and TX",
             "So the port is serving and only the sampled ONU is down",
             "oid_subtree_responds is true and the probe returns definite answers, ruling out the firmware mechanism",
             "OLT ping, SNMP, CPU, memory, temperature and 33 days of uptime are all normal",
             "CRM offline count across the OLT is consistent with the 4.85% background rate",
             "The subject ONU last held a session three days ago and its traffic has been zero since",
             "The alarm is a sampling artifact; the only real fault is one customer offline for three days"],
         "required_evidence": ["rest_of_port_online", "sample_onu_is_the_only_failure",
                               "olt_metrics_normal"],
         "expected_remediation": "dispatch_technician",
         "expected_escalation": {"priority": "Average", "category": "field_service",
                                 "requires_human_review": True,
                                 "review_reason": "The health check's one-ONU-per-port sampling produced a false OLT-wide critical; monitoring should be raised separately"},
         "distractors": ["An OLT-wide critical invites a Disaster conclusion",
                         "Every port genuinely reports a failed sample, so the alarm looks internally consistent",
                         "There is a real fault here, so dismissing the alarm entirely would also miss it"]},
        gaps=[{"signal": "rx_power", "from_index": 84, "to_index": 167}])


# ================================================================ FC-004
def fc004():
    cap = datetime(2026, 9, 23, 11, 0, tzinfo=timezone.utc)
    K, port, idx = "KV03", 5, 16
    e = ESTATE[K]
    lid, m = onu_mac(), cpe_mac()
    start, tel = healthy_series(cap, rx_base=-19.7, dist=124)
    prs, idxs, sidx = make_peers(K, port, lid, -19.68, n_on_port=25, n_listed=7, subject_idx=idx)
    return assemble(
        "FC-004", "olt_health_false_critical", "hard", cap,
        "[mechanism_d] A ten-month-old health record is presented as current state; the OLT has been healthy for months and the check has simply not run.",
        ["Is the age of a stored record checked before it is trusted?",
         "Is a stale alarm separated from a current one?",
         "Is the absence of monitoring itself reported as the finding?"],
        {"type": "health_check_alarm",
         "input": {"olt_host": e["host"], "overall_status": "critical",
                   "error_description": "All PONs failed (8/8)"}},
        subscriber(K, port, idx, lid, m, model_i=0, profile="profile_20M"),
        {"onu_status": 1, "rx_power": "-19.68", "tx_power": "2.41", "reading_age_minutes": 17,
         "olt_health": {**healthy_olt_health(K, "2025-11-11"), "healthy_pons": 0,
                        "failed_pons_list": [f"EPON0/{i}:1" for i in range(1, 9)],
                        "error_description": "All PONs failed (8/8)",
                        "overall_status": "critical"},
         "olt_metrics": olt_metrics(K, 24, 18, 42, 58),
         "router_state": router_state(K, cap, 0.2)},
        prs, tel, olt_series(cap, 24, 18, 42),
        {"onu": {"responds": True, "online": 1, "rx_power": -19.71, "tx_power": 2.42,
                 "auth_flag": "Auth", "exchange": "Finish", "rtt_tq": 58},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 5011200,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {sidx: -19.71}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": sessions(cap, 2, 16, 706, 11.2, 3, "10.5.50.51"),
         "radius": radius(m, lid, "10.5.50.51"),
         "traffic": traffic([1010, 1050, 990, 1030, 1000, 1060, 1020], cur=181, avg=177, peak=530)},
        {"fault_type": "olt_health_false_critical",
         "root_cause": "The stored health record carries a run_date of 2025-11-11, ten months before the current date. The health check has not run since. The OLT has 58 days of uptime, answers every probe normally and is serving all its customers; the alarm describes a condition that no longer exists, if it ever did.",
         "severity": "Information", "affected_scope": "none",
         "affected_lineids": [], "affected_customer_count": 0,
         "service_impact": False,
         "expected_reasoning": [
             "The health record reports critical with all eight PONs failed",
             "Its run_date is 2025-11-11, ten months before the scenario's capture time",
             "A stored record that old describes history, not current state",
             "The live probe answers normally: the ONU is online with RX -19.71 and TX 2.42",
             "OLT ping and SNMP succeed, oid_subtree_responds is true and uptime is 58 days",
             "58 days of uptime postdates the stored record, so the device has restarted since it was written",
             "CPU 24, memory 18 and temperature 42 are all at healthy baseline",
             "Customers are authenticated with normal sessions and seven days of steady traffic",
             "The finding is not an outage but that OLT health monitoring has not run for ten months"],
         "required_evidence": ["record_age_checked", "live_probe_contradicts_record",
                               "uptime_postdates_record"],
         "expected_remediation": "flag_monitoring_defect",
         "expected_escalation": {"priority": "Information", "category": "monitoring",
                                 "requires_human_review": True,
                                 "review_reason": "OLT health checks have not run since 2025-11-11; the schedule is not active"},
         "distractors": ["The alarm text is identical to a genuine critical",
                         "The record is internally consistent and only its date betrays it",
                         "Nothing in the alarm payload signals that it is stale"]})


# ================================================================ RU-001
def ru001():
    cap = datetime(2026, 9, 20, 3, 25, tzinfo=timezone.utc)
    K, port, idx = "JAD04", 2, 13
    lid, m = onu_mac(), cpe_mac()
    start, tel = healthy_series(cap, rx_base=-20.6, dist=152)
    tel["speed_kbps"] = [r2(max(0.02, _rng.gauss(5.3, 2.2))) if i < 161 else 0.0 for i in range(H)]
    prs, idxs, sidx = make_peers(K, port, lid, -20.58, n_on_port=26, n_listed=7, subject_idx=idx)
    return assemble(
        "RU-001", "router_unreachable", "easy", cap,
        "A BNG has stopped checking in and its customers have lost service while every ONU behind it stays optically healthy and online.",
        ["Is the fault located at the router rather than the optical plant?",
         "Are healthy ONUs with dead sessions recognised as the signature?",
         "Is the blast radius extended across OLTs served by the router?"],
        {"type": "threshold_breach", "input": {"signal": "router_heartbeat_stale",
                                               "olt_host": ESTATE[K]["host"], "value": 7.4}},
        subscriber(K, port, idx, lid, m, model_i=0, profile="profile_20M"),
        {"onu_status": 1, "rx_power": "-20.58", "tx_power": "2.39", "reading_age_minutes": 21,
         "olt_health": healthy_olt_health(K, "2026-09-20"),
         "olt_metrics": olt_metrics(K, 24, 18, 42, 71),
         "router_state": router_state(K, cap, 7.4, "danger")},
        prs, tel, olt_series(cap, 24, 18, 42),
        {"onu": {"responds": True, "online": 1, "rx_power": -20.61, "tx_power": 2.40,
                 "auth_flag": "Auth", "exchange": "Finish", "rtt_tq": 63},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 6134400,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {sidx: -20.61}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": sessions(cap, 1, 14, 701, 7.4, 2, "10.5.50.96"),
         "radius": radius(m, lid, "10.5.50.96"),
         "traffic": traffic([1020, 980, 1050, 1000, 1030, 990, 290], cur=0, avg=207, peak=620)},
        {"fault_type": "router_unreachable",
         "root_cause": "The BNG TK_AZ_Bitola_Jadranska01 stopped checking in 7.4 hours ago. Customers behind it lost their sessions at the same moment. The optical plant is entirely unaffected: ONUs remain registered and are returning normal signal readings.",
         "severity": "Disaster", "affected_scope": "router",
         "affected_lineids": [], "affected_customer_count": 271,
         "service_impact": True,
         "expected_reasoning": [
             "Router heartbeat is 7.4 hours stale, past the 4 hour danger threshold",
             "The ONU is online with RX -20.6 and TX 2.4, both normal, and the live probe confirms it",
             "Every peer on the port is also online with normal optical readings",
             "OLT ping, SNMP and device metrics are all healthy",
             "So the optical layer is working and the fault is not in the fibre plant",
             "Sessions across customers on this router ended together 7.4 hours ago",
             "Throughput fell to zero at the same moment while the ONUs stayed registered",
             "Healthy ONUs with dead sessions is the router signature: the optical layer carries no traffic without the BNG",
             "The blast radius follows the router, not the OLT, so every customer it serves is affected"],
         "required_evidence": ["heartbeat_past_danger_threshold", "onus_online_and_optically_healthy",
                               "sessions_ended_together"],
         "expected_remediation": "escalate_infrastructure",
         "expected_escalation": {"priority": "Disaster", "category": "infrastructure",
                                 "requires_human_review": False, "review_reason": None},
         "distractors": ["ONU status is online everywhere, inviting a no_fault conclusion",
                         "The OLT health check reports healthy, which is correct but irrelevant",
                         "Optical readings are perfect, which points away from where the fault is"]})


# ================================================================ RU-002
def ru002():
    cap = datetime(2026, 9, 21, 12, 40, tzinfo=timezone.utc)
    K, port, idx = "MADZ01", 4, 23
    lid, m = onu_mac(), cpe_mac()
    start, tel = healthy_series(cap, rx_base=-21.9, dist=87)
    prs, idxs, sidx = make_peers(K, port, lid, -21.87, n_on_port=22, n_listed=7, subject_idx=idx)
    return assemble(
        "RU-002", "no_fault", "medium", cap,
        "A router has no check-in record at all; it was never enrolled in monitoring, and its customers are being served normally.",
        ["Is 'never checked in' separated from 'went stale'?",
         "Is an unprovisioned monitoring record distinguished from an outage?",
         "Is customer-facing evidence used to settle the question?"],
        {"type": "scheduled_scan", "input": {"scope": "router", "target": "TK_Skopje15-Madzari01"}},
        subscriber(K, port, idx, lid, m, model_i=1, profile="profile_40M"),
        {"onu_status": 1, "rx_power": "-21.87", "tx_power": "2.33", "reading_age_minutes": 15,
         "olt_health": healthy_olt_health(K, "2026-09-21"),
         "olt_metrics": olt_metrics(K, 22, 17, 40, 62),
         "router_state": router_state(K, cap, never=True)},
        prs, tel, olt_series(cap, 22, 17, 40),
        {"onu": {"responds": True, "online": 1, "rx_power": -21.90, "tx_power": 2.34,
                 "auth_flag": "Auth", "exchange": "Finish", "rtt_tq": 54},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 5356800,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {sidx: -21.90}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": sessions(cap, 3, 17, 683, 9.8, 3, "10.5.50.167"),
         "radius": radius(m, lid, "10.5.50.167"),
         "traffic": traffic([1000, 1040, 970, 1020, 1010, 1050, 990], cur=152, avg=147, peak=440)},
        {"fault_type": "no_fault",
         "root_cause": "The router has no check-in record of any kind, which means it was never enrolled in heartbeat monitoring rather than that it stopped responding. Its customers are authenticated, holding long sessions and passing normal traffic.",
         "severity": "Information", "affected_scope": "none",
         "affected_lineids": [], "affected_customer_count": 0,
         "service_impact": False,
         "expected_reasoning": [
             "The router's heartbeat status is 'never' with a null last_checkin",
             "That is different from a heartbeat that went stale, which would carry a timestamp and an elapsed time",
             "No record at all indicates the router was never enrolled in the check-in mechanism",
             "The ONU behind it is online with RX -21.9 and TX 2.3, both normal",
             "The live probe confirms the ONU and its peers are all responding normally",
             "Sessions are active with a 683 minute mean, close to the 11.9 hour network norm",
             "Daily traffic is steady across all seven days with no interruption",
             "Customers on this router are being served, so there is no outage",
             "The finding is a monitoring gap, not a network fault"],
         "required_evidence": ["never_checked_in_not_stale", "customers_passing_traffic",
                               "sessions_normal_duration"],
         "expected_remediation": "flag_monitoring_defect",
         "expected_escalation": {"priority": "Information", "category": "monitoring",
                                 "requires_human_review": True,
                                 "review_reason": "Router is not enrolled in heartbeat monitoring and should be added"},
         "distractors": ["A null heartbeat looks worse than a stale one and invites a Disaster conclusion",
                         "A scheduled scan targeting the router frames it as the suspect",
                         "The correct answer is that nothing is wrong with the network"]})


# ================================================================ RA-001
def ra001():
    cap = datetime(2026, 9, 18, 8, 50, tzinfo=timezone.utc)
    K, port, idx = "GRAD01", 3, 28
    lid, m = onu_mac(), cpe_mac()
    start, tel = healthy_series(cap, rx_base=-19.5, dist=63)
    tel["speed_kbps"] = [0.0] * H
    prs, idxs, sidx = make_peers(K, port, lid, -19.52, n_on_port=30, n_listed=7, subject_idx=idx)
    return assemble(
        "RA-001", "radius_missing_entry", "easy", cap,
        "A newly provisioned customer has a perfect optical layer and no RADIUS entry, so authentication never happens.",
        ["Is a healthy physical layer with no service recognised?",
         "Is the absence of a RADIUS entry found?",
         "Is an unnecessary technician dispatch avoided?"],
        {"type": "customer_complaint",
         "input": {"lineid": lid, "complaint": "New connection installed yesterday, never worked"}},
        subscriber(K, port, idx, lid, m, model_i=0, profile="profile_20M"),
        {"onu_status": 1, "rx_power": "-19.52", "tx_power": "2.47", "reading_age_minutes": 18,
         "olt_health": healthy_olt_health(K, "2026-09-18"),
         "olt_metrics": olt_metrics(K, 25, 18, 43, 44),
         "router_state": router_state(K, cap, 0.2)},
        prs, tel, olt_series(cap, 25, 18, 43),
        {"onu": {"responds": True, "online": 1, "rx_power": -19.55, "tx_power": 2.48,
                 "auth_flag": "Auth", "exchange": "Finish", "rtt_tq": 51},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 3801600,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {sidx: -19.55}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": {"count_24h": 0, "count_7d": 0, "avg_duration_minutes": 0,
                      "last_disconnect": None, "recent": []},
         "radius": radius(m, lid, None, exists=False, consistent=False, mismatches=[
             {"type": "missing_radcheck",
              "detail": "The customer is active in CRM with a CPE MAC but has no radcheck row. The provisioning step that creates the RADIUS user did not complete."}]),
         "traffic": traffic([0, 0, 0, 0, 0, 0, 0], up=[0] * 7, cur=196, avg=201, peak=590)},
        {"fault_type": "radius_missing_entry",
         "root_cause": "The customer has no radcheck row, so every authentication attempt is rejected and no session is ever established. The provisioning step that writes the RADIUS user did not complete when the line was installed.",
         "severity": "Average", "affected_scope": "single_customer",
         "affected_lineids": [lid], "affected_customer_count": 1, "service_impact": True,
         "expected_reasoning": [
             "The ONU is online with RX -19.52 and TX 2.47, both comfortably normal",
             "The live probe confirms the ONU and its peers are responding normally",
             "The OLT and router are healthy, so no shared infrastructure fault exists",
             "The physical layer is therefore working end to end",
             "Despite that, the customer has zero sessions in both the 24 hour and 7 day windows",
             "RADIUS holds no radcheck row for this CPE MAC, so authentication cannot succeed",
             "Daily traffic is zero for all seven days, consistent with never having been authenticated",
             "A healthy physical layer with an absent RADIUS entry is a provisioning failure, not a network fault",
             "No technician visit is warranted; the RADIUS entry needs creating"],
         "required_evidence": ["physical_layer_confirmed_healthy", "radcheck_absent",
                               "zero_sessions_since_install"],
         "expected_remediation": "create_radius_entry",
         "expected_escalation": {"priority": "Average", "category": "provisioning",
                                 "requires_human_review": False, "review_reason": None},
         "distractors": ["A brand new connection that never worked suggests an installation fault",
                         "Zero traffic could be read as a dead line"]})


# ================================================================ RA-002
def ra002():
    cap = datetime(2026, 9, 19, 19, 15, tzinfo=timezone.utc)
    K, port, idx = "ANC08", 4, 34
    lid, m = onu_mac(), cpe_mac()
    start, tel = healthy_series(cap, rx_base=-22.4, dist=178)
    prs, idxs, sidx = make_peers(K, port, lid, -22.41, n_on_port=32, n_listed=7, subject_idx=idx)
    return assemble(
        "RA-002", "radius_suspended_but_serving", "medium", cap,
        "A customer suspended in CRM is still on the standard subscriber pool and consuming normal traffic; the assigned IP settles which system is right.",
        ["Is the IP range used to verify service state rather than a status flag?",
         "Is the CRM/RADIUS disagreement identified as the fault?",
         "Is service_impact judged correctly when the customer is getting more than they should?"],
        {"type": "scheduled_scan", "input": {"scope": "network", "target": None}},
        subscriber(K, port, idx, lid, m, model_i=0, profile="profile_20M", active=0),
        {"onu_status": 1, "rx_power": "-22.41", "tx_power": "2.35", "reading_age_minutes": 26,
         "olt_health": healthy_olt_health(K, "2026-09-19"),
         "olt_metrics": olt_metrics(K, 24, 17, 41, 86),
         "router_state": router_state(K, cap, 0.3)},
        prs, tel, olt_series(cap, 24, 17, 41),
        {"onu": {"responds": True, "online": 1, "rx_power": -22.44, "tx_power": 2.36,
                 "auth_flag": "Auth", "exchange": "Finish", "rtt_tq": 69},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 7430400,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {sidx: -22.44}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": sessions(cap, 2, 16, 715, 13.6, 3, "10.5.50.188"),
         "radius": radius(m, lid, "10.5.50.188", consistent=False, mismatches=[
             {"type": "disabled_not_pooled",
              "detail": "CRM marks this customer inactive but RADIUS has no Framed-Pool set, so the suspension was never applied. The customer holds an address in pool_Users."}]),
         "traffic": traffic([1080, 1010, 1120, 1040, 1000, 1090, 1050], cur=214, avg=209, peak=645)},
        {"fault_type": "radius_suspended_but_serving",
         "root_cause": "The customer is marked inactive in CRM but RADIUS never applied the suspension. Framed-Pool is unset and the assigned address is in pool_Users, so full service continues. This is one of the 218 such cases in the estate.",
         "severity": "Warning", "affected_scope": "single_customer",
         "affected_lineids": [lid], "affected_customer_count": 1, "service_impact": False,
         "expected_reasoning": [
             "CRM marks the customer inactive, which should mean service is suspended",
             "RADIUS has a radcheck row with no Framed-Pool set",
             "A suspended customer should be assigned to pool_Disable_Users and hold an address in 10.200.200.0/24",
             "The assigned address is 10.5.50.188, which is in pool_Users, the standard subscriber range",
             "The IP range settles the question without relying on either system's status flag",
             "Sessions are active with a 715 minute mean and traffic is normal across all seven days",
             "The customer is therefore receiving full service despite being suspended in CRM",
             "The optical layer is healthy and irrelevant to this fault",
             "There is no service impact for the customer; the impact is commercial"],
         "required_evidence": ["ip_in_standard_pool_not_disable_pool", "crm_marks_inactive",
                               "traffic_confirms_live_service"],
         "expected_remediation": "apply_disable_pool",
         "expected_escalation": {"priority": "Warning", "category": "provisioning",
                                 "requires_human_review": False, "review_reason": None},
         "distractors": ["Every technical signal is healthy, inviting a no_fault conclusion",
                         "No customer has complained and none will",
                         "service_impact is false even though a genuine fault exists"]})


# ================================================================ RA-003
def ra003():
    cap = datetime(2026, 9, 17, 11, 30, tzinfo=timezone.utc)
    K, port, idx = "SR01", 5, 14
    lid, m = onu_mac(), cpe_mac()
    old_lid = onu_mac()
    start, tel = healthy_series(cap, rx_base=-20.1, dist=145)
    tel["distance"] = [145] * H
    prs, idxs, sidx = make_peers(K, port, lid, -20.13, n_on_port=20, n_listed=7, subject_idx=idx)
    return assemble(
        "RA-003", "radius_lineid_conflict", "medium", cap,
        "After an ONU swap the CRM lineid was updated and the RADIUS lineid was not; session history is being attributed to a device that no longer exists.",
        ["Is the cross-system key mismatch found?",
         "Is it separated from a CRM-internal duplicate?",
         "Is automated correction correctly avoided?"],
        {"type": "customer_complaint",
         "input": {"lineid": lid, "complaint": "Works fine but my usage history in the portal is wrong"}},
        subscriber(K, port, idx, lid, m, model_i=4, profile="profile_30M_1M"),
        {"onu_status": 1, "rx_power": "-20.13", "tx_power": "2.42", "reading_age_minutes": 22,
         "olt_health": healthy_olt_health(K, "2026-09-17"),
         "olt_metrics": olt_metrics(K, 21, 16, 39, 88),
         "router_state": router_state(K, cap, 0.5)},
        prs, tel, olt_series(cap, 21, 16, 39),
        {"onu": {"responds": True, "online": 1, "rx_power": -20.16, "tx_power": 2.43,
                 "auth_flag": "Auth", "exchange": "Finish", "rtt_tq": 57},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 7603200,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {sidx: -20.16}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": sessions(cap, 2, 15, 702, 10.4, 3, "10.5.50.132"),
         "radius": {"radcheck_exists": True, "username": m, "lineid_in_radius": old_lid,
                    "framed_pool": None, "assigned_ip": "10.5.50.132",
                    "crm_consistent": False,
                    "mismatches": [
                        {"type": "lineid_conflict",
                         "detail": f"radcheck.lineid is {old_lid} while crm_user_net.lineid is {lid} for the same username. The ONU was replaced on 2026-08-30 and CRM was updated; RADIUS was not."},
                        {"type": "orphan_radcheck",
                         "detail": f"The superseded ONU MAC {old_lid} no longer corresponds to any installed device."}]},
         "traffic": traffic([1030, 1070, 1000, 1050, 1010, 1080, 1040], cur=143, avg=139, peak=410)},
        {"fault_type": "radius_lineid_conflict",
         "root_cause": "The ONU was replaced on 30 August. CRM was updated with the new ONU MAC but the RADIUS lineid still carries the superseded one, so accounting records are written against a device that is no longer installed.",
         "severity": "Warning", "affected_scope": "single_customer",
         "affected_lineids": [lid], "affected_customer_count": 1, "service_impact": False,
         "expected_reasoning": [
             "The customer reports incorrect usage history while service itself works",
             "Authentication succeeds because it keys on the CPE MAC, which matches in both systems",
             "The optical layer is healthy: RX -20.1, TX 2.4, distance constant, peers normal",
             "crm_user_net.lineid and radcheck.lineid hold different ONU MACs for the same username",
             "The CRM value is the installed device; the RADIUS value is a superseded one",
             "Distance has been constant at 145 m throughout, so the physical path did not change with the swap",
             "Accounting is therefore attributed to a device that no longer exists, which explains the portal discrepancy",
             "This is a cross-system key mismatch, distinct from two CRM records colliding on one interface",
             "Automated correction is unsafe here because the wrong row could be rewritten"],
         "required_evidence": ["crm_and_radius_lineids_differ", "authentication_still_succeeds",
                               "physical_layer_healthy"],
         "expected_remediation": "manual_review",
         "expected_escalation": {"priority": "Warning", "category": "provisioning",
                                 "requires_human_review": True,
                                 "review_reason": "Correcting a RADIUS lineid risks disconnecting the wrong customer and must be done by hand"},
         "distractors": ["Service works normally, inviting a no_fault conclusion",
                         "The complaint is about a portal display rather than connectivity",
                         "The mismatch resembles a duplicate slot conflict but is cross-system"]})


# ================================================================ RA-004
def ra004():
    cap = datetime(2026, 9, 22, 16, 5, tzinfo=timezone.utc)
    K, port, idx = "PP03", 2, 26
    lid, m = onu_mac(), cpe_mac()
    start, tel = healthy_series(cap, rx_base=-21.0, dist=228)
    tel["speed_kbps"] = [0.0 if i % 7 in (3, 4) else r2(max(0.05, _rng.gauss(5.6, 2.3)))
                         for i in range(H)]
    prs, idxs, sidx = make_peers(K, port, lid, -21.02, n_on_port=27, n_listed=7, subject_idx=idx)
    return assemble(
        "RA-004", "radius_replication_lag", "hard", cap,
        "A customer authenticates against one RADIUS server and is rejected by the other; the two hold different state for the same username and neither the optical nor the session layer alone reveals it.",
        ["Is inconsistency across servers identified as the cause?",
         "Is intermittency correctly attributed to which server answered?",
         "Is the optical layer conclusively ruled out first?"],
        {"type": "customer_complaint",
         "input": {"lineid": lid, "complaint": "Drops every couple of hours then comes back by itself"}},
        subscriber(K, port, idx, lid, m, model_i=1, profile="profile_80M"),
        {"onu_status": 1, "rx_power": "-21.02", "tx_power": "2.38", "reading_age_minutes": 9,
         "olt_health": healthy_olt_health(K, "2026-09-22"),
         "olt_metrics": olt_metrics(K, 23, 18, 42, 41),
         "router_state": router_state(K, cap, 0.2)},
        prs, tel, olt_series(cap, 23, 18, 42),
        {"onu": {"responds": True, "online": 1, "rx_power": -21.05, "tx_power": 2.39,
                 "auth_flag": "Auth", "exchange": "Finish", "rtt_tq": 71},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 3542400,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {sidx: -21.05}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": sessions(cap, 13, 79, 104, 1.1, 5, ips=["10.5.50.212", "10.5.50.212", "10.5.50.212"]),
         "radius": {"radcheck_exists": True, "username": m, "lineid_in_radius": lid,
                    "framed_pool": None, "assigned_ip": "10.5.50.212",
                    "crm_consistent": False,
                    "mismatches": [
                        {"type": "replication_lag",
                         "detail": "The primary FreeRADIUS holds a current radcheck row for this username. The secondary holds a stale row whose password was changed during a profile upgrade on 2026-09-20 and has not replicated. Authentication succeeds against the primary and is rejected by the secondary."},
                        {"type": "replication_lag",
                         "detail": "Session starts correlate with which server answered: accepted sessions begin within seconds of a primary response, rejected attempts cluster when the MikroTik failed over to the secondary."}]},
         "traffic": traffic([980, 640, 1010, 590, 950, 620, 900], cur=201, avg=225, peak=670)},
        {"fault_type": "radius_replication_lag",
         "root_cause": "A password change made during a profile upgrade on 20 September replicated to the primary FreeRADIUS but not the secondary. When the MikroTik fails over, the secondary rejects the customer; when the primary answers, authentication succeeds. The result is repeated disconnection and recovery with no physical cause.",
         "severity": "Average", "affected_scope": "single_customer",
         "affected_lineids": [lid], "affected_customer_count": 1, "service_impact": True,
         "expected_reasoning": [
             "Thirteen sessions in 24 hours against a 2-3 baseline, with a 104 minute mean against an 11.9 hour norm",
             "RX has been flat at -21.0 dBm for seven days inside the noise floor, and TX, bias, voltage and distance are all stable",
             "The live probe confirms the ONU is online and healthy, and peers on the port are normal",
             "The OLT and router are healthy, so no shared infrastructure fault exists",
             "With the optical layer conclusively clean, the cause must lie in authentication",
             "The radcheck row on the primary is current, so a single-server check would find nothing wrong",
             "Comparing both servers shows the secondary holds a stale row from before the 20 September profile change",
             "Session outcomes correlate with which server answered rather than with any signal or time of day",
             "The throughput series shows recurring zero windows that match the rejected attempts",
             "Inconsistent state across replicated servers explains intermittency that no single query reveals"],
         "required_evidence": ["optical_layer_confirmed_clean", "both_radius_servers_compared",
                               "session_outcome_correlates_with_server"],
         "expected_remediation": "escalate_radius_infrastructure",
         "expected_escalation": {"priority": "Average", "category": "infrastructure",
                                 "requires_human_review": True,
                                 "review_reason": "Master-slave replication between the FreeRADIUS pair is lagging; other customers changed since 20 September may be affected"},
         "distractors": ["The session pattern is identical to signal-related flapping",
                         "The primary RADIUS record is entirely correct, so a single-server check finds nothing",
                         "Self-recovering drops suggest an intermittent physical fault",
                         "Traffic alternates between normal and reduced days, which looks like usage variation"]})


# ================================================================ SF-001
def sf001():
    cap = datetime(2026, 9, 18, 21, 50, tzinfo=timezone.utc)
    K, port, idx = "KO14", 2, 18
    lid, m = onu_mac(), cpe_mac()
    start, tel = healthy_series(cap, rx_base=-26.3, dist=302)
    tel["rx_power"] = [r2(-26.3 - 1.9 * math.sin(2 * math.pi * i / 11.0) + _rng.gauss(0, 0.25))
                       for i in range(H)]
    prs, idxs, sidx = make_peers(K, port, lid, -26.28, n_on_port=23, n_listed=7, subject_idx=idx)
    return assemble(
        "SF-001", "session_flapping_signal", "medium", cap,
        "Heavy session flapping with RX oscillating across the usable threshold; the optical signal explains the sessions.",
        ["Is flapping attributed to its optical cause rather than treated as an independent fault?",
         "Is the RX oscillation correlated with the session pattern?",
         "Is the auth layer correctly ruled out?"],
        {"type": "threshold_breach", "input": {"signal": "session_disconnect_count",
                                               "lineid": lid, "value": 16}},
        subscriber(K, port, idx, lid, m, model_i=0, profile="profile_20M"),
        {"onu_status": 1, "rx_power": "-26.28", "tx_power": "2.30", "reading_age_minutes": 7,
         "olt_health": healthy_olt_health(K, "2026-09-18"),
         "olt_metrics": olt_metrics(K, 23, 17, 42, 36),
         "router_state": router_state(K, cap, 0.3)},
        prs, tel, olt_series(cap, 23, 17, 42),
        {"onu": {"responds": True, "online": 1, "rx_power": -27.94, "tx_power": 2.29,
                 "auth_flag": "Auth", "exchange": "Finish", "rtt_tq": 94},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 3110400,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {sidx: -27.94}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": sessions(cap, 16, 94, 71, 0.6, 5, "10.5.50.176"),
         "radius": radius(m, lid, "10.5.50.176"),
         "traffic": traffic([740, 520, 680, 430, 610, 380, 490], cur=167, avg=172, peak=490)},
        {"fault_type": "session_flapping_signal",
         "root_cause": "RX power oscillates between roughly -24.4 and -28.2 dBm on an eleven hour cycle, crossing the threshold at which the link stops being usable. The session drops follow the signal excursions.",
         "severity": "Warning", "affected_scope": "single_customer",
         "affected_lineids": [lid], "affected_customer_count": 1, "service_impact": True,
         "expected_reasoning": [
             "Sixteen sessions in 24 hours against a 2-3 baseline, with a 71 minute mean duration",
             "Cached RX is -26.28 dBm, already in the degraded band",
             "Telemetry shows RX oscillating between about -24.4 and -28.2 dBm on an eleven hour cycle",
             "The lower excursions cross -28 dBm, at which point the link becomes unusable",
             "Live RX of -27.94 confirms the signal is currently near the bottom of that swing",
             "TX power, bias current, supply voltage and distance are all stable, so the ONU is healthy",
             "RADIUS is clean with a single consistent entry and no mismatches",
             "Peers on EPON0/2 read normal, so the fault is in this customer's own path",
             "The session pattern tracks the signal excursions, so the optical fault explains the flapping"],
         "required_evidence": ["rx_oscillates_across_threshold", "radius_confirmed_clean",
                               "session_pattern_tracks_signal"],
         "expected_remediation": "dispatch_technician",
         "expected_escalation": {"priority": "Warning", "category": "field_service",
                                 "requires_human_review": False, "review_reason": None},
         "distractors": ["The trigger names the session count, pointing at the auth layer",
                         "Sixteen disconnects is well within the observed flapping tail and could be read as a CPE fault"]})


# ================================================================ DS-001
def ds001():
    cap = datetime(2026, 9, 20, 13, 5, tzinfo=timezone.utc)
    K, port, idx = "VE05", 4, 17
    lid, m = onu_mac(), cpe_mac()
    other_lid, other_m = onu_mac(), cpe_mac()
    start, tel = healthy_series(cap, rx_base=-20.9, dist=134)
    prs, idxs, sidx = make_peers(
        K, port, lid, -20.88, n_on_port=29, n_listed=7, subject_idx=idx,
        extra=[{"lineid": other_lid, "interface": f"EPON0/{port}:{idx}",
                "onu_status": 1, "rx_power": "-20.88", "active": 1}])
    prs["duplicate_slot_conflict"] = {
        "interface": f"EPON0/{port}:{idx}",
        "lineids": [lid, other_lid],
        "detail": "Two active CRM records place different ONU MACs on one physical slot. Only one ONU can occupy a slot."}
    return assemble(
        "DS-001", "duplicate_onu_slot", "medium", cap,
        "Two active customers are recorded on one physical ONU slot; the live probe reports a single device and its MAC identifies which record is real.",
        ["Is the CRM view compared against the live probe?",
         "Is the live lineid used to identify the real occupant?",
         "Is the impossibility of the CRM state recognised?"],
        {"type": "scheduled_scan", "input": {"scope": "olt", "target": ESTATE[K]["host"]}},
        subscriber(K, port, idx, lid, m, model_i=0, profile="profile_20M"),
        {"onu_status": 1, "rx_power": "-20.88", "tx_power": "2.37", "reading_age_minutes": 24,
         "olt_health": healthy_olt_health(K, "2026-09-20"),
         "olt_metrics": olt_metrics(K, 26, 19, 44, 64),
         "router_state": router_state(K, cap, 0.3)},
        prs, tel, olt_series(cap, 26, 19, 44),
        {"onu": {"responds": True, "online": 1, "rx_power": -20.91, "tx_power": 2.38,
                 "auth_flag": "Auth", "exchange": "Finish", "rtt_tq": 55},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 5529600,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {sidx: -20.91}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": sessions(cap, 2, 16, 709, 10.9, 3, "10.5.50.145"),
         "radius": radius(m, lid, "10.5.50.145"),
         "traffic": traffic([1000, 1050, 980, 1020, 1010, 1040, 990], cur=217, avg=212, peak=655)},
        {"fault_type": "duplicate_onu_slot",
         "root_cause": f"Two active CRM records place different ONU MACs on EPON0/{port}:{idx}. A slot holds exactly one ONU, so one record is stale. The live probe returns a single device, and its MAC matches the subject record, identifying the other as the leftover.",
         "severity": "Warning", "affected_scope": "multi_customer",
         "affected_lineids": [lid, other_lid], "affected_customer_count": 2,
         "service_impact": False,
         "expected_reasoning": [
             f"The CRM view lists two active customers on EPON0/{port}:{idx} with different ONU MACs",
             "A PON slot holds exactly one ONU, so this state is physically impossible",
             "The live probe of that slot returns a single responding device",
             f"The probe's optical values match the subject record's cached reading of -20.88 dBm",
             "RADIUS holds a consistent entry for the subject with normal sessions and traffic",
             "The second record therefore does not correspond to an installed device and is stale",
             "The optical layer is healthy and neither customer is experiencing a service fault",
             "This is a record defect of the same class as the 644 such interfaces in the estate"],
         "required_evidence": ["two_crm_records_one_slot", "live_probe_returns_one_device",
                               "probe_identifies_real_occupant"],
         "expected_remediation": "manual_review",
         "expected_escalation": {"priority": "Warning", "category": "provisioning",
                                 "requires_human_review": True,
                                 "review_reason": "One of two CRM records on this slot is stale; deleting the wrong one disconnects a live customer"},
         "distractors": ["Nothing is failing and no customer has complained",
                         "Both records are marked active and look equally legitimate in CRM"]})


# ================================================================ DS-002
def ds002():
    cap = datetime(2026, 9, 23, 9, 30, tzinfo=timezone.utc)
    K, port, idx = "JAD04", 8, 41
    lid, m = onu_mac(), cpe_mac()
    l2, l3 = onu_mac(), onu_mac()
    start, tel = healthy_series(cap, rx_base=-23.6, dist=256)
    prs, idxs, sidx = make_peers(
        K, port, lid, -23.58, n_on_port=35, n_listed=7, subject_idx=idx,
        extra=[{"lineid": l2, "interface": f"EPON0/{port}:{idx}", "onu_status": 1,
                "rx_power": "-23.58", "active": 1},
               {"lineid": l3, "interface": f"EPON0/{port}:{idx}", "onu_status": 0,
                "rx_power": "0", "active": 1}])
    prs["duplicate_slot_conflict"] = {
        "interface": f"EPON0/{port}:{idx}",
        "lineids": [lid, l2, l3],
        "detail": "Three active CRM records occupy one slot. None of the three ONU MACs matches the MAC the live probe reports."}
    probe_lid = onu_mac()
    return assemble(
        "DS-002", "duplicate_onu_slot", "hard", cap,
        "Three active records occupy one slot and the ONU actually present matches none of them; the honest answer may be that the evidence does not identify the real occupant.",
        ["Is a conclusion of insufficient evidence reached where it is warranted?",
         "Is the probe MAC compared against all three records rather than assumed to match one?",
         "Is a confident but unsupported attribution avoided?"],
        {"type": "scheduled_scan", "input": {"scope": "olt", "target": ESTATE[K]["host"]}},
        subscriber(K, port, idx, lid, m, model_i=3, profile="profile_40M"),
        {"onu_status": 1, "rx_power": "-23.58", "tx_power": "2.33", "reading_age_minutes": 31,
         "olt_health": healthy_olt_health(K, "2026-09-23"),
         "olt_metrics": olt_metrics(K, 25, 18, 43, 73),
         "router_state": router_state(K, cap, 0.2)},
        prs, tel, olt_series(cap, 25, 18, 43),
        {"onu": {"responds": True, "online": 1, "rx_power": -23.61, "tx_power": 2.34,
                 "auth_flag": "Auth", "exchange": "Finish", "rtt_tq": 83,
                 "reported_lineid": probe_lid},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 6307200,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {sidx: -23.61}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": sessions(cap, 2, 15, 688, 12.4, 3, "10.5.50.199"),
         "radius": radius(m, lid, "10.5.50.199"),
         "traffic": traffic([1010, 990, 1040, 1000, 1020, 980, 1030], cur=209, avg=214, peak=660)},
        {"fault_type": "duplicate_onu_slot",
         "root_cause": f"Three active CRM records occupy EPON0/{port}:{idx}. The live probe returns one ONU whose reported MAC matches none of the three, so the installed device is not represented by any current record. The available evidence does not determine which record, if any, corresponds to the customer being served.",
         "severity": "Warning", "affected_scope": "multi_customer",
         "affected_lineids": [lid, l2, l3], "affected_customer_count": 3,
         "service_impact": False,
         "expected_reasoning": [
             f"The CRM view lists three active customers on EPON0/{port}:{idx}",
             "A slot holds exactly one ONU, so at least two records are wrong",
             "The live probe returns a single responding device with normal optical values",
             "The MAC the probe reports matches none of the three CRM lineids",
             "So the installed ONU is not represented by any of the three records",
             "One record's cached RX matches the probe reading, but that is consistent with stale copying and does not identify the occupant",
             "RADIUS holds an entry for one of the three with active sessions, but it keys on the CPE MAC and not on the ONU",
             "No available signal distinguishes which record belongs to the device present",
             "The honest conclusion is that the occupant cannot be determined from this evidence and a field check is needed"],
         "required_evidence": ["three_crm_records_one_slot", "probe_mac_matches_no_record",
                               "insufficient_evidence_acknowledged"],
         "expected_remediation": "manual_review",
         "expected_escalation": {"priority": "Warning", "category": "provisioning",
                                 "requires_human_review": True,
                                 "review_reason": "Three records on one slot and none matches the installed ONU; a physical check is required before any record is changed"},
         "distractors": ["One record's cached RX matches the probe exactly, inviting a confident attribution",
                         "That record also holds the active RADIUS entry, which reinforces the wrong inference",
                         "A confident answer is available and wrong; the correct answer is that the evidence is insufficient"]})


# ================================================================ SV-001
def sv001():
    cap = datetime(2026, 9, 19, 10, 20, tzinfo=timezone.utc)
    K, port, idx = "OHSC02", 6, 8
    lid, m = onu_mac(), cpe_mac()
    start, tel = healthy_series(cap, rx_base=-18.9, dist=52)
    tel["speed_kbps"] = [0.0] * H
    prs, idxs, sidx = make_peers(K, port, lid, -18.92, n_on_port=18, n_listed=7, subject_idx=idx)
    return assemble(
        "SV-001", "stuck_provisioning_vlan46", "medium", cap,
        "A newly installed CPE is still on the factory-default management VLAN; it is present on the fibre and absent from the network.",
        ["Is the VLAN walk consulted when the physical layer is healthy?",
         "Is the factory VLAN recognised as unprovisioned rather than misconfigured?",
         "Is this separated from a missing RADIUS entry?"],
        {"type": "customer_complaint",
         "input": {"lineid": lid, "complaint": "Installed two days ago, still no connection"}},
        subscriber(K, port, idx, lid, m, model_i=6, profile="profile_100M"),
        {"onu_status": 1, "rx_power": "-18.92", "tx_power": "2.50", "reading_age_minutes": 16,
         "olt_health": healthy_olt_health(K, "2026-09-19"),
         "olt_metrics": olt_metrics(K, 24, 17, 41, 31),
         "router_state": router_state(K, cap, 0.3)},
        prs, tel, olt_series(cap, 24, 17, 41),
        {"onu": {"responds": True, "online": 1, "rx_power": -18.95, "tx_power": 2.51,
                 "auth_flag": "Auth", "exchange": "Finish", "rtt_tq": 51},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 2678400,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {sidx: -18.95}),
         "vlan_walk": vlan_walk(K, port, actual=46)},
        {"sessions": {"count_24h": 0, "count_7d": 0, "avg_duration_minutes": 0,
                      "last_disconnect": None, "recent": []},
         "radius": radius(m, lid, None, exists=True, consistent=True),
         "traffic": traffic([0, 0, 0, 0, 0, 0, 0], up=[0] * 7, cur=158, avg=161, peak=470)},
        {"fault_type": "stuck_provisioning_vlan46",
         "root_cause": "The CPE is still on VLAN 46, the factory-default management VLAN it ships with. The TR-069 provisioning step that migrates it to VLAN 1999 and its data VLAN never completed, so the device is registered on the fibre but has no path onto the network.",
         "severity": "Average", "affected_scope": "single_customer",
         "affected_lineids": [lid], "affected_customer_count": 1, "service_impact": True,
         "expected_reasoning": [
             "The ONU is online with RX -18.92 and TX 2.50, both excellent",
             "The live probe confirms the ONU and its peers are responding normally",
             "The OLT and router are healthy, so the physical layer works end to end",
             "Despite that, the customer has zero sessions and zero traffic since installation",
             "A radcheck row does exist for this CPE MAC, so this is not a missing RADIUS entry",
             "The VLAN walk shows the customer on VLAN 46 where VLAN 1116 is expected",
             "VLAN 46 is the factory-default management VLAN a CPE ships with",
             "Provisioning should have migrated it to 1999 and the port's data VLAN, and did not",
             "The device is present on the fibre and has no path onto the network"],
         "required_evidence": ["vlan_walk_shows_46", "radcheck_exists_so_not_missing_entry",
                               "physical_layer_confirmed_healthy"],
         "expected_remediation": "trigger_acs_provisioning",
         "expected_escalation": {"priority": "Average", "category": "provisioning",
                                 "requires_human_review": False, "review_reason": None},
         "distractors": ["Zero sessions with a healthy physical layer is also the RADIUS missing-entry signature",
                         "Excellent optical readings invite a no_fault conclusion on the network side",
                         "The VLAN walk is not an obvious first move"]})


# ================================================================ SV-002
def sv002():
    cap = datetime(2026, 9, 21, 15, 45, tzinfo=timezone.utc)
    K, port, idx = "GRAD01", 8, 37
    lid, m = onu_mac(), cpe_mac()
    start, tel = healthy_series(cap, rx_base=-21.7, dist=193)
    tel["speed_kbps"] = [0.0] * H
    prs, idxs, sidx = make_peers(K, port, lid, -21.73, n_on_port=33, n_listed=8, subject_idx=idx)
    return assemble(
        "SV-002", "stuck_provisioning_vlan46", "hard", cap,
        "Healthy fibre, no service, and a RADIUS entry that looks wrong; the VLAN walk is what separates a provisioning failure from an authentication one.",
        ["Is the VLAN walk reached before the RADIUS anomaly is accepted as the cause?",
         "Is a coincident RADIUS defect correctly judged not to explain the symptoms?",
         "Is the nearest look-alike, a missing RADIUS entry, ruled out on evidence?"],
        {"type": "customer_complaint",
         "input": {"lineid": lid, "complaint": "Reconnected after moving house, nothing works"}},
        subscriber(K, port, idx, lid, m, model_i=1, profile="profile_40M"),
        {"onu_status": 1, "rx_power": "-21.73", "tx_power": "2.41", "reading_age_minutes": 11,
         "olt_health": healthy_olt_health(K, "2026-09-21"),
         "olt_metrics": olt_metrics(K, 25, 18, 43, 49),
         "router_state": router_state(K, cap, 0.2)},
        prs, tel, olt_series(cap, 25, 18, 43),
        {"onu": {"responds": True, "online": 1, "rx_power": -21.76, "tx_power": 2.42,
                 "auth_flag": "Auth", "exchange": "Finish", "rtt_tq": 66},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 4233600,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {sidx: -21.76}),
         "vlan_walk": vlan_walk(K, port, actual=46)},
        {"sessions": {"count_24h": 0, "count_7d": 0, "avg_duration_minutes": 0,
                      "last_disconnect": None, "recent": []},
         "radius": {"radcheck_exists": True, "username": m, "lineid_in_radius": lid,
                    "framed_pool": None, "assigned_ip": None, "crm_consistent": False,
                    "mismatches": [
                        {"type": "orphan_radcheck",
                         "detail": "A radcheck row from the customer's previous address remains under a superseded CPE MAC. It is inert and is not consulted for the current username."}]},
         "traffic": traffic([0, 0, 0, 0, 0, 0, 0], up=[0] * 7, cur=203, avg=198, peak=610)},
        {"fault_type": "stuck_provisioning_vlan46",
         "root_cause": "The relocated CPE is still on the factory-default VLAN 46 and was never migrated to VLAN 1999 and its data VLAN, so it cannot reach the network. The orphan RADIUS row left behind at the previous address is inert and is not the cause.",
         "severity": "Average", "affected_scope": "single_customer",
         "affected_lineids": [lid], "affected_customer_count": 1, "service_impact": True,
         "expected_reasoning": [
             "The ONU is online with RX -21.73 and TX 2.41, and the live probe confirms it",
             "Peers, OLT and router are all healthy, so the physical layer works",
             "The customer has zero sessions and zero traffic since reconnection",
             "RADIUS does hold a current radcheck row for this CPE MAC, so the missing-entry explanation is ruled out",
             "There is a RADIUS anomaly, an orphan row under a superseded MAC from the previous address",
             "That row is inert: it is not consulted for the current username and cannot prevent authentication",
             "Accepting it as the cause would stop the investigation one step short",
             "The VLAN walk shows the customer on VLAN 46 where VLAN 1058 is expected",
             "VLAN 46 is the factory default, so provisioning never migrated this CPE after the move",
             "A device on the factory VLAN has no network path regardless of its RADIUS state"],
         "required_evidence": ["vlan_walk_shows_46", "radcheck_exists_so_not_missing_entry",
                               "orphan_row_ruled_out_as_cause"],
         "expected_remediation": "trigger_acs_provisioning",
         "expected_escalation": {"priority": "Average", "category": "provisioning",
                                 "requires_human_review": True,
                                 "review_reason": "An orphan RADIUS row from the previous address should be cleaned up separately"},
         "distractors": ["The RADIUS orphan is a plausible cause and is found before the VLAN walk",
                         "The symptom profile is identical to a missing RADIUS entry",
                         "A house move suggests an account or provisioning record problem rather than a VLAN one"]})


# ================================================================ CD-001
def cd001():
    cap = datetime(2026, 9, 17, 18, 5, tzinfo=timezone.utc)
    K, port, idx = "KV03", 7, 21
    lid, m = onu_mac(), cpe_mac()
    start, tel = healthy_series(cap, rx_base=-20.4, dist=118)
    prs, idxs, sidx = make_peers(K, port, lid, -20.37, n_on_port=24, n_listed=7, subject_idx=idx)
    return assemble(
        "CD-001", "catv_drift", "easy", cap,
        "A customer subscribed to CATV whose device state was never synchronised; data service is entirely unaffected.",
        ["Is a single-service state mismatch identified?",
         "Is partial service impact reported without escalating severity?",
         "Is the data path correctly judged unaffected?"],
        {"type": "customer_complaint",
         "input": {"lineid": lid, "complaint": "Internet is fine but the TV channels never came on"}},
        subscriber(K, port, idx, lid, m, model_i=0, profile="profile_CATV",
                   catv_service=1, catv_synced=0),
        {"onu_status": 1, "rx_power": "-20.37", "tx_power": "2.44", "reading_age_minutes": 19,
         "olt_health": healthy_olt_health(K, "2026-09-17"),
         "olt_metrics": olt_metrics(K, 23, 17, 41, 53),
         "router_state": router_state(K, cap, 0.4)},
        prs, tel, olt_series(cap, 23, 17, 41),
        {"onu": {"responds": True, "online": 1, "rx_power": -20.40, "tx_power": 2.45,
                 "auth_flag": "Auth", "exchange": "Finish", "rtt_tq": 56},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 4579200,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {sidx: -20.40}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": sessions(cap, 2, 15, 697, 12.9, 3, "10.5.50.108"),
         "radius": radius(m, lid, "10.5.50.108"),
         "traffic": traffic([1040, 1000, 1070, 1010, 1050, 990, 1030], cur=181, avg=185, peak=550)},
        {"fault_type": "catv_drift",
         "root_cause": "The customer is recorded as subscribed to CATV but catv_synced is 0, so the CATV state was never pushed to the ONU. Data service is unaffected; only the television service is missing.",
         "severity": "Information", "affected_scope": "single_customer",
         "affected_lineids": [lid], "affected_customer_count": 1, "service_impact": True,
         "expected_reasoning": [
             "The customer reports working internet and missing television",
             "catv_service is 1 and catv_synced is 0, so the subscription exists and the device state does not match it",
             "The ONU model supports CATV, so this is not an equipment limitation",
             "Optical readings are normal and the live probe confirms the ONU is healthy",
             "Sessions and daily traffic are normal, consistent with working data service",
             "The OLT and router are healthy and no shared fault exists",
             "This is a service state mismatch on one dimension, of the same class as the 84 unsynced lines in the estate",
             "It is resolved by re-pushing the CATV state rather than by any field work"],
         "required_evidence": ["catv_service_set_but_unsynced", "data_service_unaffected",
                               "onu_model_supports_catv"],
         "expected_remediation": "resync_catv",
         "expected_escalation": {"priority": "Information", "category": "provisioning",
                                 "requires_human_review": False, "review_reason": None},
         "distractors": ["Every network signal is healthy, inviting a no_fault conclusion",
                         "The complaint could be read as customer equipment rather than provisioning"]})


# ================================================================ CG-001
def cg001():
    cap = datetime(2026, 9, 22, 20, 40, tzinfo=timezone.utc)
    K, port, idx = "ANC08", 7, 24
    lid, m = onu_mac(), cpe_mac()
    start, tel = healthy_series(cap, rx_base=-21.2, dist=167)
    tel["speed_kbps"] = [r2(max(0.05, _rng.gauss(2.1, 0.9))) if (i % 24) in range(18, 24)
                         else r2(max(0.05, _rng.gauss(6.8, 2.4))) for i in range(H)]
    prs, idxs, sidx = make_peers(K, port, lid, -21.24, n_on_port=47, n_listed=8, subject_idx=idx)
    return assemble(
        "CG-001", "pon_congestion", "medium", cap,
        "Several customers on one heavily loaded PON port report evening slowness; every optical signal is normal and traffic is rising rather than falling.",
        ["Is the direction of the traffic anomaly used as the discriminator?",
         "Is multi-customer slowness separated from a shared optical fault?",
         "Is the port's occupancy recognised as a contributing factor?"],
        {"type": "customer_complaint",
         "input": {"lineid": lid, "complaint": "Every evening it crawls, fine during the day"}},
        subscriber(K, port, idx, lid, m, model_i=1, profile="profile_300M"),
        {"onu_status": 1, "rx_power": "-21.24", "tx_power": "2.36", "reading_age_minutes": 13,
         "olt_health": healthy_olt_health(K, "2026-09-22"),
         "olt_metrics": olt_metrics(K, 38, 24, 51, 89),
         "router_state": router_state(K, cap, 0.2)},
        prs, tel, olt_series(cap, 38, 24, 51),
        {"onu": {"responds": True, "online": 1, "rx_power": -21.27, "tx_power": 2.37,
                 "auth_flag": "Auth", "exchange": "Finish", "rtt_tq": 62},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 7689600,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {sidx: -21.27}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": sessions(cap, 2, 16, 711, 14.2, 3, "10.5.50.163"),
         "radius": radius(m, lid, "10.5.50.163"),
         "traffic": traffic([2840, 3010, 2760, 3180, 2950, 3320, 3090],
                            cur=912, avg=488, peak=948)},
        {"fault_type": "pon_congestion",
         "root_cause": "EPON0/7 carries 47 customers and its evening load is reaching 912 Mbps against a 488 Mbps average, close to the port's shared capacity ceiling. Throughput degrades for everyone on the port during peak hours. No optical or authentication fault exists.",
         "severity": "Warning", "affected_scope": "pon_port",
         "affected_lineids": [], "affected_customer_count": 47, "service_impact": True,
         "expected_reasoning": [
             "The complaint is time-of-day specific, which points at load rather than at a physical fault",
             "RX is flat at -21.2 dBm inside the noise floor, and TX, bias, voltage and distance are all stable",
             "The live probe shows every ONU on the port online with normal optical readings",
             "RADIUS is clean and sessions are long and stable, so authentication is not involved",
             "PON port traffic is at 912 Mbps against a 488 Mbps average",
             "Daily traffic for this customer is roughly three times the network mean and rising, not falling",
             "Every fault-driven degradation reduces traffic; congestion raises it, so the direction is the discriminator",
             "The customer's own throughput series drops sharply during the same evening hours each day",
             "The port carries 47 customers, at the top of the observed occupancy distribution",
             "This is capacity exhaustion on a shared port, not a fault on any one line"],
         "required_evidence": ["optical_layer_confirmed_clean", "traffic_elevated_not_depressed",
                               "degradation_is_time_of_day"],
         "expected_remediation": "capacity_planning",
         "expected_escalation": {"priority": "Warning", "category": "infrastructure",
                                 "requires_human_review": True,
                                 "review_reason": "EPON0/7 needs a capacity review; 47 customers on one port with evening load near ceiling"},
         "distractors": ["Multi-customer slowness resembles a splitter or feeder degradation",
                         "Elevated OLT CPU and temperature could be read as device stress causing the slowness",
                         "Reduced throughput in the speed series looks like a link problem"]})


# ================================================================ NF-001
def nf001():
    cap = datetime(2026, 9, 16, 9, 0, tzinfo=timezone.utc)
    K, port, idx = "SR01", 2, 9
    lid, m = onu_mac(), cpe_mac()
    start, tel = healthy_series(cap, rx_base=-24.6, dist=289)
    prs, idxs, sidx = make_peers(K, port, lid, -24.58, n_on_port=21, n_listed=7, subject_idx=idx)
    return assemble(
        "NF-001", "no_fault", "easy", cap,
        "A scheduled sweep surfaces several values that look mildly unusual; every one of them is inside its calibrated normal band.",
        ["Are calibrated thresholds applied rather than assumed ones?",
         "Is the 2-3 session baseline recognised as normal re-authentication?",
         "Can the pipeline conclude that nothing is wrong and stop?"],
        {"type": "scheduled_scan", "input": {"scope": "olt", "target": ESTATE[K]["host"]}},
        subscriber(K, port, idx, lid, m, model_i=0, profile="profile_20M"),
        {"onu_status": 1, "rx_power": "-24.58", "tx_power": "2.62", "reading_age_minutes": 29,
         "olt_health": healthy_olt_health(K, "2026-09-16"),
         "olt_metrics": olt_metrics(K, 22, 17, 40, 90),
         "router_state": router_state(K, cap, 1.6)},
        prs, tel, olt_series(cap, 22, 17, 40),
        {"onu": {"responds": True, "online": 1, "rx_power": -24.61, "tx_power": 2.63,
                 "auth_flag": "Auth", "exchange": "Finish", "rtt_tq": 92},
         "olt": {"ping_ok": True, "snmp_responds": True, "sys_uptime_seconds": 7776000,
                 "oid_subtree_responds": True},
         "pon_probe": pon_probe(port, idxs, {sidx: -24.61}),
         "vlan_walk": vlan_walk(K, port)},
        {"sessions": sessions(cap, 3, 19, 668, 8.1, 3, "10.5.50.84"),
         "radius": radius(m, lid, "10.5.50.84"),
         "traffic": traffic([960, 1010, 930, 990, 1040, 950, 1000], cur=149, avg=154, peak=455)},
        {"fault_type": "no_fault",
         "root_cause": "No fault is present. RX sits in the lower part of the normal band, TX is inside the measured healthy range, the session count is at the network baseline, and the OLT's offline count matches the background rate.",
         "severity": "Not classified", "affected_scope": "none",
         "affected_lineids": [], "affected_customer_count": 0, "service_impact": False,
         "expected_reasoning": [
             "RX is -24.58 dBm, which is in the lower part of the normal -20 to -25 band and above the -25 degraded threshold",
             "The RX series has been flat for seven days inside the noise floor, so there is no downward trend",
             "TX is 2.62 dBm, inside the measured healthy range of 0 to +5 for this estate",
             "The documented -6 to -10 band would flag this value, but that threshold is wrong and would flag most of the network",
             "Three sessions in 24 hours is the baseline that 80.8% of customers show, not flapping",
             "Session duration of 668 minutes is close to the 11.9 hour network mean",
             "Router heartbeat at 1.6 hours is inside the 2 hour ok threshold",
             "The OLT's offline count is consistent with the 4.85% background rate",
             "Traffic is steady across all seven days with no trend",
             "Every value that looks mildly unusual is inside its calibrated normal band"],
         "required_evidence": ["rx_within_normal_band", "tx_judged_against_correct_band",
                               "session_count_is_baseline"],
         "expected_remediation": "no_action",
         "expected_escalation": {"priority": "Not classified", "category": "monitoring",
                                 "requires_human_review": False, "review_reason": None},
         "distractors": ["RX near -25 looks close to the degraded threshold",
                         "TX at 2.62 would be flagged by the incorrect documented threshold",
                         "Router heartbeat at 1.6 hours looks stale without the threshold",
                         "A scheduled scan implies something is expected to be found"]})


BUILDERS = [fc002, fc003, fc004, ru001, ru002, ra001, ra002, ra003, ra004,
            sf001, ds001, ds002, sv001, sv002, cd001, cg001, nf001]
