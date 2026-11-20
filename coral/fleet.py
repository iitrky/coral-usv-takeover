"""
Remote-operation-centre (ROC) queue simulator for a satellite-supervised USV fleet.

K vessels emit encounter assessments as a Poisson stream (rate r_e per vessel).
TAKEOVER requests enter a queue served by M operators. Service time depends on the
measured link (uplink of the situational picture + 2 RTT + human assessment time).
If a request is not resolved before its timeout (estimated TCPA - T_man) the vessel
executes a minimum-risk manoeuvre (MRM). A hazardous encounter is UNSAFE if it was
auto-cleared (PROCEED) or if neither the operator nor the MRM acted before
(true time-to-violation - T_man).
"""
import heapq
import numpy as np
from .conformal import PROCEED, TAKEOVER, AVOID, service_time


def simulate(decisions, y, tcpa_true, est_tcpa, bw, rtt, rng, K=24, M_ops=2, r_e=1 / 60.0,
             T_man=30.0, priority="urgency", tau_h_median=20.0, tau_h_sigma=0.4, return_arrays=False):
    n = len(y)
    order = rng.permutation(n)
    gaps = rng.exponential(1.0 / (K * r_e), n)
    t_arr = np.cumsum(gaps)
    tau_h = tau_h_median * np.exp(rng.normal(0, tau_h_sigma, n))
    svc = service_time(bw, rtt, tau_h=0.0) + tau_h
    timeout = np.maximum(est_tcpa - T_man, 10.0)

    free_at = [0.0] * M_ops
    heapq.heapify(free_at)
    queue = []           # (priority key, arrival time, idx)
    resolve = np.full(n, np.nan)
    mrm = np.zeros(n, bool)
    busy = 0.0
    waits = []
    # event-driven: process arrivals in time order, serving queue when operators free
    pending = [(t_arr[k], order[k]) for k in range(n) if decisions[order[k]] == TAKEOVER]

    def key(i, ta):
        return (est_tcpa[i] + ta) if priority == "urgency" else ta

    pi = 0
    now = 0.0
    while pi < len(pending) or queue:
        next_free = free_at[0]
        if queue and (pi >= len(pending) or next_free <= pending[pi][0]):
            # an operator becomes free before next arrival: serve best queued request
            start = max(next_free, now)
            # admit any arrivals up to start
            while pi < len(pending) and pending[pi][0] <= start:
                ta, i = pending[pi]
                heapq.heappush(queue, (key(i, ta), ta, i)); pi += 1
            _, ta, i = heapq.heappop(queue)
            if start - ta >= timeout[i]:      # already timed out while waiting -> MRM
                resolve[i] = ta + timeout[i]
                mrm[i] = True
                waits.append(timeout[i])
                continue
            heapq.heappop(free_at)
            done = start + svc[i]
            if done - ta > timeout[i]:        # operator too slow -> MRM fires at timeout
                resolve[i] = ta + timeout[i]
                mrm[i] = True
                end = ta + timeout[i]
            else:
                resolve[i] = done
                end = done
            busy += end - start
            heapq.heappush(free_at, end)
            waits.append(start - ta)
            now = start
        else:
            ta, i = pending[pi]; pi += 1
            heapq.heappush(queue, (key(i, ta), ta, i))
            now = ta

    span = t_arr[-1] if n else 1.0
    t_res = np.full(n, np.inf)
    arr_of = np.empty(n); arr_of[order] = t_arr
    tk = decisions == TAKEOVER
    t_res[tk] = resolve[tk] - arr_of[tk]
    deadline = tcpa_true - T_man
    hz = y == 1
    unsafe = hz & ((decisions == PROCEED) | (tk & (t_res > deadline)))
    out = dict(
        unsafe_rate=float(unsafe.sum() / max(1, hz.sum())),
        auto_clear_miss=float((hz & (decisions == PROCEED)).sum() / max(1, hz.sum())),
        late_takeover_hazard=float((hz & tk & (t_res > deadline)).sum() / max(1, hz.sum())),
        false_manoeuvre=float(((y == 0) & (decisions == AVOID)).sum() / max(1, (y == 0).sum())),
        takeover_rate=float(tk.mean()),
        mrm_rate=float(mrm.sum() / max(1, tk.sum())),
        mrm_per_hour=float(mrm.sum() / (span / 3600.0)),
        utilisation=float(busy / (M_ops * span)),
        mean_wait=float(np.mean(waits)) if waits else 0.0,
        wait_q90=float(np.quantile(waits, 0.9)) if waits else 0.0,
        autonomy=float(1.0 - tk.mean()),
    )
    if return_arrays:
        out = dict(out)
        out['_unsafe'] = unsafe
        out['_late'] = hz & tk & (t_res > deadline)
        out['_t_res'] = t_res
    return out
