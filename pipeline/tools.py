"""Tool layer. Signatures match what the MCP servers will expose."""
import json
import threading
from pathlib import Path
from langchain_core.tools import tool

SCENARIOS = Path(__file__).parent.parent / "scenarios"
_local = threading.local()  # one scenario per worker thread


def load(scenario_id: str):
    """Load a scenario by id, e.g. FD-001."""
    hits = list(SCENARIOS.glob(f"{scenario_id}-*.json"))
    if not hits:
        raise FileNotFoundError(scenario_id)
    _local.s = json.loads(hits[0].read_text())
    return _local.s


def current() -> dict:
    return getattr(_local, "s", {})


def _sec(name: str) -> dict:
    return current().get(name, {})


def summarise(series: list) -> dict:
    """Trend summary instead of raw arrays. Keeps agent context small."""
    vals = [v for v in series if v is not None]
    if not vals:
        return {"available": False}
    n = len(vals)
    return {
        "available": True,
        "points": n,
        "first": vals[0],
        "last": vals[-1],
        "min": min(vals),
        "max": max(vals),
        "mean": round(sum(vals) / n, 2),
        "range": round(max(vals) - min(vals), 2),
        "change": round(vals[-1] - vals[0], 2),
        "gaps": len(series) - n,
    }


# --- network data ---------------------------------------------------------

@tool
def get_customer_by_lineid(lineid: str = "") -> str:
    """Subscriber record: identity, interface, OLT, router, profile, ONU model,
    service flags and whether CRM marks the line active. Pass the lineid from the
    trigger; pass an empty string when the trigger carries no lineid and you want the
    record in scope for this investigation. Only the record in scope is held: any other
    lineid returns not_held, which is a limit of this view and says nothing about that
    customer."""
    sub = _sec("subscriber")
    if not lineid or sub.get("lineid") == lineid:
        return json.dumps(sub)
    return json.dumps({"error": "not_held", "lineid_in_scope": sub.get("lineid")})


@tool
def get_onu_status_cached(lineid: str) -> str:
    """Cached ONU status and optical power. May be stale; '0' and null mean no reading."""
    ns = _sec("network_state")
    return json.dumps({
        "onu_status": ns.get("onu_status"),
        "rx_power": ns.get("rx_power"),
        "tx_power": ns.get("tx_power"),
        "reading_age_minutes": ns.get("reading_age_minutes"),
    })


@tool
def get_olt_health(olt_id: str = "") -> str:
    """Last OLT health check result. The checker reports critical only when every
    sampled PON failed, so overall_status and failed_pons_list can disagree; read
    both, and read ping_ok and snmp_response_ok separately."""
    return json.dumps(_sec("network_state").get("olt_health", {}))


@tool
def get_olt_metrics(olt_id: str) -> str:
    """OLT CPU, memory, temperature, uptime, firmware."""
    return json.dumps(_sec("network_state").get("olt_metrics", {}))


@tool
def get_router_status(router_id: int = 0) -> str:
    """Router heartbeat. ok <2h, warning 2-4h, danger >4h. heartbeat_status "never"
    with last_checkin null means no check-in was ever recorded, which is an absent
    monitoring record rather than a router that went down."""
    return json.dumps(_sec("network_state").get("router_state", {}))


@tool
def get_customers_on_interface(olt_id: str = "", interface: str = "") -> str:
    """CRM view of one PON port: who is recorded on it and their cached status.
    Only the port in scope for this investigation is held. Asking for a different port
    returns not_held, which says nothing about that port's health. Leave interface
    empty to get the port in scope. Use it to see whether peers share the problem and
    to find lineids when the trigger names only an OLT. duplicate_slot_conflict is
    non-null when two subscriber records claim the same ONU slot on the port; that is
    always a provisioning conflict, never background."""
    p = _sec("peers")
    port = p.get("interface_port")
    if interface and str(interface).split(":")[0] != str(port).split(":")[0]:
        return json.dumps({"error": "not_held", "port_in_scope": port})
    return json.dumps({
        "interface_port": p.get("interface_port"),
        "crm_view": p.get("crm_view"),
        "duplicate_slot_conflict": p.get("duplicate_slot_conflict"),
    })


@tool
def get_olt_population(olt_id: str = "") -> str:
    """Customer counts per port and online/offline totals for the OLT.
    Compare the offline share against the 4.85% network baseline before calling it
    an outage."""
    return json.dumps(_sec("peers").get("olt_population", {}))


