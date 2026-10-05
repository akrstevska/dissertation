#!/usr/bin/env python3
"""Generate the three sample scenarios with calibrated telemetry series.

Noise floors enforced per calibration.md §6.2:
  RX  sd 0.10 dBm  -> ~+/-0.3 range over 24h
  TX  sd 0.025 dBm -> ~+/-0.08 range over 24h
"""
import json, random, math, os
from datetime import datetime, timedelta, timezone

random.seed(20260921)

H = 168  # 7 days hourly


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def r2(x):
    return round(x, 2)


def flat(base, sd, n=H, clip=None):
    out = []
    for _ in range(n):
        v = random.gauss(base, sd)
        if clip:
            v = max(clip[0], min(clip[1], v))
        out.append(r2(v))
    return out


def diurnal_temp(base, amp, sd, n=H):
    return [r2(base + amp * math.sin(2 * math.pi * (i % 24) / 24.0) + random.gauss(0, sd))
            for i in range(n)]


def ramp(start, end, sd, n=H, knee=None):
    """Linear drift start->end with noise. knee = index where drift begins."""
    out = []
    k = knee if knee is not None else 0
    span = max(1, n - 1 - k)
    for i in range(n):
        if i < k:
            base = start
        else:
            base = start + (end - start) * ((i - k) / span)
        out.append(r2(base + random.gauss(0, sd)))
    return out


def erratic(base, sd, n=H, spikes=()):
    out = flat(base, sd, n)
    for idx, val in spikes:
        out[idx] = r2(val)
    return out


