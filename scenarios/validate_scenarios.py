#!/usr/bin/env python3
"""Validate scenario JSON files against docs/scenario-schema.md §14."""
import json, re, sys, glob, os

MAC = re.compile(r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$")
IFACE = re.compile(r"^EPON0/[1-8]:\d{1,3}$")
SECTIONS = ["metadata", "trigger", "subscriber", "network_state",
            "peers", "telemetry", "snmp_live", "session_auth", "ground_truth"]

MODEL_CAPS = {
    "Aztech 1G + CATV": ("Bridge", 1, 0),
    "JM 1G + CATV + WiFi + POTs": ("Router", 1, 1),
    "Aztech 1G": ("Bridge", 0, 0),
    "Aztech 2GE + WiFi(dual band) + POTs + CATV": ("Router", 1, 1),
    "Infel 1G + CATV": ("Bridge", 1, 0),
    "JM 1G + CATV": ("Bridge", 1, 0),
    "Raisecom 1G": ("Bridge", 0, 0),
    "JM 1G": ("Bridge", 0, 0),
    "Aztech 1G + CATV-xPON": ("Bridge", 1, 0),
    "Aztech 1G + CATV + WiFi + POTs": ("Router", 1, 1),
}


def check(path):
    errs, warns = [], []
    s = json.load(open(path))
    E, W = errs.append, warns.append

    # structural
    for sec in SECTIONS:
        if sec not in s:
            E(f"missing section: {sec}")
    if errs:
        return errs, warns

    m, sub, ns = s["metadata"], s["subscriber"], s["network_state"]
    peers, tel, live, sa = s["peers"], s["telemetry"], s["snmp_live"], s["session_auth"]
    gt = s["ground_truth"]

    # format
    for f in ("lineid", "mac"):
        if not MAC.match(sub[f]):
            E(f"subscriber.{f} bad MAC format: {sub[f]}")
    if not IFACE.match(sub["interface"]):
        E(f"subscriber.interface bad: {sub['interface']}")
    if sub["olt_technology"] != "EPON":
        E("olt_technology must be EPON")
    if sub["olt_model"] != "V1600D":
        E("olt_model must be V1600D")
    if not re.match(r"^10\.220\.\d{1,3}\.\d{1,3}$", sub["olt_ip"]):
        E(f"olt_ip outside 10.220.0.0/16: {sub['olt_ip']}")

    # stored powers are strings, live are numbers
    for f in ("rx_power", "tx_power"):
        if not isinstance(ns[f], str):
            E(f"network_state.{f} must be a string")
        elif ns[f] not in ("0", None) and not re.match(r"^-?\d+\.\d{2}$", ns[f]):
            E(f"network_state.{f} needs 2 decimals: {ns[f]}")
    for f in ("rx_power", "tx_power"):
        v = live["onu"].get(f)
        if v is not None and not isinstance(v, (int, float)):
            E(f"snmp_live.onu.{f} must be a number or null")

    # physical plausibility
    def numeric(x):
        try:
            return float(x)
        except (TypeError, ValueError):
            return None

    rx = numeric(ns["rx_power"])
    if rx is not None and ns["rx_power"] != "0" and not (-40.0 <= rx <= 3.7):
        E(f"rx_power out of range: {rx}")
    tx = numeric(ns["tx_power"])
    if tx is not None and ns["tx_power"] != "0" and not (-10.0 <= tx <= 5.6):
        E(f"tx_power out of range: {tx}")
    if tx is not None and ns["tx_power"] != "0" and not (0.0 <= tx <= 5.0):
        W(f"tx_power {tx} outside healthy 0..+5 band (intended?)")

    om = ns["olt_metrics"]
    if om["cpu_load"] == 0 and om["memory_usage"] == 0 and om["temperature"] == 0:
        if ns["olt_health"]["snmp_response_ok"]:
            E("olt_metrics zeroed while SNMP is reported working")
    if om["cpu_load"] > 48: E(f"olt cpu_load > 48: {om['cpu_load']}")
    if om["memory_usage"] > 76: E(f"olt memory_usage > 76: {om['memory_usage']}")
    if om["temperature"] > 68: E(f"olt temperature > 68: {om['temperature']}")

    # telemetry
    os_ = tel["onu_series"]
    n = os_["window_hours"]
    for sig in ("rx_power", "tx_power", "temperature", "distance",
                "tx_bias_current", "supply_voltage", "speed_kbps"):
        if sig not in os_:
            E(f"telemetry.onu_series missing {sig}")
        elif len(os_[sig]) != n:
            E(f"telemetry {sig} length {len(os_[sig])} != window_hours {n}")
    # 0 is the poller's no-read default, like null
    def live_vals(key):
        return [x for x in os_.get(key, []) if x is not None and x != 0]

    d = live_vals("distance")
    if d and len(set(d)) > 1 and m["fault_type"] != "distance_change":
        E(f"distance varies but fault_type is {m['fault_type']}")
    if d and not all(6 <= x <= 365 for x in d):
        E("distance outside 6..365 m")
    bias = live_vals("tx_bias_current")
    if bias and m["fault_type"] != "laser_degradation":
        if not all(8.0 <= x <= 14.5 for x in bias):
            W("tx_bias_current outside 9.5..13.0 healthy band")
    volt = live_vals("supply_voltage")
    if volt and not all(3.30 <= x <= 3.55 for x in volt):
        W("supply_voltage outside 3.40..3.46 healthy band")

    # a declared gap must correspond to real nulls, and nulls must be declared
    declared = set()
    for g in tel.get("availability", {}).get("gaps", []):
        declared.add(g["signal"])
    nulls = {k for k in ("rx_power", "tx_power", "temperature", "distance",
                         "tx_bias_current", "supply_voltage", "speed_kbps")
             if any(x is None for x in os_.get(k, []))}
    offline_ok = (m["fault_type"] in ("onu_offline", "pon_port_failure",
                                      "splitter_failure", "olt_failure")
                  or ns["onu_status"] == 0)
    if nulls and not offline_ok and not declared:
        E(f"nulls in telemetry {sorted(nulls)} with no declared gaps and no offline fault")
    if tel["availability"]["onu_series_complete"] and nulls and not offline_ok:
        E("onu_series_complete is true but nulls are present")

    # noise floor on healthy optical series
    healthy_optics = m["fault_type"] not in (
        "fiber_degradation", "laser_degradation", "distance_change",
        "onu_offline", "pon_port_failure", "splitter_failure",
        "session_flapping_signal")
    if healthy_optics:
        rr = [x for x in os_["rx_power"][-24:] if x is not None and x != 0]
        tt = [x for x in os_["tx_power"][-24:] if x is not None and x != 0]
        if len(rr) >= 12:
            r = max(rr) - min(rr)
            if r > 0.9:
                E(f"healthy RX 24h range {r:.2f} exceeds noise floor (~0.6)")
        if len(tt) >= 12:
            t = max(tt) - min(tt)
            if t > 0.25:
                E(f"healthy TX 24h range {t:.2f} exceeds noise floor (~0.16)")

    # health record internal consistency
    h = ns["olt_health"]
    if h["snmp_community_ok"] != h["snmp_response_ok"]:
        E("snmp_community_ok must equal snmp_response_ok (same sysUpTime get)")
    if h["healthy_pons"] + len(h["failed_pons_list"]) != h["total_pons_tested"]:
        E(f"healthy_pons + failed != total_pons_tested "
          f"({h['healthy_pons']} + {len(h['failed_pons_list'])} != {h['total_pons_tested']})")
    crit = (h["overall_status"] == "critical")
    should = (h["healthy_pons"] == 0 and h["total_pons_tested"] > 0)
    if h["ping_ok"] and h["snmp_response_ok"] and crit != should:
        E(f"overall_status '{h['overall_status']}' inconsistent with "
          f"healthy_pons={h['healthy_pons']}/{h['total_pons_tested']}")
    if h["overall_status"] == "healthy" and h["error_description"] is not None:
        E("healthy status must carry a null error_description")

    # peers
    p = peers["olt_population"]
    if p["onu_online_count"] + p["onu_offline_count"] != p["total_customers"]:
        E("online + offline != total_customers")
    if sum(p["customers_per_port"].values()) != p["total_customers"]:
        E(f"customers_per_port sums to {sum(p['customers_per_port'].values())}, "
          f"total_customers is {p['total_customers']}")
    if p["pon_ports_in_use"] > 8:
        E("pon_ports_in_use > 8 (EPON max)")
    if len(p["customers_per_port"]) != p["pon_ports_in_use"]:
        E("customers_per_port entries != pon_ports_in_use")
    port = peers["interface_port"]
    for c in peers["crm_view"]["customers"]:
        if not c["interface"].startswith(port + ":"):
            E(f"peer {c['lineid']} not on {port}")
    if sub["lineid"] not in [c["lineid"] for c in peers["crm_view"]["customers"]]:
        E("subject lineid absent from peers.crm_view.customers")
    for c in peers["crm_view"]["customers"]:
        if c["interface"] == sub["interface"] and c["lineid"] != sub["lineid"]:
            if peers.get("duplicate_slot_conflict") is None:
                E(f"two lineids on {sub['interface']} but duplicate_slot_conflict is null")
    off = p["onu_offline_count"] / p["total_customers"]
    outage = m["fault_type"] in ("pon_port_failure", "splitter_failure", "olt_failure",
                                 "router_unreachable")
    if not outage and not (0.0 <= off <= 0.12):
        W(f"offline rate {off:.1%} far from 4.85% baseline for a non-outage fault")

    # onu model capability agreement
    caps = MODEL_CAPS.get(sub["onu_model"])
    if caps:
        t, cv, vo = caps
        if sub["onu_type"] != t: E(f"onu_type {sub['onu_type']} != {t} for model")
        if sub["has_catv"] != cv: E("has_catv disagrees with onu_model")
        if sub["has_voip"] != vo: E("has_voip disagrees with onu_model")

    # radius
    r = sa["radius"]
    if r["radcheck_exists"] and r["username"] != sub["mac"]:
        E(f"radius.username {r['username']} != subscriber.mac {sub['mac']}")
    ip = r.get("assigned_ip")
    if r.get("framed_pool") == "pool_Disable_Users":
        if ip and not ip.startswith("10.200.200."):
            E("pool_Disable_Users requires an IP in 10.200.200.0/24")
    elif ip and ip.startswith("10.200.200."):
        E("IP in disable pool without framed_pool set")

    # sessions vs baseline
    c24 = sa["sessions"]["count_24h"]
    flap = m["fault_type"] in ("session_flapping_signal", "session_flapping_auth",
                               "fiber_degradation", "radius_replication_lag")
    if c24 > 26:
        E(f"count_24h {c24} exceeds the empirical ceiling of 26")
    intentional = m["fault_type"] in ("distance_change", "session_flapping_signal",
                                      "session_flapping_auth")
    if c24 >= 8 and not flap and not intentional:
        W(f"count_24h {c24} is flapping territory for fault_type {m['fault_type']}")
    if c24 <= 3 and flap and m["fault_type"].startswith("session_flapping"):
        E(f"count_24h {c24} is baseline but fault_type is {m['fault_type']}")

    # live probe uniformity for the false-critical signature
    if m["fault_type"] == "olt_health_false_critical":
        mech = m.get("mechanism", "a")
        probes = live["pon_probe"]["onus"]
        h = ns["olt_health"]
        if not (live["olt"]["ping_ok"] and live["olt"]["snmp_responds"]):
            E("false_critical requires ping and SNMP to succeed")
        if mech == "a":
            # OID subtree absent: uniform non-response, no service impact
            if not all(x["responds"] is False for x in probes):
                E("mechanism a requires responds:false uniformly across probes")
            if live["olt"]["oid_subtree_responds"] is not False:
                E("mechanism a requires oid_subtree_responds:false")
            if gt["service_impact"] is not False:
                E("mechanism a must have service_impact false")
        elif mech == "b":
            # all-or-nothing status rule: healthy label over a real outage
            if h["overall_status"] != "healthy":
                E("mechanism b requires overall_status healthy")
            if h["error_description"] is not None:
                E("mechanism b requires a null error_description")
            if not (0 < h["healthy_pons"] < h["total_pons_tested"]):
                E("mechanism b requires a partial PON failure")
            if gt["service_impact"] is not True:
                E("mechanism b must have service_impact true")
        elif mech == "c":
            # one-ONU sampling: the rest of the port is fine
            if all(x["responds"] is False for x in probes):
                E("mechanism c requires the rest of the port to respond")
            if not any(x.get("online") == 1 for x in probes):
                E("mechanism c requires surviving online ONUs on the port")
            if live["olt"]["oid_subtree_responds"] is not True:
                E("mechanism c requires oid_subtree_responds:true")
        elif mech == "d":
            # staleness: the record predates current device state
            if h["run_date"] >= m["captured_at"][:10]:
                E("mechanism d requires a run_date older than captured_at")
            if gt["service_impact"] is not False:
                E("mechanism d must have service_impact false")

    # ground truth
    if gt["fault_type"] != m["fault_type"]:
        E("ground_truth.fault_type != metadata.fault_type")
    if gt["affected_scope"] not in ("none", "single_customer", "pon_port",
                                    "olt", "router", "multi_customer"):
        E(f"bad affected_scope: {gt['affected_scope']}")
    if gt["severity"] not in ("Not classified", "Information", "Warning",
                              "Average", "High", "Disaster"):
        E(f"bad severity: {gt['severity']}")
    multi = gt["affected_scope"] in ("olt", "router", "pon_port", "multi_customer")
    if gt["affected_lineids"] or not multi:
        if gt["affected_customer_count"] != len(gt["affected_lineids"]):
            E("affected_customer_count != len(affected_lineids)")
    for f in ("expected_reasoning", "required_evidence", "distractors"):
        if not gt.get(f):
            E(f"ground_truth.{f} is empty")

    return errs, warns


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "/mnt/user-data/outputs/scenarios"
    files = sorted(glob.glob(os.path.join(target, "*.json")))
    total_e = 0
    for f in files:
        e, w = check(f)
        total_e += len(e)
        name = os.path.basename(f)
        status = "FAIL" if e else ("pass" if not w else "pass (warnings)")
        print(f"\n{name}: {status}")
        for x in e:
            print(f"   ERROR  {x}")
        for x in w:
            print(f"   warn   {x}")
    print(f"\n{len(files)} file(s), {total_e} error(s)")
    sys.exit(1 if total_e else 0)
