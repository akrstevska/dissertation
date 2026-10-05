#!/usr/bin/env python3
"""Shared estate, MAC allocation and section builders for the scenario set."""
import random, math
from datetime import datetime, timedelta, timezone

H = 168
_rng = random.Random(20260923)

ONU_OUI = ["4C:D7:C8", "00:A1:07", "80:F1:A8", "4C:46:D1", "78:88:8A", "B4:64:15", "70:B6:4F"]
CPE_OUI = ["C8:3A:35", "30:16:9D", "80:AF:CA", "50:0F:F5", "CC:2D:21", "00:EB:D8"]

_used = set()
# MACs already spent by the three sample scenarios
for m in ["4C:D7:C8:A1:3F:02", "C8:3A:35:7B:11:E4", "00:A1:07:C4:1D:88", "30:16:9D:A2:5F:03",
          "4C:46:D1:B8:03:2C", "50:0F:F5:D1:77:96", "4C:EA:41:0B:77:19", "0C:B9:12:5C:20:AA",
          "00:A1:07:3D:81:47", "80:F1:A8:66:0C:9B", "4C:46:D1:19:B2:30", "78:88:8A:4E:55:C1",
          "B4:64:15:02:9A:6E", "4C:D7:C8:77:0A:12", "70:B6:4F:31:C9:6D", "80:F1:A8:1B:44:7F",
          "4C:46:D1:5E:80:A4", "B4:64:15:6C:23:11", "4C:D7:C8:2E:91:40", "70:B6:4F:8A:16:D3",
          "00:A1:07:50:C8:7B", "80:F1:A8:D4:62:09", "B4:64:15:39:AE:54", "78:88:8A:67:1F:B2",
          "1C:EF:03:90:2B:5A"]:
    _used.add(m)


def mac(pool):
    while True:
        m = "%s:%02X:%02X:%02X" % (_rng.choice(pool), _rng.randint(0, 255),
                                   _rng.randint(0, 255), _rng.randint(0, 255))
        if m not in _used:
            _used.add(m)
            return m


def onu_mac():
    return mac(ONU_OUI)


def cpe_mac():
    return mac(CPE_OUI)


# ---------------------------------------------------------------- estate
ESTATE = {
    "ANC08":      dict(host="TK_AZ-OLT_SK_ANC-08",        ip="10.220.114.5", ext="10417", code=1,  ports=8, cust=298, router=("TK_Skopje13-ANC01", 31, "CCR2216-1G-12XS-2XQ"), city="Skopje", area="ANC",        fw="V2.03.78R"),
    "GRAD01":     dict(host="TK_AZ-OLT_SK-Gradezen-01",   ip="10.220.88.4",  ext="10362", code=5,  ports=8, cust=281, router=("TK_Skopje02-Gradezen", 18, "CCR2116-12G-4S+"),   city="Skopje", area="Gradezen",   fw="V2.03.78R"),
    "BOGO05":     dict(host="TK_AF_OLT_OH_Bogomilska-05", ip="10.220.57.6",  ext="10238", code=2,  ports=7, cust=183, router=("TK_AZ_Ohrid_Bogomilska", 9, "CCR2004-1G-12S+2XS"), city="Ohrid",  area="Bogomilska", fw="V2.04.12R"),
    "KV03":       dict(host="TK_AF-OLT_KV03",             ip="10.220.41.8",  ext="10155", code=3,  ports=8, cust=214, router=("TK_Router_KV01", 22, "CCR1072-1G-8S+"),         city="Kavadarci", area="KV",     fw="V2.03.78R"),
    "VE05":       dict(host="TK_AZ_OLT-VE05",             ip="10.220.72.11", ext="10298", code=4,  ports=8, cust=272, router=("TK_Router_VE01", 27, "CCR2216-1G-12XS-2XQ"),    city="Veles",   area="VE",        fw="V2.03.78R"),
    "JAD04":      dict(host="TK_AZ-OLT_BT_Jad-04",        ip="10.220.39.9",  ext="10203", code=6,  ports=8, cust=271, router=("TK_AZ_Bitola_Jadranska01", 12, "CCR2116-12G-4S+"), city="Bitola", area="Jadranska", fw="V2.03.78R"),
    "SR01":       dict(host="TK_AF-OLT_SR01",             ip="10.220.1.3",   ext="10087", code=7,  ports=6, cust=148, router=("TK_Router_SR01", 35, "CCR1036-12G-4S"),         city="Strumica", area="SR",       fw="V2.03.78R"),
    "VSB02":      dict(host="TK_AZ-OLT_SK_V_S_B-02",      ip="10.220.96.7",  ext="10381", code=8,  ports=3, cust=76,  router=("TK_Skopje10-V_S_B", 25, "CCR2004-1G-12S+2XS"),   city="Skopje",  area="VSB",       fw="V2.03.78R"),
    "KO14":       dict(host="TK_AZ_OLT-KO-14",            ip="10.220.60.15", ext="10331", code=9,  ports=7, cust=167, router=("TK_Router_KO03", 20, "CCR1072-1G-8S+"),         city="Kocani",  area="KO",        fw="V2.04.12R"),
    "PP03":       dict(host="TK_AF-OLT_PP03",             ip="10.220.28.4",  ext="10122", code=10, ports=8, cust=236, router=("TK_Prilep_NC", 14, "CCR2116-12G-4S+"),          city="Prilep",  area="PP",        fw="V2.03.78R"),
    "OHSC02":     dict(host="TK_AZ-OLT_OH_SC-02",         ip="10.220.55.3",  ext="10231", code=11, ports=7, cust=192, router=("TK_AZ_Ohrid_SC", 10, "CCR2004-1G-12S+2XS"),     city="Ohrid",   area="SC",        fw="V2.03.78R"),
    "MADZ01":     dict(host="TK_AZ-OLT_SK-Madzari-01",    ip="10.220.121.4", ext="10444", code=12, ports=6, cust=139, router=("TK_Skopje15-Madzari01", 40, "CCR2004-1G-12S+2XS"), city="Skopje", area="Madzari",  fw="V2.03.78R"),
}