# ---------------------------------------------------------------- FD-001
def fd001():
    cap = datetime(2026, 9, 20, 14, 20, tzinfo=timezone.utc)
    start = cap - timedelta(hours=H - 1)

    rx = ramp(-19.20, -26.40, 0.15, knee=24)
    tx = flat(2.31, 0.040)
    temp = diurnal_temp(22.4, 1.8, 0.30)
    dist = [188] * H
    bias = flat(11.20, 0.15)
    volt = flat(3.44, 0.010)
    speed = [r2(max(0.05, random.gauss(4.4, 2.1))) for _ in range(H)]
    # throughput collapses as the link degrades
    for i in range(H - 48, H):
        speed[i] = r2(max(0.02, speed[i] * (1 - 0.85 * (i - (H - 48)) / 48)))

    cpu = [int(max(0, min(48, random.gauss(24, 3)))) for _ in range(H)]
    mem = [int(max(0, min(76, random.gauss(17, 1.5)))) for _ in range(H)]
    otemp = [int(max(0, min(68, random.gauss(41, 2)))) for _ in range(H)]

    return {
        "metadata": {
            "scenario_id": "FD-001",
            "fault_type": "fiber_degradation",
            "difficulty": "easy",
            "captured_at": iso(cap),
            "description": "Single customer with steadily worsening RX power over seven days; port neighbours unaffected and ONU still online.",
            "tests": [
                "Is progressive degradation distinguished from an outage?",
                "Is blast radius correctly bounded to one customer?",
                "Are elevated sessions read as a symptom rather than a separate fault?"
            ]
        },
        "trigger": {
            "type": "customer_complaint",
            "input": {
                "lineid": "4C:D7:C8:A1:3F:02",
                "complaint": "Internet is slow and keeps cutting out, worse in the evenings"
            }
        },
        "subscriber": {
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
        },
        "network_state": {
            "onu_status": 1,
            "rx_power": "-26.40",
            "tx_power": "2.31",
            "reading_age_minutes": 47,
            "olt_health": {
                "olt_ip": "10.220.114.5",
                "olt_host": "TK_AZ-OLT_SK_ANC-08",
                "olt_technology": "EPON",
                "olt_ext_id": "10417",
                "ping_ok": True,
                "snmp_community_ok": True,
                "snmp_response_ok": True,
                "total_pons_tested": 8,
                "healthy_pons": 8,
                "failed_pons_list": [],
                "error_description": None,
                "overall_status": "healthy",
                "run_date": "2026-09-20"
            },
            "olt_metrics": {
                "cpu_load": 24, "memory_usage": 17, "temperature": 41,
                "uptime_days": 83, "firmware": "V2.03.78R", "firmware_date": "2024-06-11"
            },
            "router_state": {
                "name": "TK_Skopje13-ANC01",
                "model": "CCR2216-1G-12XS-2XQ",
                "os_version": "7.24",
                "last_checkin": iso(cap - timedelta(minutes=18)),
                "hours_since_checkin": 0.3,
                "heartbeat_status": "ok",
                "cpu_usage": 4, "memory_utilization": 0, "temperature": 38
            }
        },
        "peers": {
            "interface_port": "EPON0/3",
            "crm_view": {
                "total_on_port": 22,
                "customers": [
                    {"lineid": "4C:EA:41:0B:77:19", "interface": "EPON0/3:1",  "onu_status": 1, "rx_power": "-19.80", "active": 1},
                    {"lineid": "0C:B9:12:5C:20:AA", "interface": "EPON0/3:2",  "onu_status": 1, "rx_power": "-21.15", "active": 1},
                    {"lineid": "00:A1:07:3D:81:47", "interface": "EPON0/3:5",  "onu_status": 1, "rx_power": "-20.52", "active": 1},
                    {"lineid": "80:F1:A8:66:0C:9B", "interface": "EPON0/3:8",  "onu_status": 1, "rx_power": "-22.04", "active": 1},
                    {"lineid": "4C:46:D1:19:B2:30", "interface": "EPON0/3:11", "onu_status": 1, "rx_power": "-19.33", "active": 1},
                    {"lineid": "4C:D7:C8:A1:3F:02", "interface": "EPON0/3:14", "onu_status": 1, "rx_power": "-26.40", "active": 1},
                    {"lineid": "78:88:8A:4E:55:C1", "interface": "EPON0/3:17", "onu_status": 1, "rx_power": "-21.77", "active": 1},
                    {"lineid": "B4:64:15:02:9A:6E", "interface": "EPON0/3:21", "onu_status": 0, "rx_power": "-20.91", "active": 1}
                ]
            },
            "olt_population": {
                "total_customers": 298,
                "pon_ports_in_use": 8,
                "customers_per_port": {"EPON0/1": 41, "EPON0/2": 38, "EPON0/3": 22,
                                       "EPON0/4": 47, "EPON0/5": 35, "EPON0/6": 40,
                                       "EPON0/7": 39, "EPON0/8": 36},
                "onu_online_count": 284,
                "onu_offline_count": 14
            },
            "duplicate_slot_conflict": None
        },
        "telemetry": {
            "onu_series": {
                "interval": "1h", "window_hours": H, "series_start": iso(start),
                "rx_power": rx, "tx_power": tx, "temperature": temp,
                "distance": dist, "tx_bias_current": bias,
                "supply_voltage": volt, "speed_kbps": speed
            },
            "olt_series": {
                "interval": "1h", "window_hours": H, "series_start": iso(start),
                "cpu_load": cpu, "memory_usage": mem, "temperature": otemp
            },
            "availability": {"onu_series_complete": True, "gaps": []}
        },
        "snmp_live": {
            "onu": {"responds": True, "online": 1, "rx_power": -27.10, "tx_power": 2.28,
                    "auth_flag": "Auth", "exchange": "Finish", "rtt_tq": 61},
            "olt": {"ping_ok": True, "snmp_responds": True,
                    "sys_uptime_seconds": 7171200, "oid_subtree_responds": True},
            "pon_probe": {
                "interface_port": "EPON0/3",
                "onus": [
                    {"onu_index": 1,  "online": 1, "rx_power": -19.78, "tx_power": 2.50, "responds": True},
                    {"onu_index": 2,  "online": 1, "rx_power": -21.11, "tx_power": 2.44, "responds": True},
                    {"onu_index": 5,  "online": 1, "rx_power": -20.49, "tx_power": 2.37, "responds": True},
                    {"onu_index": 8,  "online": 1, "rx_power": -22.01, "tx_power": 2.29, "responds": True},
                    {"onu_index": 11, "online": 1, "rx_power": -19.35, "tx_power": 2.52, "responds": True},
                    {"onu_index": 14, "online": 1, "rx_power": -27.10, "tx_power": 2.28, "responds": True},
                    {"onu_index": 17, "online": 1, "rx_power": -21.74, "tx_power": 2.41, "responds": True},
                    {"onu_index": 21, "online": 0, "rx_power": None,   "tx_power": None, "responds": True}
                ]
            },
            "vlan_walk": {
                "responds": True,
                "vlans_present": [1, 46, 100, 1011, 1012, 1013, 1014, 1015, 1016, 1017, 1018, 1998, 1999],
                "customer_vlan_expected": 1013,
                "customer_vlan_actual": 1013
            }
        },
        "session_auth": {
            "sessions": {
                "count_24h": 9, "count_7d": 27, "avg_duration_minutes": 71,
                "last_disconnect": iso(cap - timedelta(hours=2, minutes=14)),
                "recent": [
                    {"start": iso(cap - timedelta(hours=2, minutes=8)),  "end": None, "duration_s": 7680, "ip": "10.5.50.117"},
                    {"start": iso(cap - timedelta(hours=4, minutes=1)),  "end": iso(cap - timedelta(hours=2, minutes=14)), "duration_s": 6420, "ip": "10.5.50.117"},
                    {"start": iso(cap - timedelta(hours=7, minutes=36)), "end": iso(cap - timedelta(hours=4, minutes=9)),  "duration_s": 12420, "ip": "10.5.50.117"}
                ]
            },
            "radius": {
                "radcheck_exists": True,
                "username": "C8:3A:35:7B:11:E4",
                "lineid_in_radius": "4C:D7:C8:A1:3F:02",
                "framed_pool": None,
                "assigned_ip": "10.5.50.117",
                "crm_consistent": True,
                "mismatches": []
            },
            "traffic": {
                "download_mb_daily": [1010, 980, 940, 870, 610, 305, 128],
                "upload_mb_daily": [6240, 6100, 5980, 5410, 3820, 1905, 742],
                "monthly_avg_download_mb": 948,
                "monthly_avg_upload_mb": 6104,
                "pon_port_traffic": {"current_mbps": 188, "avg_mbps": 195, "peak_mbps": 610}
            }
        },
        "ground_truth": {
            "fault_type": "fiber_degradation",
            "root_cause": "Progressive attenuation in the fibre path between the splitter and this customer's ONU, consistent with a bend, damaged connector or degrading splice on the drop.",
            "severity": "Warning",
            "affected_scope": "single_customer",
            "affected_lineids": ["4C:D7:C8:A1:3F:02"],
            "affected_customer_count": 1,
            "service_impact": True,
            "expected_reasoning": [
                "Cached RX of -26.40 dBm sits in the degraded band (-25 to -28)",
                "Telemetry shows RX falling from -19.2 to -26.4 dBm over six days against a +/-0.3 dBm noise floor, so this is a trend and not a spot reading",
                "Live RX of -27.10 is below the cached -26.40, so degradation is still progressing",
                "TX power, TX bias current, supply voltage and distance are all flat, so the ONU laser and the fibre geometry are unchanged",
                "Port neighbours on EPON0/3 read -19 to -22 dBm, so the PON port, feeder and splitter are healthy",
                "The fault is therefore downstream of the splitter, in this customer's own fibre path",
                "Nine sessions in 24h against a 2-3 baseline is a symptom of the marginal link, not an independent auth fault",
                "Declining daily traffic is consistent with intermittent connectivity"
            ],
            "required_evidence": [
                "rx_trend_over_time",
                "peers_normal_on_same_port",
                "tx_and_bias_stable"
            ],
            "expected_remediation": "dispatch_technician",
            "expected_escalation": {
                "priority": "Warning",
                "category": "field_service",
                "requires_human_review": False,
                "review_reason": None
            },
            "distractors": [
                "Elevated session count invites a session_flapping_auth diagnosis",
                "Declining traffic alone could suggest congestion",
                "One neighbour (EPON0/3:21) is offline for unrelated reasons, at the 4.85% network baseline"
            ]
        }
    }


