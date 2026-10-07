# Hypotheses

Approved and frozen 7 Oct 2026, before the full runs (plan step 7). Do not edit after step 7 starts.

H1–H4 were set in `docs/final-plan.md` before any run on the current code. The
operational definitions below were written after the 5-scenario smoke runs (same day),
before any full run. The smoke split is part of the 35 and is not excluded.

## Comparisons

All comparisons are within one model, across the 35 scenarios, using the same repetitions
for every configuration of that model.

- `agent` vs `monolithic_stored`: does the specialised system beat a single prompt?
- `agent` vs `monolithic_shared_stored`: is it the architecture or the knowledge?

## Outcomes

- **Case correct** (primary): `fault_type`, `remediation` and `priority` all
  correct. `fault_type` alone hit the ceiling in the smoke runs (5/5 for both monoliths),
  so it cannot separate the configurations on its own.
- Secondary: each deterministic field separately, `priority_distance`,
  `evidence_coverage`, `unsupported_claims`.
- Cost: tokens and USD per run, from LangSmith.
- Consistency: share of scenarios whose `fault_type` and `remediation` are identical in
  all 3 repetitions.

## Hypotheses

**H1.** On `gpt-5.6-luna`, `agent` has a higher case-correct rate than
`monolithic_stored`, and the gap is larger on hard scenarios than on easy ones.
Difficulty is the `metadata.difficulty` label (9 easy, 13 medium, 13 hard), which is
structural (`docs/scenario-schema.md`), not set from results.

**H2.** Against `monolithic_shared_stored` (equal knowledge), the gap narrows, and what
remains is concentrated in scenarios that need live verification.
"Needs live verification": at least one `required_evidence` item can only be
established from `snmp_live`. The list of scenarios is fixed from the scenario files
before the full runs and recorded below.

**H3.** Both monoliths cost less per run than `agent`, and are more consistent across the
3 repetitions.

**H4.** The `agent` − `monolithic_stored` gap in case-correct rate is smaller on
`gpt-6-luna` than on `gpt-5.6-luna`.

## Decision rule

- Paired comparison per scenario (same scenario, two configurations): McNemar test on
  case correct, plus a bootstrap 95% CI on the difference (analysis A1, if approved).
- With 35 scenarios, a difference is reported as supported only if the CI excludes 0.
  Otherwise it is reported as a direction, not a result.
- `gpt-5.4-nano` is single-run: its differences smaller than the run-to-run variation
  measured on luna are inconclusive. `gpt-5.6-luna` and `gpt-6-luna` get 3 repetitions.

## Scenarios needing live verification

Fixed 7 Oct 2026 from the scenario files only (`required_evidence` checked against what the
stored sections contain). The deciding item is the one only `snmp_live` holds.

| Scenario | Difficulty | Live-only item |
|---|---|---|
| DS-001 | medium | `live_probe_returns_one_device` |
| DS-002 | hard | `probe_mac_matches_no_record` |
| FC-001 | easy | `oid_subtree_non_response_is_uniform` |
| FC-002 | hard | `definite_offline_not_no_response` |
| FC-004 | hard | `live_probe_contradicts_record` |
| FD-002 | medium | `cached_live_discrepancy` |
| OO-001 | easy | `definite_offline_not_no_response` |
| OO-002 | medium | `definite_offline_not_no_response` |
| OO-003 | hard | `olt_alarm_contradicted_by_probe` |
| PP-003 | hard | `definite_offline_not_no_response`, `oid_subtree_responds_true` |
| SV-001 | medium | `vlan_walk_shows_46` |
| SV-002 | hard | `vlan_walk_shows_46` |

12 need live verification; the other 23 can be settled from stored data.

Checked and not live-only: FC-003, PP-001, PP-002, SP-001 (the port's state is in
`peers.crm_view`), OF-001, OF-002 (ping and SNMP results are in `network_state.olt_health`).

DS-002 was first on the stored side, only because its stored
`peers.duplicate_slot_conflict.detail` stated the live result. That sentence was removed
before the full runs (`docs/scenario-changelog.md`, 7 Oct), which puts DS-002 on the live side.
