"""Monolithic baseline prompt. One call, no tools, no stages.

Carries the same fault_type enum and the same calibrated thresholds as the pipeline, so
the comparison measures diagnosis rather than whether the baseline guesses our label
vocabulary or our bands. It does NOT carry the diagnosis agent's discriminator rules —
those are the reasoning the pipeline supplies, and handing them over would erase the
difference being measured.
"""

FAULT_TYPES = [
    "fiber_degradation", "laser_degradation", "distance_change", "onu_offline",
    "pon_port_failure", "splitter_failure", "olt_failure", "olt_health_false_critical",
    "router_unreachable", "radius_missing_entry", "radius_suspended_but_serving",
    "radius_lineid_conflict", "radius_replication_lag", "session_flapping_signal",
    "session_flapping_auth", "duplicate_onu_slot", "stuck_provisioning_vlan46",
    "catv_drift", "pon_congestion", "no_fault",
]

# Sections handed to the baseline. metadata is excluded: it holds fault_type, a
# description naming the fault and a tests list naming the discriminators. tools.py never
# exposes it either, so excluding it is also what matches the agents' view.
SECTIONS = ["trigger", "subscriber", "network_state", "peers", "telemetry",
            "snmp_live", "session_auth"]
# What a single call could hold without acting: everything except the live device probes.
STORED_SECTIONS = [s for s in SECTIONS if s != "snmp_live"]

DESCRIBE = {"trigger": "the trigger that raised it", "subscriber": "the subscriber record",
            "network_state": "current stored network state",
            "peers": "the customers on the same PON port", "telemetry": "seven days of telemetry",
            "snmp_live": "live device probe results",
            "session_auth": "session and authentication state"}

# Same closed vocabularies the pipeline's remediation and escalation agents answer in.
CATEGORIES = ["field_service", "infrastructure", "provisioning", "monitoring", "noc"]
PRIORITIES = ["Not classified", "Information", "Warning", "Average", "High", "Disaster"]


def between(text: str, start: str, end: str) -> str:
    i, j = text.find(start), text.find(end)
    assert i != -1 and j > i, f"markers not found: {start!r} .. {end!r}"
    return text[i:j].strip()


# Boundaries of the discriminator block inside the live DIAGNOSIS prompt. Sliced at run
# time rather than copied, so the shared-knowledge baseline cannot drift from the agent.
DISC_START = "Discriminators that separate look-alike faults:"
DISC_END = "Verify before you conclude."


def discriminators(diagnosis_prompt: str) -> str:
    i, j = diagnosis_prompt.find(DISC_START), diagnosis_prompt.find(DISC_END)
    assert i != -1 and j > i, "discriminator block markers not found in DIAGNOSIS"
    return diagnosis_prompt[i:j].rstrip()


def build(scenario: dict, thresholds: str, actions: list[str], shared: str = "",
          sections: list[str] = SECTIONS) -> str:
    import json
    data = {k: scenario[k] for k in sections if k in scenario}
    held = [DESCRIBE[k] for k in sections]
    held = ", ".join(held[:-1]) + ", and " + held[-1]
    shared = f"\n{shared}\n" if shared else ""

    def wrap(xs):
        return "\n".join("  " + " ".join(xs[i:i + 4]) for i in range(0, len(xs), 4))

    return f"""You are a network fault diagnosis system for an EPON ISP.

Below is everything known about one case: {held}.

Work out what is wrong, what should be done about it, and how it should be escalated.

{thresholds}
{shared}
fault_type must be exactly one of these, copied character for character. It is a closed
list; never invent a label, reword one, or describe the fault in this field:
{wrap(FAULT_TYPES)}

Choose the closest member of that list even when you are unsure, and carry your
uncertainty in confidence. Use no_fault only when every reading has a normal explanation.

action must be exactly one of these, copied character for character:
{wrap(actions)}

priority is the Zabbix six-level scale. category is one of: {", ".join(CATEGORIES)}.
affected_scope says how far the evidence reaches. service_impact says whether customers
are actually losing service, separately from priority.

Case data:
{json.dumps(data, indent=2)}

Reply with JSON only:
{{
  "fault_type": "one of the listed values",
  "root_cause": "...",
  "confidence": 0.0-1.0,
  "affected_scope": "none"|"single_customer"|"pon_port"|"olt"|"router"|"multi_customer",
  "action": "one of the listed actions",
  "priority": {"|".join(f'"{p}"' for p in PRIORITIES)},
  "category": {"|".join(f'"{c}"' for c in CATEGORIES)},
  "requires_human_review": true|false,
  "review_reason": "..." or null,
  "affected_customer_count": 0,
  "service_impact": true|false,
  "reasoning": ["each step that led to the conclusion"]
}}"""