# ---------------------------------------------------------------- SF-002
def sf002():
    cap = datetime(2026, 9, 21, 9, 45, tzinfo=timezone.utc)
    start = cap - timedelta(hours=H - 1)

    rx = flat(-20.62, 0.15)
    tx = flat(2.44, 0.040)
    temp = diurnal_temp(21.1, 1.6, 0.30)
    dist = [96] * H
    bias = flat(10.65, 0.15)
    volt = flat(3.42, 0.010)
    speed = [r2(max(0.05, random.gauss(6.1, 2.6))) for _ in range(H)]
    # traffic gaps during rejected-auth windows, not a smooth decline
    for i in (38, 39, 57, 58, 59, 91, 92, 118, 119, 140, 141, 142, 160, 161):
        speed[i] = 0.0

    cpu = [int(max(0, min(48, random.gauss(26, 3)))) for _ in range(H)]
    mem = [int(max(0, min(76, random.gauss(18, 1.5)))) for _ in range(H)]
    otemp = [int(max(0, min(68, random.gauss(43, 2)))) for _ in range(H)]

    return {
        "metadata": {
            "scenario_id": "SF-002",
            "fault_type": "session_flapping_auth",
            "difficulty": "hard",
            "captured_at": iso(cap),
            "description": "Heavy session flapping with a completely clean optical layer; a duplicate RADIUS entry for the same username resolves inconsistently.",
            "tests": [
                "Is a second data layer searched once the optical layer comes back clean?",
                "Is the absence of an optical explanation treated as evidence?",
                "Is the duplicate radcheck entry found rather than the fault being attributed to the ONU?"
            ]
        },
        "trigger": {
            "type": "threshold_breach",
            "input": {
                "signal": "session_disconnect_count",
                "lineid": "00:A1:07:C4:1D:88",
                "value": 19
            }
        },
        "subscriber": {
            "customer_id": 27733,
            "lineid": "00:A1:07:C4:1D:88",
            "mac": "30:16:9D:A2:5F:03",
            "interface": "EPON0/5:9",
            "olt_id": "10362",
            "olt_host": "TK_AZ-OLT_SK-Gradezen-01",
            "olt_ip": "10.220.88.4",
            "olt_technology": "EPON",
            "olt_model": "V1600D",
            "router_id": 18,
            "router_name": "TK_Skopje02-Gradezen",
            "profile": "profile_40M",
            "active": 1,
            "deleted": 0,
            "onu_model": "JM 1G + CATV + WiFi + POTs",
            "onu_type": "Router",
            "has_catv": 1,
            "has_voip": 1,
            "catv_service": 1,
            "catv_synced": 1,
            "city": "Skopje",
            "area": "Gradezen"
        },
        "network_state": {
            "onu_status": 1,
            "rx_power": "-20.62",
            "tx_power": "2.44",
            "reading_age_minutes": 12,
            "olt_health": {
                "olt_ip": "10.220.88.4",
                "olt_host": "TK_AZ-OLT_SK-Gradezen-01",
                "olt_technology": "EPON",
                "olt_ext_id": "10362",
                "ping_ok": True,
                "snmp_community_ok": True,
                "snmp_response_ok": True,
                "total_pons_tested": 8,
                "healthy_pons": 8,
                "failed_pons_list": [],
                "error_description": None,
                "overall_status": "healthy",
                "run_date": "2026-09-21"
            },
            "olt_metrics": {
                "cpu_load": 26, "memory_usage": 18, "temperature": 43,
                "uptime_days": 47, "firmware": "V2.03.78R", "firmware_date": "2024-06-11"
            },
            "router_state": {
                "name": "TK_Skopje02-Gradezen",
                "model": "CCR2116-12G-4S+",
                "os_version": "7.24",
                "last_checkin": iso(cap - timedelta(minutes=9)),
                "hours_since_checkin": 0.15,
                "heartbeat_status": "ok",
                "cpu_usage": 6, "memory_utilization": 0, "temperature": 41
            }
        },
        "peers": {
            "interface_port": "EPON0/5",
            "crm_view": {
                "total_on_port": 28,
                "customers": [
                    {"lineid": "4C:D7:C8:77:0A:12", "interface": "EPON0/5:2",  "onu_status": 1, "rx_power": "-21.40", "active": 1},
                    {"lineid": "70:B6:4F:31:C9:6D", "interface": "EPON0/5:4",  "onu_status": 1, "rx_power": "-19.95", "active": 1},
                    {"lineid": "00:A1:07:C4:1D:88", "interface": "EPON0/5:9",  "onu_status": 1, "rx_power": "-20.62", "active": 1},
                    {"lineid": "80:F1:A8:1B:44:7F", "interface": "EPON0/5:13", "onu_status": 1, "rx_power": "-22.18", "active": 1},
                    {"lineid": "4C:46:D1:5E:80:A4", "interface": "EPON0/5:19", "onu_status": 1, "rx_power": "-20.07", "active": 1},
                    {"lineid": "B4:64:15:6C:23:11", "interface": "EPON0/5:24", "onu_status": 1, "rx_power": "-21.63", "active": 1}
                ]
            },
            "olt_population": {
                "total_customers": 281,
                "pon_ports_in_use": 8,
                "customers_per_port": {"EPON0/1": 33, "EPON0/2": 36, "EPON0/3": 31,
                                       "EPON0/4": 42, "EPON0/5": 28, "EPON0/6": 39,
                                       "EPON0/7": 37, "EPON0/8": 35},
                "onu_online_count": 268,
                "onu_offline_count": 13
            },
            "duplicate_slot_conflict": None
        },
        "telemetry": {
            "onu_series": {
                "interval": "1h", "window_hours": H, "series_start": iso(start),
                "rx_power": rx, "tx_power": tx, "temperature": temp,
                "distance": dist, "tx_bias_current": bias,
                "supply_voltage": volt, "speed_kbps": speed
            },
            "olt_series": {
                "interval": "1h", "window_hours": H, "series_start": iso(start),
                "cpu_load": cpu, "memory_usage": mem, "temperature": otemp
            },
            "availability": {"onu_series_complete": True, "gaps": []}
        },
        "snmp_live": {
            "onu": {"responds": True, "online": 1, "rx_power": -20.58, "tx_power": 2.45,
                    "auth_flag": "Auth", "exchange": "Finish", "rtt_tq": 53},
            "olt": {"ping_ok": True, "snmp_responds": True,
                    "sys_uptime_seconds": 4060800, "oid_subtree_responds": True},
            "pon_probe": {
                "interface_port": "EPON0/5",
                "onus": [
                    {"onu_index": 2,  "online": 1, "rx_power": -21.37, "tx_power": 2.48, "responds": True},
                    {"onu_index": 4,  "online": 1, "rx_power": -19.91, "tx_power": 2.51, "responds": True},
                    {"onu_index": 9,  "online": 1, "rx_power": -20.58, "tx_power": 2.45, "responds": True},
                    {"onu_index": 13, "online": 1, "rx_power": -22.15, "tx_power": 2.33, "responds": True},
                    {"onu_index": 19, "online": 1, "rx_power": -20.04, "tx_power": 2.40, "responds": True},
                    {"onu_index": 24, "online": 1, "rx_power": -21.60, "tx_power": 2.37, "responds": True}
                ]
            },
            "vlan_walk": {
                "responds": True,
                "vlans_present": [1, 46, 100, 1051, 1052, 1053, 1054, 1055, 1056, 1057, 1058, 1998, 1999],
                "customer_vlan_expected": 1055,
                "customer_vlan_actual": 1055
            }
        },
        "session_auth": {
            "sessions": {
                "count_24h": 19, "count_7d": 118, "avg_duration_minutes": 38,
                "last_disconnect": iso(cap - timedelta(minutes=22)),
                "recent": [
                    {"start": iso(cap - timedelta(minutes=19)), "end": None, "duration_s": 1140, "ip": "10.5.50.204"},
                    {"start": iso(cap - timedelta(hours=1, minutes=4)),  "end": iso(cap - timedelta(minutes=22)), "duration_s": 2520, "ip": "10.5.50.204"},
                    {"start": iso(cap - timedelta(hours=1, minutes=51)), "end": iso(cap - timedelta(hours=1, minutes=9)),  "duration_s": 2520, "ip": "10.5.50.61"},
                    {"start": iso(cap - timedelta(hours=3, minutes=2)),  "end": iso(cap - timedelta(hours=1, minutes=56)), "duration_s": 3960, "ip": "10.5.50.204"},
                    {"start": iso(cap - timedelta(hours=4, minutes=30)), "end": iso(cap - timedelta(hours=3, minutes=8)),  "duration_s": 4920, "ip": "10.5.50.61"}
                ]
            },
            "radius": {
                "radcheck_exists": True,
                "username": "30:16:9D:A2:5F:03",
                "lineid_in_radius": "00:A1:07:C4:1D:88",
                "framed_pool": None,
                "assigned_ip": "10.5.50.204",
                "crm_consistent": False,
                "mismatches": [
                    {"type": "orphan_radcheck",
                     "detail": "A second radcheck row exists for username 30:16:9D:A2:5F:03 with lineid 1C:EF:03:90:2B:5A, which matches no active CRM customer. Two rows for one username; FreeRADIUS resolves whichever it reaches first."},
                    {"type": "lineid_conflict",
                     "detail": "The orphan row carries a different lineid to the CRM record, so sessions are attributed inconsistently between the two."}
                ]
            },
            "traffic": {
                "download_mb_daily": [820, 611, 905, 540, 738, 402, 690],
                "upload_mb_daily": [5120, 3980, 5640, 3210, 4770, 2560, 4390],
                "monthly_avg_download_mb": 871,
                "monthly_avg_upload_mb": 5533,
                "pon_port_traffic": {"current_mbps": 204, "avg_mbps": 211, "peak_mbps": 588}
            }
        },
        "ground_truth": {
            "fault_type": "session_flapping_auth",
            "root_cause": "Two radcheck rows exist for the same username. FreeRADIUS resolves inconsistently between them, so authentication succeeds or fails depending on which row is matched, producing repeated short sessions and two alternating IP assignments.",
            "severity": "Average",
            "affected_scope": "single_customer",
            "affected_lineids": ["00:A1:07:C4:1D:88"],
            "affected_customer_count": 1,
            "service_impact": True,
            "expected_reasoning": [
                "19 sessions in 24h against a 2-3 baseline, with a 38 minute mean duration against an 11.9 hour norm",
                "RX has been flat at -20.6 dBm for seven days inside the +/-0.3 dBm noise floor, so signal is not the cause",
                "TX power, bias current, supply voltage and distance are all stable",
                "Port neighbours are normal and the OLT is healthy, so no shared infrastructure fault",
                "With no optical explanation available, the search moves to the authentication layer",
                "RADIUS holds two radcheck rows for username 30:16:9D:A2:5F:03, one of them an orphan with a different lineid",
                "Recent sessions alternate between two IP addresses, consistent with inconsistent row resolution",
                "Traffic is erratic rather than declining, which fits intermittent authentication rather than a degrading link"
            ],
            "required_evidence": [
                "optical_layer_confirmed_clean",
                "duplicate_radcheck_identified",
                "alternating_ip_assignment"
            ],
            "expected_remediation": "manual_review",
            "expected_escalation": {
                "priority": "Average",
                "category": "provisioning",
                "requires_human_review": True,
                "review_reason": "Duplicate RADIUS rows must be resolved by hand; deleting the wrong row disconnects the customer"
            },
            "distractors": [
                "The session pattern is identical to signal-related flapping and invites that diagnosis",
                "Zero-throughput windows in the speed series look like link loss but coincide with rejected auth",
                "ONU is a Router type, inviting a CPE-fault explanation"
            ]
        }
    }