MODELS = [
    ("Aztech 1G + CATV", "Bridge", 1, 0),
    ("JM 1G + CATV + WiFi + POTs", "Router", 1, 1),
    ("Aztech 1G", "Bridge", 0, 0),
    ("Infel 1G + CATV", "Bridge", 1, 0),
    ("JM 1G + CATV", "Bridge", 1, 0),
    ("Raisecom 1G", "Bridge", 0, 0),
    ("Aztech 2GE + WiFi(dual band) + POTs + CATV", "Router", 1, 1),
]
PROFILES = (["profile_20M"] * 56 + ["profile_40M"] * 15 + ["profile_30M_1M"] * 11 +
            ["profile_CATV"] * 6 + ["profile_80M"] * 6 + ["profile_300M"] * 5 + ["profile_100M"])


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def r2(x):
    return round(x, 2)


def flat(base, sd, n=H, clip=None):
    out = []
    for _ in range(n):
        v = _rng.gauss(base, sd)
        if clip:
            v = max(clip[0], min(clip[1], v))
        out.append(r2(v))
    return out


def diurnal(base, amp, sd, n=H):
    return [r2(base + amp * math.sin(2 * math.pi * (i % 24) / 24.0) + _rng.gauss(0, sd))
            for i in range(n)]


def ramp(start, end, sd, n=H, knee=0):
    out, span = [], max(1, n - 1 - knee)
    for i in range(n):
        base = start if i < knee else start + (end - start) * ((i - knee) / span)
        out.append(r2(base + _rng.gauss(0, sd)))
    return out


def step(before, after, at, sd, n=H):
    return [r2((before if i < at else after) + _rng.gauss(0, sd)) for i in range(n)]


def cliff(series, at, value=None):
    """Truncate a series at an index: everything after becomes value (or None)."""
    return series[:at] + [value] * (len(series) - at)


def vlan_for(olt_key, port):
    return 1000 + ESTATE[olt_key]["code"] * 10 + port


def port_map(olt_key, subject_port, subject_count):
    e = ESTATE[olt_key]
    counts, remaining = {}, e["cust"] - subject_count
    others = [p for p in range(1, e["ports"] + 1) if p != subject_port]
    base = remaining // len(others)
    for i, p in enumerate(others):
        counts[f"EPON0/{p}"] = base
    counts[f"EPON0/{others[-1]}"] += remaining - base * len(others)
    counts[f"EPON0/{subject_port}"] = subject_count
    return {f"EPON0/{p}": counts[f"EPON0/{p}"] for p in range(1, e["ports"] + 1)}


