"""Measured thresholds for this network. Sources in docs/calibration.md."""

THRESHOLDS = """
Calibrated thresholds for this network (EPON only):
- RX power: strong > -20, normal -20 to -25, degraded -25 to -28, critical <= -28 dBm
- TX power: normal 0 to +5 dBm, mean +2.3. NOT -6 to -10; that documented value is wrong
  and would flag 92% of the estate.
- rx_power/tx_power of "0" or null mean NO READING, never a strong signal.
- The poller writes 0 for any value it cannot read. When the OLT does not answer SNMP,
  every stored onu_status, power and series value under it reads 0 and says nothing about
  the ONUs or the customers. A 0 in distance or supply voltage is never a measurement.
- Sessions: 2-3 per day is the normal re-auth baseline (80.8% of customers).
  4-7 is elevated. Flapping starts at 8+. Observed ceiling is 26.
- Mean session duration is 11.9 hours.
- ONU offline baseline across the network is 4.85%. On a 300-customer OLT,
  ~14 offline is normal background, not an outage.
- Router heartbeat: ok < 2h, warning 2-4h, danger > 4h, never = no record ever.
- OLT healthy baseline: CPU ~25%, memory ~17%, temperature ~42C.
- Healthy optical noise floor over 24h: RX +/-0.3 dBm, TX +/-0.08 dBm.
  Anything wider is a real change.
- Distance is constant per customer. A step change means the fibre path changed.
- TX bias current 9.5-13.0 mA healthy. Rising bias at constant TX power = laser ageing.
"""