# ---------------------------------------------------------------- FC-001
def fc001():
    cap = datetime(2026, 9, 21, 19, 31, 34, tzinfo=timezone.utc)
    start = cap - timedelta(hours=H - 1)

    rx = flat(-19.84, 0.15)
    tx = flat(2.29, 0.040)
    temp = diurnal_temp(23.0, 1.7, 0.30)
    dist = [142] * H
    bias = flat(11.75, 0.15)
    volt = flat(3.43, 0.010)
    speed = [r2(max(0.05, random.gauss(5.2, 2.3))) for _ in range(H)]

    cpu = [int(max(0, min(48, random.gauss(22, 3)))) for _ in range(H)]
    mem = [int(max(0, min(76, random.gauss(19, 1.5)))) for _ in range(H)]
    otemp = [int(max(0, min(68, random.gauss(44, 2)))) for _ in range(H)]

    failed = [f"EPON0/{i}:1" for i in range(1, 8)]

    return {
        "metadata": {
            "scenario_id": "FC-001",
            "fault_type": "olt_health_false_critical",
            "difficulty": "easy",
            "captured_at": iso(cap),
            "description": "Health check reports all seven PONs failed on an OLT whose customers are online, authenticated and passing traffic; the ONU parameter OID subtree is absent on this firmware version.",
            "tests": [
                "Is an alarm verified before it is acted on?",
                "Is uniform non-response distinguished from a definite offline answer?",
                "Is a monitoring defect distinguished from a service outage?"
            ],
            "note": "subscriber holds a representative customer on the affected OLT, used for per-customer probes."
        },
        "trigger": {
            "type": "health_check_alarm",
            "input": {
                "olt_host": "TK_AF_OLT_OH_Bogomilska-05",
                "overall_status": "critical",
                "error_description": "All PONs failed (7/7)"
            }
        },
        "subscriber": {
            "customer_id": 14902,
            "lineid": "4C:46:D1:B8:03:2C",
            "mac": "50:0F:F5:D1:77:96",
            "interface": "EPON0/2:6",
            "olt_id": "10238",
            "olt_host": "TK_AF_OLT_OH_Bogomilska-05",
            "olt_ip": "10.220.57.6",
            "olt_technology": "EPON",
            "olt_model": "V1600D",
            "router_id": 9,
            "router_name": "TK_AZ_Ohrid_Bogomilska",
            "profile": "profile_20M",
            "active": 1,
            "deleted": 0,
            "onu_model": "Aztech 1G + CATV",
            "onu_type": "Bridge",
            "has_catv": 1,
            "has_voip": 0,
            "catv_service": 1,
            "catv_synced": 1,
            "city": "Ohrid",
            "area": "Bogomilska"
        },
        "network_state": {
            "onu_status": 1,
            "rx_power": "-19.84",
            "tx_power": "2.29",
            "reading_age_minutes": 22,
            "olt_health": {
                "olt_ip": "10.220.57.6",
                "olt_host": "TK_AF_OLT_OH_Bogomilska-05",
                "olt_technology": "EPON",
                "olt_ext_id": "10238",
                "ping_ok": True,
                "snmp_community_ok": True,
                "snmp_response_ok": True,
                "total_pons_tested": 7,
                "healthy_pons": 0,
                "failed_pons_list": failed,
                "error_description": "All PONs failed (7/7)",
                "overall_status": "critical",
                "run_date": "2026-09-21"
            },
            "olt_metrics": {
                "cpu_load": 22, "memory_usage": 19, "temperature": 44,
                "uptime_days": 61, "firmware": "V2.04.12R", "firmware_date": "2025-11-28"
            },
            "router_state": {
                "name": "TK_AZ_Ohrid_Bogomilska",
                "model": "CCR2004-1G-12S+2XS",
                "os_version": "7.24",
                "last_checkin": iso(cap - timedelta(minutes=6)),
                "hours_since_checkin": 0.1,
                "heartbeat_status": "ok",
                "cpu_usage": 5, "memory_utilization": 0, "temperature": 39
            }
        },
        "peers": {
            "interface_port": "EPON0/2",
            "crm_view": {
                "total_on_port": 26,
                "customers": [
                    {"lineid": "4C:D7:C8:2E:91:40", "interface": "EPON0/2:1",  "onu_status": 1, "rx_power": "-20.11", "active": 1},
                    {"lineid": "70:B6:4F:8A:16:D3", "interface": "EPON0/2:3",  "onu_status": 1, "rx_power": "-21.46", "active": 1},
                    {"lineid": "4C:46:D1:B8:03:2C", "interface": "EPON0/2:6",  "onu_status": 1, "rx_power": "-19.84", "active": 1},
                    {"lineid": "00:A1:07:50:C8:7B", "interface": "EPON0/2:10", "onu_status": 1, "rx_power": "-22.30", "active": 1},
                    {"lineid": "80:F1:A8:D4:62:09", "interface": "EPON0/2:15", "onu_status": 1, "rx_power": "-20.75", "active": 1},
                    {"lineid": "B4:64:15:39:AE:54", "interface": "EPON0/2:18", "onu_status": 0, "rx_power": "-21.02", "active": 1},
                    {"lineid": "78:88:8A:67:1F:B2", "interface": "EPON0/2:22", "onu_status": 1, "rx_power": "-19.58", "active": 1}
                ]
            },
            "olt_population": {
                "total_customers": 183,
                "pon_ports_in_use": 7,
                "customers_per_port": {"EPON0/1": 29, "EPON0/2": 26, "EPON0/3": 24,
                                       "EPON0/4": 31, "EPON0/5": 22, "EPON0/6": 28,
                                       "EPON0/7": 23},
                "onu_online_count": 174,
                "onu_offline_count": 9
            },
            "duplicate_slot_conflict": None
        },
        "telemetry": {
            "onu_series": {
                "interval": "1h", "window_hours": H, "series_start": iso(start),
                "rx_power": rx, "tx_power": tx, "temperature": temp,
                "distance": dist, "tx_bias_current": bias,
                "supply_voltage": volt, "speed_kbps": speed
            },
            "olt_series": {
                "interval": "1h", "window_hours": H, "series_start": iso(start),
                "cpu_load": cpu, "memory_usage": mem, "temperature": otemp
            },
            "availability": {"onu_series_complete": True, "gaps": []}
        },
        "snmp_live": {
            "onu": {"responds": False, "online": None, "rx_power": None, "tx_power": None,
                    "auth_flag": None, "exchange": None, "rtt_tq": None},
            "olt": {"ping_ok": True, "snmp_responds": True,
                    "sys_uptime_seconds": 5270400, "oid_subtree_responds": False},
            "pon_probe": {
                "interface_port": "EPON0/2",
                "onus": [
                    {"onu_index": 1,  "online": None, "rx_power": None, "tx_power": None, "responds": False},
                    {"onu_index": 3,  "online": None, "rx_power": None, "tx_power": None, "responds": False},
                    {"onu_index": 6,  "online": None, "rx_power": None, "tx_power": None, "responds": False},
                    {"onu_index": 10, "online": None, "rx_power": None, "tx_power": None, "responds": False},
                    {"onu_index": 15, "online": None, "rx_power": None, "tx_power": None, "responds": False},
                    {"onu_index": 18, "online": None, "rx_power": None, "tx_power": None, "responds": False},
                    {"onu_index": 22, "online": None, "rx_power": None, "tx_power": None, "responds": False}
                ]
            },
            "vlan_walk": {
                "responds": True,
                "vlans_present": [1, 46, 100, 1021, 1022, 1023, 1024, 1025, 1026, 1027, 1998, 1999],
                "customer_vlan_expected": 1022,
                "customer_vlan_actual": 1022
            }
        },
        "session_auth": {
            "sessions": {
                "count_24h": 2, "count_7d": 15, "avg_duration_minutes": 694,
                "last_disconnect": iso(cap - timedelta(hours=14, minutes=52)),
                "recent": [
                    {"start": iso(cap - timedelta(hours=14, minutes=48)), "end": None, "duration_s": 53280, "ip": "10.5.50.88"},
                    {"start": iso(cap - timedelta(hours=27, minutes=5)),  "end": iso(cap - timedelta(hours=14, minutes=52)), "duration_s": 43980, "ip": "10.5.50.88"}
                ]
            },
            "radius": {
                "radcheck_exists": True,
                "username": "50:0F:F5:D1:77:96",
                "lineid_in_radius": "4C:46:D1:B8:03:2C",
                "framed_pool": None,
                "assigned_ip": "10.5.50.88",
                "crm_consistent": True,
                "mismatches": []
            },
            "traffic": {
                "download_mb_daily": [905, 1120, 870, 1045, 960, 1180, 1015],
                "upload_mb_daily": [5880, 6740, 5510, 6320, 6010, 7180, 6450],
                "monthly_avg_download_mb": 1002,
                "monthly_avg_upload_mb": 6298,
                "pon_port_traffic": {"current_mbps": 231, "avg_mbps": 224, "peak_mbps": 702}
            }
        },
        "ground_truth": {
            "fault_type": "olt_health_false_critical",
            "root_cause": "The OLT firmware (V2.04.12R) does not expose the ONU parameter OID subtree the health check reads. Every sampled ONU returns no instance, the check marks all seven PONs failed and writes a critical status, while the OLT and all 183 customers are operating normally.",
            "severity": "Information",
            "affected_scope": "none",
            "affected_lineids": [],
            "affected_customer_count": 0,
            "service_impact": False,
            "expected_reasoning": [
                "Health check reports critical with all 7 of 7 PONs failed",
                "OLT ping succeeds and SNMP sysUpTime answers, with 61 days of uptime and no recent reboot",
                "OLT CPU 22%, memory 19% and temperature 44C are all at healthy baseline",
                "Live probe returns oid_subtree_responds false, and every ONU on the port returns responds false rather than online 0",
                "Uniform non-response means nothing answered; it is not a definite negative, so no ONU has been reported down",
                "CRM shows 174 of 183 ONUs online, and 9 offline matches the 4.85% network baseline",
                "The representative customer holds a session opened 14 hours ago and is passing normal daily traffic",
                "Cached optical readings are 22 minutes old and normal, and telemetry has been flat for seven days",
                "Healthy service with uniform probe non-response indicates an OID or firmware mismatch in the monitoring tool, not a network outage"
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
                "requires_human_review": True,
                "review_reason": "Health check produces false criticals on firmware V2.04.12R; the OID subtree it reads is absent on this version"
            },
            "distractors": [
                "The critical alarm invites an olt_failure or pon_port_failure diagnosis",
                "Nine genuinely offline ONUs on the OLT are unrelated background noise at the normal rate",
                "Firmware V2.04.12R differs from the estate norm V2.03.78R, which is the discriminator rather than a fault in itself"
            ]
        }
    }


out = "/mnt/user-data/outputs/scenarios"
os.makedirs(out, exist_ok=True)

for name, fn in [("FD-001-easy", fd001), ("SF-002-hard", sf002), ("FC-001-easy", fc001)]:
    obj = fn()
    with open(f"{out}/{name}.json", "w") as f:
        json.dump(obj, f, indent=2)
    print(f"wrote {name}.json")

# quick stats check on the noise floors
for name, fn in [("FD-001", fd001), ("SF-002", sf002), ("FC-001", fc001)]:
    o = fn()
    s = o["telemetry"]["onu_series"]
    rx24 = s["rx_power"][-24:]
    tx24 = s["tx_power"][-24:]
    print(f"{name}: RX last24 range {r2(max(rx24)-min(rx24))} dBm | "
          f"TX last24 range {r2(max(tx24)-min(tx24))} dBm | "
          f"series len {len(s['rx_power'])}")
