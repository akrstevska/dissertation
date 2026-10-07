# Scenario changelog

## October 2026 — network engineer review

All 35 scenarios were reviewed by a network engineer at the ISP for realism. He confirmed
29 without change. In 3 the fault mechanism was not realistic, 2 broke a data convention,
and 1 got an added note. Applied with `scenarios/generators/fix_engineer_review.py`.
All 35 validate.

| Scenario | Engineer's finding | Change | Ground truth effect |
|---|---|---|---|
| SF-002 | `radcheck.username` has a unique index, so two rows for one username are near-impossible. Even if they existed, FreeRADIUS rejects outright instead of picking one. | New mechanism: a per-user `Session-Timeout := 4500` in `radreply`, written at a profile change. The session ends every 75 min and the customer reconnects within a minute. Durations are uniform, and reconnects succeed. | Same fault type and remediation. New required evidence: `uniform_session_durations`, `session_timeout_in_radreply`. |
| RA-004 | Replication lag does not cause repeated disconnection. On failover to an unsynced secondary, the customer cannot authenticate at all. | The primary stops answering, and the MikroTik fails over to a secondary holding a pre-password-change row. At the customer's next re-auth they are rejected and stay down. Normal session history before that, nothing after. | Same fault type, severity and remediation. Required evidence `session_outcome_correlates_with_server` replaced by `outage_began_after_failover`. |
| RA-003 | Line ID is an authentication parameter. A CRM/RADIUS mismatch disables the user at the next DHCP exchange, so they lose service. | The premise is reversed: the ONU swap is moved to the day before, and the customer has been rejected since. The complaint is now "no internet". | Severity Warning → **Average**. service_impact false → **true**. `authentication_still_succeeds` replaced by `no_session_since_swap`. |
| OF-002 | When the OLT does not answer SNMP, the poller writes 0, so every ONU shows offline. | Stored status, powers, peers and population are all 0 (0/167 online). ONU and OLT telemetry is 0 from the failure hour. Ping, sessions and traffic are unchanged. | Same answer (olt_failure, Warning, no service impact). `telemetry_stopped_at_same_time` replaced by `stored_zeros_are_no_reading`. **Harder:** stored data now looks like OF-001. |
| OF-001 | Same convention. | Telemetry goes to 0 instead of null at the failure hour, and the reading is no longer "stale". Also fixed a defect: OLT CPU, memory and temperature read about 0 for all seven days, although the OLT failed two hours ago. | Reasoning line on staleness reworded. Answer unchanged. |
| RU-001 | Fine. If OLT management runs through the same MikroTik, the OLTs would be unreachable too. | Reasoning line added: OLT management is reachable here, so it does not route through this BNG. | None. |

### Severity consistency correction (7 October 2026)

| Scenario | Change | Reason |
|---|---|---|
| DC-002 | severity and priority Average → **Warning** | RX ends at −26.5 dBm, inside the degraded band, and the customer is still connected (8 sessions in 24h). The severity model (`docs/scenario-schema.md` §12) defines Warning as "degradation, service still usable" and Average as "single customer out of service". FD-001, the same situation at −26.4 dBm, is Warning. |
| SF-002 | severity and priority Average → **Warning** | When the mechanism was rewritten (75-minute session timer, reconnect within a minute), the severity was carried over from the old mechanism instead of being re-derived. Service is interrupted but usable, so it is Warning, consistent with SF-001 (signal flapping, Warning). |

Disclosure: in a 5-scenario smoke test every system answered Warning for both, and that is how the
inconsistency was noticed. The correction follows the documented severity model and the matching
scenarios, not the scores. It was made before the final evaluation runs, with the author's approval.

### Knowledge corrected alongside the scenarios

The pipeline and the baselines were taught the same wrong mechanisms. They were corrected
so the systems are not tested against facts they were taught wrong. All corrections are
general rules, with no scenario-specific hints.

- `pipeline/prompts/diagnosis_prompt.py` and `baseline/prompt_template.py` (clean
  discriminators): the auth rules are rewritten. Duplicate rows and lag-as-flapping are
  removed. The new rules are: flapping with succeeding reconnects means a reply attribute
  is ending the sessions; RADIUS rejection does not flap; and no-service faults are told
  apart by where the row is wrong (missing / wrong lineid / stale on the secondary). The
  shared baseline slices this block from the diagnosis prompt, so it follows
  automatically.
- `pipeline/prompts/thresholds.py`: the poller writes 0 for values it cannot read.
- `pipeline/prompts/remediation_prompt.py`: auth-related flapping → `manual_review`.
- `docs/fault-taxonomy.md` §3.7, §3.9, §3.12, §3.13, §3.15 and the tables;
  `docs/scenario-schema.md` §6.
- `scenarios/validate_scenarios.py`: plausibility checks skip 0 like null.

### Consequence for results

All results produced before this date use the old scenarios and the old prompts. They are
superseded, and the full evaluation is re-run on the corrected set.
