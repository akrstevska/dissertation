#!/usr/bin/env python3
"""Apply the network engineer's review (October 2026) to six scenarios in place.

Patched here rather than regenerated: batch1/batch2 share one seeded RNG, so editing a
builder would shift the random data of every scenario built after it.
See docs/scenario-changelog.md for what changed and why.
"""
import json, random
from datetime import datetime, timedelta, timezone
from pathlib import Path

DIR = Path(__file__).parent.parent
H = 168
rng = random.Random(20261005)


def load(name):
    return json.loads((DIR / f"{name}.json").read_text())


def save(name, s):
    (DIR / f"{name}.json").write_text(json.dumps(s, indent=2) + "\n")


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def at(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def speed():
    return round(max(0.05, rng.gauss(5.6, 2.3)), 2)


def upload(down):
    return [d * 6 + rng.randint(-200, 200) if d else 0 for d in down]


def traffic(t, down):
    up = upload(down)
    t.update({"download_mb_daily": down, "upload_mb_daily": up,
              "monthly_avg_download_mb": sum(down) // len(down),
              "monthly_avg_upload_mb": sum(up) // len(up)})


def ended_sessions(end, n, mean_s, ip):
    """n completed sessions, newest first, the newest ending at `end`."""
    rec = []
    for _ in range(n):
        dur = int(mean_s * rng.uniform(0.85, 1.15))
        rec.append({"start": iso(end - timedelta(seconds=dur)), "end": iso(end),
                    "duration_s": dur, "ip": ip})
        end = end - timedelta(seconds=dur + rng.randint(60, 900))
    return rec


def zero_from(series, i):
    """The poller writes 0 for every value it cannot read."""
    return series[:i] + [0] * (len(series) - i)


ONU_SIGNALS = ("rx_power", "tx_power", "temperature", "distance",
               "tx_bias_current", "supply_voltage", "speed_kbps")


# ------------------------------------------------------------------ OF-001
def of001():
    s = load("OF-001-easy")
    tel = s["telemetry"]
    for k in ONU_SIGNALS:
        tel["onu_series"][k] = zero_from([0 if v is None else v for v in tel["onu_series"][k]], 166)
    os_ = tel["olt_series"]   # was ~0 for all seven days; the OLT only died two hours ago
    os_["cpu_load"] = [int(max(0, min(48, rng.gauss(24, 3)))) for _ in range(166)] + [0, 0]
    os_["memory_usage"] = [int(max(0, min(76, rng.gauss(18, 1.5)))) for _ in range(166)] + [0, 0]
    os_["temperature"] = [int(max(0, min(68, rng.gauss(42, 2)))) for _ in range(166)] + [0, 0]
    s["network_state"]["reading_age_minutes"] = 3

    gt = s["ground_truth"]
    zeros = ("Stored readings and every telemetry signal dropped to 0 two hours ago, including distance and "
             "supply voltage, which cannot physically be 0: that is the poller's default when it cannot read, "
             "not a measurement")
    gt["expected_reasoning"] = [zeros if r.startswith("Optical readings are stale") else r
                                for r in gt["expected_reasoning"]]
    gt["distractors"] = [
        "Zero values in olt_metrics could be read as healthy low utilisation",
        "Zeroed stored readings and telemetry look like measurements but are the poller's no-read default"]
    save("OF-001-easy", s)


# ------------------------------------------------------------------ OF-002
def of002():
    s = load("OF-002-medium")
    ns, peers, tel = s["network_state"], s["peers"], s["telemetry"]
    ns.update({"onu_status": 0, "rx_power": "0", "tx_power": "0", "reading_age_minutes": 4})
    peers["crm_view"]["customers"] = [{**c, "onu_status": 0, "rx_power": "0"}
                                      for c in peers["crm_view"]["customers"]]
    pop = peers["olt_population"]
    pop["onu_online_count"], pop["onu_offline_count"] = 0, pop["total_customers"]
    for k in ONU_SIGNALS:
        tel["onu_series"][k] = zero_from([0 if v is None else v for v in tel["onu_series"][k]], 120)
    for k in ("cpu_load", "memory_usage", "temperature"):
        tel["olt_series"][k] = zero_from(tel["olt_series"][k], 120)
    tel["availability"] = {"onu_series_complete": True, "gaps": []}

    s["metadata"]["tests"] = [
        "Is loss of monitoring separated from loss of service?",
        "Is a stored all-offline picture recognised as the poller's no-read default?",
        "Is the customer-facing conclusion drawn from customer-facing evidence?"]
    gt = s["ground_truth"]
    gt["expected_reasoning"] = [
        "The health check reports critical, but its two SNMP flags come from a single sysUpTime read and are always equal, so the wording distinguishes nothing",
        "Ping succeeds, so the device is powered and reachable on the management network",
        "No SNMP query answers, so no ONU can be probed and no device metrics can be collected",
        "Stored data shows every ONU on the OLT offline with RX and TX of 0, but that is what the poller writes when it cannot read the OLT, not a measured state",
        "Telemetry for both the ONU and the OLT drops to 0 on every signal at the same hour 48 hours ago, including distance and supply voltage, which cannot physically be 0",
        "Customer-facing evidence is intact: sessions are active with normal durations and daily traffic is unchanged across all seven days",
        "Service therefore continues normally; what has been lost is visibility, not connectivity",
        "The correct conclusion is a monitoring-path failure on a serving OLT, not a customer outage"]
    gt["required_evidence"] = ["ping_succeeds_snmp_fails", "customers_passing_traffic",
                               "stored_zeros_are_no_reading"]
    gt["distractors"] = [
        "Stored data shows every ONU on the OLT offline, which is the picture of a dead OLT",
        "A critical alarm on a whole OLT invites a Disaster severity",
        "Zeroed olt_metrics could be read as a failing device",
        "Every probe returns no response, which resembles the firmware mismatch signature"]
    save("OF-002-medium", s)


# ------------------------------------------------------------------ RA-003
def ra003():
    s = load("RA-003-medium")
    cap = at(s["metadata"]["captured_at"])
    swap = datetime(2026, 9, 16, 14, 10, tzinfo=timezone.utc)
    lid = s["subscriber"]["lineid"]
    sa = s["session_auth"]
    old = sa["radius"]["lineid_in_radius"]

    s["trigger"]["input"]["complaint"] = "No internet since the technician replaced my ONU yesterday"
    sa["sessions"] = {"count_24h": 1, "count_7d": 13, "avg_duration_minutes": 702,
                      "last_disconnect": iso(swap),
                      "recent": ended_sessions(swap, 3, 702 * 60, "10.5.50.132")}
    sa["radius"]["assigned_ip"] = None
    sa["radius"]["mismatches"] = [
        {"type": "lineid_conflict",
         "detail": f"radcheck.lineid is {old} while crm_user_net.lineid is {lid} for the same username. The ONU was replaced on 2026-09-16 and CRM was updated; RADIUS was not."},
        {"type": "orphan_radcheck",
         "detail": f"The superseded ONU MAC {old} no longer corresponds to any installed device."}]
    traffic(sa["traffic"], [1030, 1070, 1000, 1050, 1010, 620, 0])
    hours_down = int((cap - swap).total_seconds() // 3600) + 1
    sp = s["telemetry"]["onu_series"]["speed_kbps"]
    s["telemetry"]["onu_series"]["speed_kbps"] = sp[:H - hours_down] + [0.0] * hours_down

    s["metadata"]["description"] = ("After an ONU swap the CRM lineid was updated and the RADIUS lineid was not; "
                                    "Line ID is checked at authentication, so the customer has been rejected since the swap.")
    s["metadata"]["tests"] = [
        "Is the cross-system key mismatch found?",
        "Is it separated from a missing RADIUS entry and from a CRM-internal duplicate?",
        "Is the physical layer ruled out despite a complaint that points at the new hardware?"]
    gt = s["ground_truth"]
    gt.update({
        "root_cause": "The ONU was replaced on 16 September. CRM was updated with the new ONU MAC but radcheck.lineid still carries the superseded one. Line ID is checked at authentication, so from the DHCP exchange that followed the swap every attempt has been rejected and the customer has had no service.",
        "severity": "Average", "service_impact": True,
        "expected_reasoning": [
            "The customer has had no service since the ONU was replaced yesterday",
            "The optical layer is healthy: RX -20.1, TX 2.4, distance constant at 145 m, and the live probe confirms the ONU online",
            "Peers on the port are normal and the OLT and router are healthy, so no shared infrastructure fault exists",
            "The last session ended at 14:10 on 16 September and none has been established since; throughput has been zero since then",
            "A radcheck row exists for the CPE MAC, so this is not a missing entry",
            "crm_user_net.lineid and radcheck.lineid hold different ONU MACs for the same username",
            "The CRM value is the installed ONU; the RADIUS value is the one that was removed",
            "Line ID is an authentication parameter, so a RADIUS lineid that does not match the installed ONU rejects every attempt",
            "This is a cross-system key mismatch, distinct from two CRM records colliding on one interface",
            "The installed device should be confirmed before the RADIUS record is rewritten"],
        "required_evidence": ["crm_and_radius_lineids_differ", "no_session_since_swap",
                              "physical_layer_healthy"],
        "expected_remediation": "manual_review",
        "expected_escalation": {"priority": "Average", "category": "provisioning",
                                "requires_human_review": True,
                                "review_reason": "The RADIUS lineid must be rewritten to the installed ONU; the installed device should be confirmed before the record is changed"},
        "distractors": ["The complaint ties the outage to a hardware visit, inviting an ONU or fibre fault",
                        "A radcheck row exists, so a check that stops at its existence finds nothing wrong",
                        "The mismatch resembles a duplicate slot conflict but is cross-system"]})
    save("RA-003-medium", s)


# ------------------------------------------------------------------ RA-004
def ra004():
    s = load("RA-004-hard")
    cap = at(s["metadata"]["captured_at"])
    drop = datetime(2026, 9, 22, 11, 52, tzinfo=timezone.utc)
    sa = s["session_auth"]

    s["trigger"]["input"]["complaint"] = "Internet stopped around midday and hasn't come back, restarting the router didn't help"
    sa["sessions"] = {"count_24h": 2, "count_7d": 15, "avg_duration_minutes": 698,
                      "last_disconnect": iso(drop),
                      "recent": ended_sessions(drop, 3, 698 * 60, "10.5.50.212")}
    sa["radius"]["assigned_ip"] = None
    sa["radius"]["mismatches"] = [
        {"type": "replication_lag",
         "detail": "The primary FreeRADIUS holds a current radcheck row for this username. The secondary holds the row as it was before a password change made during a profile upgrade on 2026-09-20, which has not replicated."},
        {"type": "replication_lag",
         "detail": "The primary FreeRADIUS has not answered the MikroTik since 2026-09-22 09:40 and requests are being sent to the secondary. Every authentication attempt for this username since 11:52 has been rejected by the secondary."}]
    traffic(sa["traffic"], [980, 1010, 950, 1030, 990, 1000, 520])
    hours_down = int((cap - drop).total_seconds() // 3600) + 1
    sp = [speed() if v == 0.0 else v for v in s["telemetry"]["onu_series"]["speed_kbps"]]
    s["telemetry"]["onu_series"]["speed_kbps"] = sp[:H - hours_down] + [0.0] * hours_down

    s["metadata"]["description"] = ("A customer is rejected after the MikroTik fails over to a secondary RADIUS server that never "
                                    "received their password change; the primary holds the correct row, so no single-server check reveals it.")
    s["metadata"]["tests"] = [
        "Is inconsistency across the two RADIUS servers identified as the cause?",
        "Is it separated from a missing entry and from a lineid conflict?",
        "Is the optical layer conclusively ruled out first?"]
    gt = s["ground_truth"]
    gt.update({
        "root_cause": "A password change made during a profile upgrade on 20 September reached the primary FreeRADIUS but not the secondary. The primary stopped answering at 09:40 and the MikroTik failed over to the secondary. When the customer's session ended at 11:52 the secondary rejected the stale credentials, and every attempt since has failed. A clean authentication failure, not flapping.",
        "expected_reasoning": [
            "The customer has had no session since 11:52 and throughput has been zero since then",
            "Before that the session history was normal, two sessions in 24 hours with durations near the 11.9 hour mean, so there was no flapping",
            "RX has been flat at -21.0 dBm for seven days inside the noise floor, and TX, bias, voltage and distance are all stable",
            "The live probe confirms the ONU online and healthy, and peers on the port are normal",
            "The OLT and router are healthy, so no shared infrastructure fault exists",
            "A radcheck row exists and its lineid matches CRM, so this is neither a missing entry nor a lineid conflict",
            "The primary row is current, so a check of the primary alone finds nothing wrong",
            "Comparing both servers shows the secondary holds the row from before the 20 September password change",
            "The MikroTik has been sending requests to the secondary since 09:40, and the outage began at the first re-authentication after that",
            "An unsynchronised secondary answering after failover explains a clean authentication failure on a healthy line"],
        "required_evidence": ["optical_layer_confirmed_clean", "both_radius_servers_compared",
                              "outage_began_after_failover"],
        "expected_escalation": {"priority": "Average", "category": "infrastructure",
                                "requires_human_review": True,
                                "review_reason": "The primary FreeRADIUS is not answering and the secondary is out of sync; every customer changed since 20 September will be rejected at their next re-authentication"},
        "distractors": ["Restarting the router did not help, which invites an ONU or CPE fault",
                        "The primary RADIUS record is entirely correct, so a single-server check finds nothing",
                        "A healthy line with no service resembles a missing RADIUS entry"]})
    save("RA-004-hard", s)


# ------------------------------------------------------------------ RU-001
def ru001():
    s = load("RU-001-easy")
    er = s["ground_truth"]["expected_reasoning"]
    line = ("OLT management is reachable, so it does not run through this BNG; where OLT management "
            "shares the BNG, the OLTs behind it would be unreachable as well")
    if line not in er:
        er.insert(er.index("OLT ping, SNMP and device metrics are all healthy") + 1, line)
    save("RU-001-easy", s)


# ------------------------------------------------------------------ SF-002
def sf002():
    s = load("SF-002-hard")
    cap = at(s["metadata"]["captured_at"])
    lid = s["subscriber"]["lineid"]
    sa = s["session_auth"]
    timeout = 4500

    start = cap - timedelta(seconds=1140)
    rec = [{"start": iso(start), "end": None, "duration_s": 1140, "ip": "10.5.50.204"}]
    for _ in range(4):
        end = start - timedelta(seconds=rng.randint(40, 75))
        start = end - timedelta(seconds=timeout)
        rec.append({"start": iso(start), "end": iso(end), "duration_s": timeout, "ip": "10.5.50.204"})
    sa["sessions"] = {"count_24h": 19, "count_7d": 84, "avg_duration_minutes": 75,
                      "last_disconnect": rec[1]["end"], "recent": rec}
    sa["radius"].update({"lineid_in_radius": lid, "assigned_ip": "10.5.50.204", "crm_consistent": True,
                         "mismatches": [{"type": "radreply_attribute",
                                         "detail": "radreply holds Session-Timeout := 4500 for this username, written on 2026-09-17 when the customer's profile was changed. Other customers on profile_40M carry no Session-Timeout."}]})
    traffic(sa["traffic"], [960, 1010, 930, 990, 940, 970, 390])
    s["telemetry"]["onu_series"]["speed_kbps"] = [speed() if v == 0.0 else v
                                                  for v in s["telemetry"]["onu_series"]["speed_kbps"]]

    s["metadata"]["description"] = ("Heavy session flapping on a clean optical layer; a per-user Session-Timeout in "
                                    "radreply ends every session after 75 minutes.")
    s["metadata"]["tests"] = [
        "Is a second data layer searched once the optical layer comes back clean?",
        "Are uniform session durations recognised as a timer rather than line loss?",
        "Is the RADIUS attribute found and tied to the session length?"]
    gt = s["ground_truth"]
    gt.update({
        "root_cause": "On 17 September a Session-Timeout of 4500 seconds was written to radreply for this username when the profile was changed. The MikroTik ends the session each time the timer expires and the CPE re-authenticates within about a minute, so the customer is disconnected every 75 minutes on a physically healthy line.",
        "affected_lineids": [lid],
        "expected_reasoning": [
            "19 sessions in 24h against a 2-3 baseline, with a 75 minute mean against an 11.9 hour norm",
            "RX has been flat at -20.6 dBm for seven days inside the +/-0.3 dBm noise floor, so signal is not the cause",
            "TX power, bias current, supply voltage and distance are all stable",
            "Port neighbours are normal and the OLT is healthy, so no shared infrastructure fault",
            "With no optical explanation available, the search moves to the authentication layer",
            "Every completed recent session lasted exactly 4500 seconds, and each reconnect followed within about a minute",
            "Durations that identical point to a timer, not to random line loss",
            "radreply holds Session-Timeout 4500 for this username, set on 17 September, which matches the session length exactly",
            "Every reconnect succeeds, so authentication works; the defect is the attribute that ends each session",
            "Daily traffic is steady because each reconnect costs about a minute; the harm is the interruption, not lost volume"],
        "required_evidence": ["optical_layer_confirmed_clean", "uniform_session_durations",
                              "session_timeout_in_radreply"],
        "expected_remediation": "manual_review",
        "expected_escalation": {"priority": "Average", "category": "provisioning",
                                "requires_human_review": True,
                                "review_reason": "The per-user Session-Timeout has to be removed by hand, and the profile change that wrote it should be checked for other customers"},
        "distractors": ["The session pattern is identical to signal-related flapping and invites that diagnosis",
                        "Every reconnect succeeds, so a check that only asks whether authentication works finds nothing wrong",
                        "ONU is a Router type, inviting a CPE-fault explanation"]})
    save("SF-002-hard", s)


if __name__ == "__main__":
    for fn in (of001, of002, ra003, ra004, ru001, sf002):
        fn()
        print("patched", fn.__name__)