# View-agnostic restatement of the agent's discriminator block. Same diagnostic content,
# same thresholds, same precedence; every reference to tools, probing, fetching, partial
# views, not_held replies and "the port view you can see" removed. The discriminators are
# stated in terms of what the data shows rather than how it was obtained, so a reader
# holding the whole payload is not told about the limits of an interface it does not use.
CLEAN_DISCRIMINATORS = """Discriminators that separate look-alike faults:
- RX falling, bias flat -> fibre degradation. Bias rising, RX flat -> laser degradation.
- Distance does not drift; it is the geometry of the fibre run. A step in distance means
  the path behind it, or the record pointing at it, changed, and that is the fault. RX
  moving with the step is a consequence of the new path, not a separate degradation.
  Degradation is RX falling while distance holds constant.
- The shape of the trend decides first, and the session count only arbitrates afterwards.
  A decline is a trend that starts inside the normal band and ends outside it: RX in the
  normal band at the start of the window, degraded or critical at the end. A declining link
  is degrading however often its sessions drop, and the disconnects are a symptom of the
  decline rather than a fault beside it. A trend that already begins in the degraded band
  has not declined, whatever its endpoint and however wide its spread; that is a link which
  was marginal to begin with, swinging in and out of usable range. Only there does the
  count decide: at 8+ in 24h the sessions are flapping and the swing explains them, while
  at 7 or fewer they are not flapping at all and no flapping diagnosis is available, so the
  oscillation belongs to the fibre path.
- Peers on the port normal -> fault is this customer's own path.
  Peers also affected -> shared infrastructure.
- Whole port down -> PON port failure. Two or more down with survivors on the same port ->
  splitter failure. Exactly one down among healthy peers -> that one ONU is offline; nothing
  shared has failed, because a shared element takes at least two customers with it.
- Other ports healthy -> not the OLT. An OLT failure means the OLT itself stopped
  answering: ping fails, or ping succeeds while SNMP does not. An OLT whose own ping and
  SNMP both succeed while its ONUs read as definite negatives has failed ports, not a
  failed OLT, however many ports are involved.
- fault_type names what failed; affected_scope names how far it reaches. The two move
  independently, so a port failure that spans every port on a device is still a port
  failure, reported at olt scope.
- responds:true with online:0 is a DEFINITE offline answer.
  responds:false means nothing answered at all. These lead to opposite conclusions.
- An ONU that is a definite negative now is offline, and that is the fault. A decline
  running up to the dropout attributes the cause of it; it does not replace the fault
  with a degradation that is still in progress.
- Uniform responds:false across the ONUs on a port, while ping and SNMP both succeed and
  customers are online and passing traffic, means the monitoring is broken, not the
  network. Two converses matter as much: if SNMP itself does not answer, the OLT is
  failing and the alarm is real; and if the ONUs read online:0, the outage is real however
  the alarm happens to be worded.
- A summary status field that contradicts the detail fields in its own record is a
  monitoring defect whichever way it points, but how far it points decides which fault it
  is. A critical label over healthy detail is a false alarm and the check is at fault. A
  healthy label has to be read against how much it conceals: when every tested PON, or all
  but one, is marked failed, the status rule itself is the defect and the health check is
  the fault; when only a minority are marked failed and most are healthy, the label is
  concealing a genuine outage on those ports and the fault is that port failure, not the
  monitoring. Where the check is the fault, the service impact underneath is carried in
  scope and severity, not in fault_type.
- Blast radius comes from the online values of the ONUs on the affected port.
- That mix of online values is direct evidence and outranks any estimate drawn from
  population counts. Where two or more ONUs on the port read as definite negatives while
  others read online, the boundary falls inside the port and it is a splitter failure,
  whatever the offline total looks like beside the port's population. A single definite
  negative among healthy peers does not reach that boundary and is one ONU offline. Only where no per-ONU readings
  exist for a port can the radius be sized indirectly: then read the offline total in the
  OLT population against the per-port counts, where a count close to one port's population
  is a port failure, one close to the whole OLT is OLT-wide, and one near the 4.85%
  baseline is background. An OLT-wide offline total never turns a port with surviving ONUs
  into a whole-port failure.
- Flapping with degraded RX -> signal. Flapping with clean optics -> the cause is in
  authentication. Reconnects that keep succeeding mean authentication works and something
  is ending the sessions: a per-user RADIUS reply attribute such as Session-Timeout cuts
  every session at the same length, so durations that are all alike point to a timer, not
  to line loss. At 8+ in 24h, with durations far short of the 11.9 hour mean, the flapping
  is the fault: name the flapping and put the attribute in root_cause.
- A RADIUS defect that rejects a customer does not flap. The customer stops
  authenticating and stays down: a healthy physical layer with no session since a point in
  time is an authentication failure, not intermittency.
- Healthy physical layer with no service: the RADIUS entry explains it, and which fault it
  is depends on where the entry is wrong. No radcheck row is a missing entry. A row whose
  lineid differs from the ONU that CRM records as installed is a lineid conflict: Line ID
  is checked at authentication, so the customer is rejected at the next DHCP exchange. A
  row that is current on the primary RADIUS server but stale on the secondary is
  replication lag: it rejects the customer once the MikroTik fails over to the secondary,
  and only comparing both servers reveals it. Failing all three, the VLAN
  (46 = factory default, never provisioned).
- CRM inactive but IP in 10.5.50.0/24 -> suspended but still being served.
- A stored health record older than a few days describes history, not current state."""

# Guard: nothing in the clean block may refer to how data is obtained.
# "in scope" is banned only as a view limit ("the port in scope"), not where scope is the
# output field ("carried in scope and severity").
_BANNED = ["prob", "not_held", "you can see", "port in scope", "record in scope",
           "is held", "not held", "fetch", "tool", "call the", "every query"]
_hits = [w for w in _BANNED if w in CLEAN_DISCRIMINATORS.lower()]
assert not _hits, f"view-dependent wording left in CLEAN_DISCRIMINATORS: {_hits}"
