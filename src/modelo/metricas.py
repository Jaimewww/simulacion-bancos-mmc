"""Observed metrics contract — Alex, task C1.

Consume client records and DES time integrals, not view samples.
Compute per-level waits, time-average queues and busy teller fraction.
Record window boundaries and pending clients; draining must not extend
window denominators. Little's law is an asymptotic consistency check,
not an exact finite-horizon assertion.
"""