# --- telemetry ------------------------------------------------------------

@tool
def get_optical_series(lineid: str = "", signal: str = "all") -> str:
    """Trend summary of ONU telemetry over 7 days.
    signal: all | rx_power | tx_power | temperature | distance |
            tx_bias_current | supply_voltage | speed_kbps"""
    s = _sec("telemetry").get("onu_series", {})
    keys = ["rx_power", "tx_power", "temperature", "distance",
            "tx_bias_current", "supply_voltage", "speed_kbps"]
    want = keys if signal == "all" else [signal]
    return json.dumps({
        "window_hours": s.get("window_hours"),
        "signals": {k: summarise(s.get(k, [])) for k in want if k in s},
    })


@tool
def get_optical_series_raw(lineid: str, signal: str, last_n: int = 48) -> str:
    """Raw telemetry points for one signal. Use only when the summary is not enough."""
    s = _sec("telemetry").get("onu_series", {})
    return json.dumps({"signal": signal, "values": s.get(signal, [])[-last_n:]})


@tool
def get_olt_series(olt_id: str) -> str:
    """Trend summary of OLT CPU, memory and temperature over 7 days."""
    s = _sec("telemetry").get("olt_series", {})
    return json.dumps({k: summarise(s.get(k, [])) for k in
                       ("cpu_load", "memory_usage", "temperature")})


# --- device probe ---------------------------------------------------------

@tool
def snmp_get_onu(lineid: str) -> str:
    """Live SNMP read of one ONU. responds:false means nothing answered;
    online:0 means the OLT reported it down. These are different."""
    return json.dumps(_sec("snmp_live").get("onu", {}))


@tool
def snmp_probe_olt(olt_id: str) -> str:
    """Live OLT reachability: ping, SNMP, uptime, whether the ONU OID subtree answers."""
    return json.dumps(_sec("snmp_live").get("olt", {}))


@tool
def snmp_probe_pon_port(olt_id: str, interface: str = "") -> str:
    """Live status of every ONU on a PON port. This is how blast radius is established:
    read the online value of each ONU returned and see whether the whole port is down or
    only part of it. Only the port in scope for this investigation is held. Asking for a
    different port returns not_held, which is a limit of this view and says nothing about
    that port's health. Leave interface empty to get the port in scope."""
    p = _sec("snmp_live").get("pon_probe", {})
    port = p.get("interface_port")
    if interface and str(interface).split(":")[0] != str(port).split(":")[0]:
        return json.dumps({"error": "not_held", "port_in_scope": port})
    return json.dumps(p)


@tool
def snmp_walk_vlans(olt_id: str) -> str:
    """VLAN table against the expected plan. 46 = factory default, unprovisioned."""
    return json.dumps(_sec("snmp_live").get("vlan_walk", {}))


# --- session and auth -----------------------------------------------------

@tool
def get_sessions(lineid: str = "") -> str:
    """Session counts and recent history. count_24h of 2-3 is the normal re-auth
    baseline, 4-7 elevated, 8+ flapping. avg_duration_minutes near 714 (11.9h) is
    normal; much shorter means sessions are being cut short. Zero sessions on an
    active line means the customer has never been served."""
    return json.dumps(_sec("session_auth").get("sessions", {}))


@tool
def get_radius_status(lineid: str) -> str:
    """RADIUS entry, framed pool, assigned IP and any CRM mismatches.
    10.200.200.0/24 = suspended, 10.5.50.0/24 = standard service."""
    return json.dumps(_sec("session_auth").get("radius", {}))


@tool
def get_traffic(lineid: str = "") -> str:
    """Daily traffic and PON port utilisation. Direction labels are inverted in the
    source, so upload_mb_daily is really the download figure. pon_port_traffic
    current_mbps near peak_mbps means the port is saturated."""
    return json.dumps(_sec("session_auth").get("traffic", {}))


DETECTION_TOOLS = [
    get_customer_by_lineid, get_onu_status_cached, get_olt_health,
    get_olt_metrics, get_router_status, get_customers_on_interface,
    get_olt_population, get_sessions, get_traffic, get_optical_series,
]

DIAGNOSIS_TOOLS = [
    snmp_get_onu, snmp_probe_olt, snmp_probe_pon_port, snmp_walk_vlans,
    get_optical_series, get_optical_series_raw, get_olt_series,
    get_radius_status, get_sessions, get_customers_on_interface,
    get_olt_population,
]