def make_peers(olt_key, port, subject_lineid, subject_rx, subject_status=1,
               n_on_port=24, n_listed=7, peer_rx=None, peer_status=None,
               subject_idx=None, extra=None):
    """Build peers.crm_view + olt_population. peer_rx/peer_status are dicts by index."""
    e = ESTATE[olt_key]
    peer_rx = peer_rx or {}
    peer_status = peer_status or {}
    idxs = sorted(_rng.sample(range(1, min(64, n_on_port * 2)), n_listed - 1))
    if subject_idx is None:
        subject_idx = idxs[len(idxs) // 2]
    idxs = [i for i in idxs if i != subject_idx] + [subject_idx]
    idxs = sorted(set(idxs))

    custs = []
    for i in idxs:
        if i == subject_idx:
            custs.append({"lineid": subject_lineid, "interface": f"EPON0/{port}:{i}",
                          "onu_status": subject_status,
                          "rx_power": subject_rx if isinstance(subject_rx, str) else f"{subject_rx:.2f}",
                          "active": 1})
        else:
            rx = peer_rx.get(i, r2(_rng.gauss(-20.9, 1.6)))
            custs.append({"lineid": onu_mac(), "interface": f"EPON0/{port}:{i}",
                          "onu_status": peer_status.get(i, 1), "rx_power": f"{rx:.2f}", "active": 1})
    if extra:
        custs.extend(extra)
        custs.sort(key=lambda c: int(c["interface"].split(":")[1]))

    cpp = port_map(olt_key, port, n_on_port)
    offline = max(1, round(e["cust"] * 0.0485 * _rng.uniform(0.7, 1.3)))
    return {
        "interface_port": f"EPON0/{port}",
        "crm_view": {"total_on_port": n_on_port, "customers": custs},
        "olt_population": {
            "total_customers": e["cust"],
            "pon_ports_in_use": e["ports"],
            "customers_per_port": cpp,
            "onu_online_count": e["cust"] - offline,
            "onu_offline_count": offline,
        },
        "duplicate_slot_conflict": None,
    }, idxs, subject_idx


def healthy_olt_health(olt_key, run_date):
    e = ESTATE[olt_key]
    return {
        "olt_ip": e["ip"], "olt_host": e["host"], "olt_technology": "EPON", "olt_ext_id": e["ext"],
        "ping_ok": True, "snmp_community_ok": True, "snmp_response_ok": True,
        "total_pons_tested": e["ports"], "healthy_pons": e["ports"], "failed_pons_list": [],
        "error_description": None, "overall_status": "healthy", "run_date": run_date,
    }


def olt_metrics(olt_key, cpu=None, mem=None, temp=None, up=None):
    e = ESTATE[olt_key]
    return {
        "cpu_load": cpu if cpu is not None else int(_rng.gauss(24, 3)),
        "memory_usage": mem if mem is not None else int(_rng.gauss(18, 2)),
        "temperature": temp if temp is not None else int(_rng.gauss(42, 3)),
        "uptime_days": up if up is not None else _rng.randint(5, 91),
        "firmware": e["fw"],
        "firmware_date": "2025-11-28" if e["fw"] == "V2.04.12R" else "2024-06-11",
    }


def router_state(olt_key, cap, hours=None, status="ok", never=False):
    name, rid, model = ESTATE[olt_key]["router"]
    if never:
        return {"name": name, "model": model, "os_version": "7.24", "last_checkin": None,
                "hours_since_checkin": None, "heartbeat_status": "never",
                "cpu_usage": 4, "memory_utilization": 0, "temperature": 38}
    h = hours if hours is not None else 0.2
    return {"name": name, "model": model, "os_version": "7.24",
            "last_checkin": iso(cap - timedelta(hours=h)),
            "hours_since_checkin": round(h, 2), "heartbeat_status": status,
            "cpu_usage": int(_rng.gauss(5, 2)), "memory_utilization": 0,
            "temperature": int(_rng.gauss(40, 3))}


def healthy_series(cap, rx_base=-20.5, tx_base=2.35, dist=140,
                   bias_base=11.2, volt_base=3.43, temp_base=22.0):
    start = cap - timedelta(hours=H - 1)
    return start, {
        "interval": "1h", "window_hours": H, "series_start": iso(start),
        "rx_power": flat(rx_base, 0.15),
        "tx_power": flat(tx_base, 0.04),
        "temperature": diurnal(temp_base, 1.7, 0.30),
        "distance": [dist] * H,
        "tx_bias_current": flat(bias_base, 0.15),
        "supply_voltage": flat(volt_base, 0.010),
        "speed_kbps": [r2(max(0.05, _rng.gauss(5.4, 2.3))) for _ in range(H)],
    }


def olt_series(cap, cpu=24, mem=18, temp=42):
    start = cap - timedelta(hours=H - 1)
    return {
        "interval": "1h", "window_hours": H, "series_start": iso(start),
        "cpu_load": [int(max(0, min(48, _rng.gauss(cpu, 3)))) for _ in range(H)],
        "memory_usage": [int(max(0, min(76, _rng.gauss(mem, 1.5)))) for _ in range(H)],
        "temperature": [int(max(0, min(68, _rng.gauss(temp, 2)))) for _ in range(H)],
    }


def pon_probe(port, idxs, rx_by_idx, online_by_idx=None, responds_by_idx=None):
    online_by_idx = online_by_idx or {}
    responds_by_idx = responds_by_idx or {}
    onus = []
    for i in idxs:
        resp = responds_by_idx.get(i, True)
        on = online_by_idx.get(i, 1)
        if not resp:
            onus.append({"onu_index": i, "online": None, "rx_power": None,
                         "tx_power": None, "responds": False})
        elif on == 0:
            onus.append({"onu_index": i, "online": 0, "rx_power": None,
                         "tx_power": None, "responds": True})
        else:
            rx = rx_by_idx.get(i, r2(_rng.gauss(-20.9, 1.6)))
            onus.append({"onu_index": i, "online": 1, "rx_power": rx,
                         "tx_power": r2(_rng.gauss(2.4, 0.08)), "responds": True})
    return {"interface_port": f"EPON0/{port}", "onus": onus}


def vlan_walk(olt_key, port, actual=None):
    e = ESTATE[olt_key]
    present = [1, 46, 100] + [vlan_for(olt_key, p) for p in range(1, e["ports"] + 1)] + [1998, 1999]
    exp = vlan_for(olt_key, port)
    return {"responds": True, "vlans_present": present,
            "customer_vlan_expected": exp,
            "customer_vlan_actual": actual if actual is not None else exp}


def sessions(cap, count24=2, count7=15, avg_min=694, last_gap_h=14.8, n_recent=3, ip="10.5.50.88",
             ips=None, durations=None):
    rec, t = [], cap - timedelta(hours=last_gap_h)
    for k in range(n_recent):
        dur = durations[k] if durations else int(avg_min * 60 * _rng.uniform(0.7, 1.3))
        addr = (ips[k % len(ips)] if ips else ip)
        rec.append({"start": iso(t), "end": None if k == 0 else iso(t + timedelta(seconds=dur)),
                    "duration_s": dur, "ip": addr})
        t = t - timedelta(seconds=dur + _rng.randint(60, 900))
    return {"count_24h": count24, "count_7d": count7, "avg_duration_minutes": avg_min,
            "last_disconnect": iso(cap - timedelta(hours=last_gap_h)), "recent": rec}


def radius(m, lineid, ip="10.5.50.88", pool=None, exists=True, consistent=True, mismatches=None):
    return {"radcheck_exists": exists,
            "username": m if exists else None,
            "lineid_in_radius": lineid if exists else None,
            "framed_pool": pool,
            "assigned_ip": ip,
            "crm_consistent": consistent,
            "mismatches": mismatches or []}


def traffic(down=None, up=None, cur=210, avg=205, peak=640):
    down = down or [950, 1020, 880, 1010, 940, 1080, 970]
    up = up or [d * 6 + _rng.randint(-200, 200) for d in down]
    return {"download_mb_daily": down, "upload_mb_daily": up,
            "monthly_avg_download_mb": sum(down) // len(down),
            "monthly_avg_upload_mb": sum(up) // len(up),
            "pon_port_traffic": {"current_mbps": cur, "avg_mbps": avg, "peak_mbps": peak}}


def subscriber(olt_key, port, idx, lineid, m, model_i=0, profile=None, active=1,
               catv_service=1, catv_synced=1, cid=None):
    e = ESTATE[olt_key]
    name, typ, cv, vo = MODELS[model_i]
    return {
        "customer_id": cid or _rng.randint(10000, 34000),
        "lineid": lineid, "mac": m, "interface": f"EPON0/{port}:{idx}",
        "olt_id": e["ext"], "olt_host": e["host"], "olt_ip": e["ip"],
        "olt_technology": "EPON", "olt_model": "V1600D",
        "router_id": e["router"][1], "router_name": e["router"][0],
        "profile": profile or _rng.choice(PROFILES),
        "active": active, "deleted": 0,
        "onu_model": name, "onu_type": typ, "has_catv": cv, "has_voip": vo,
        "catv_service": catv_service if cv else 0, "catv_synced": catv_synced,
        "city": e["city"], "area": e["area"],
    }
