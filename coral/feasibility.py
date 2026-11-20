"""
CORAL-F: queue-state-conditioned conformal feasibility certificates for takeover requests.

At the moment a TAKEOVER request is raised, the ROC knows its live state (operator residual
busy times, queued work). CORAL-F forms two conformal bounds per request:

  U_i = q_R * ( W0_i + s_i )             upper bound on time-to-resolution  (Eq. 32-33)
        W0_i = (sum_m (f_m - t_i)^+ + sum_{j in Q(t_i)} s_j) / M      fluid backlog wait
        s_i  = tau_h,med + 8 S / B_i + 2 RTT_i                         nominal service time
  L_i = t_hat_i - T_man - q_D            lower bound on the true action deadline (Eq. 34)

q_R is the conformal (1-delta_R) quantile of the ratio e_R = T_res / (W0 + s) on calibration
requests, and q_D the Mondrian conformal (1-delta_D) quantile of e_D = t_hat - t* on the calibration
hazards that fall in the TAKEOVER band. A feasible request is queued with the certified timeout
min(T_out, L_i), so an unanswered hazard triggers the MRM before its true deadline w.p. >= 1-delta_D.
A request is *certified feasible* iff U_i <= L_i; otherwise it is routed to AVOID at once
(autonomous manoeuvre) instead of being queued for an operator who cannot answer in time.

Online variant: q_R and q_D are updated with an adaptive-conformal (ACI) step on each delayed
feedback (Eq. 37-38), which keeps long-run miscoverage at delta under distribution shift.
"""
import heapq
import numpy as np
from .conformal import PROCEED, TAKEOVER, AVOID, service_time


def conformal_quantile(x, delta):
    x = np.sort(np.asarray(x, float))
    n = len(x)
    if n == 0:
        return np.inf
    k = int(np.ceil((n + 1) * (1 - delta)))
    return np.inf if k > n else float(x[k - 1])


def simulate_f(decisions, y, tcpa_true, est_tcpa, bw, rtt, rng, K=24, M_ops=2, r_e=1 / 60.0,
               T_man=30.0, priority="urgency", tau_h_median=20.0, tau_h_sigma=0.4,
               cert=None, route=True, mode="route", online=False, eta_R=0.1, eta_D=5.0, delay=50, return_arrays=False):
    """Queue simulator identical to fleet.simulate, plus the CORAL-F certificate.
    cert = dict(qR=..., qD=..., dR=..., dD=...) or None (no certificate).
    route=False computes certificates (audit) without acting on them."""
    n = len(y)
    order = rng.permutation(n)
    gaps = rng.exponential(1.0 / (K * r_e), n)
    t_arr = np.cumsum(gaps)
    tau_h = tau_h_median * np.exp(rng.normal(0, tau_h_sigma, n))
    s_nom = service_time(bw, rtt, tau_h=tau_h_median)
    svc = service_time(bw, rtt, tau_h=0.0) + tau_h
    timeout = np.maximum(est_tcpa - T_man, 10.0)
    dec = decisions.copy()

    qR = cert["qR"] if cert else None
    qD = np.array(cert["qD"], float).copy() if cert else None
    edges = np.asarray(cert.get("edges", []), float) if cert else None
    bin_of = np.searchsorted(edges, est_tcpa, side="right") if cert else None
    dR = cert.get("dR", 0.01) if cert else None
    dD = cert.get("dD", 0.01) if cert else None
    W0 = np.full(n, np.nan); U = np.full(n, np.nan); L = np.full(n, np.nan)
    flagged = np.zeros(n, bool)
    qR_trace, qD_trace = [], []
    fb_R = []      # (time feedback available, idx)  resolution-time feedback
    fb_D = []      # deque of hazard idx (label after `delay` later arrivals)
    seen = 0

    free_at = [0.0] * M_ops
    heapq.heapify(free_at)
    queue = []
    q_work = [0.0]
    resolve = np.full(n, np.nan)
    mrm = np.zeros(n, bool)
    busy = 0.0
    waits = []
    pending = [(t_arr[k], order[k]) for k in range(n) if decisions[order[k]] == TAKEOVER]

    def key(i, ta):
        return (est_tcpa[i] + ta) if priority == "urgency" else ta

    def online_feedback(now):
        nonlocal qR, qD
        # resolution feedback: known once the request is resolved
        while fb_R and fb_R[0][0] <= now:
            _, j = heapq.heappop(fb_R)
            tres = resolve[j] - t_arr_of[j]
            err = float(tres > U[j])
            qR = max(0.5, qR * np.exp(eta_R * (err - dR)))
        # deadline feedback: hazard label and true deadline revealed after `delay` arrivals
        while len(fb_D) > delay:
            j = fb_D.pop(0)
            if y[j] == 1:
                err = float((tcpa_true[j] - T_man) < L[j])
                b = bin_of[j]
                qD[b] = qD[b] + eta_D * (err - dD)
        qR_trace.append(qR); qD_trace.append(qD.copy())

    t_arr_of = np.empty(n); t_arr_of[order] = t_arr

    def admit(ta, i):
        """Arrival of TAKEOVER request i at time ta: certificate check, then enqueue."""
        nonlocal seen
        if cert is not None:
            if online:
                online_feedback(ta)
            if cert.get("static_wait") is not None:
                W0[i] = cert["static_wait"]          # ablation: no live queue state
            else:
                backlog = sum(max(0.0, f - ta) for f in free_at) + q_work[0]
                W0[i] = backlog / M_ops
            U[i] = qR * (W0[i] + s_nom[i])
            L[i] = est_tcpa[i] - T_man - qD[bin_of[i]]
            flagged[i] = U[i] > L[i]
            if online:
                fb_D.append(i)
            if route and mode in ("timeout", "hybrid", "full"):
                timeout[i] = max(min(timeout[i], L[i]), 0.0)
            if route and mode in ("route", "full") and flagged[i]:
                dec[i] = AVOID
                return
            if route and mode == "hybrid" and (W0[i] + s_nom[i]) > L[i]:
                dec[i] = AVOID
                return
        heapq.heappush(queue, (key(i, ta), ta, i))
        q_work[0] += s_nom[i]

    pi = 0
    now = 0.0
    while pi < len(pending) or queue:
        next_free = free_at[0]
        if queue and (pi >= len(pending) or next_free <= pending[pi][0]):
            start = max(next_free, now)
            while pi < len(pending) and pending[pi][0] <= start:
                ta, i = pending[pi]; pi += 1
                admit(ta, i)
            if not queue:
                continue
            _, ta, i = heapq.heappop(queue)
            q_work[0] -= s_nom[i]
            if start - ta >= timeout[i]:
                resolve[i] = ta + timeout[i]; mrm[i] = True; waits.append(timeout[i])
                if online and cert is not None:
                    heapq.heappush(fb_R, (resolve[i], i))
                continue
            heapq.heappop(free_at)
            done = start + svc[i]
            if done - ta > timeout[i]:
                resolve[i] = ta + timeout[i]; mrm[i] = True; end = ta + timeout[i]
            else:
                resolve[i] = done; end = done
            busy += end - start
            heapq.heappush(free_at, end)
            waits.append(start - ta)
            if online and cert is not None:
                heapq.heappush(fb_R, (resolve[i], i))
            now = start
        else:
            ta, i = pending[pi]; pi += 1
            admit(ta, i)
            now = ta

    span = t_arr[-1] if n else 1.0
    t_res = np.full(n, np.inf)
    tk = dec == TAKEOVER
    t_res[tk] = resolve[tk] - t_arr_of[tk]
    deadline = tcpa_true - T_man
    hz = y == 1
    late = hz & tk & (t_res > deadline)
    unsafe = hz & ((dec == PROCEED) | late)
    nh = y == 0
    out = dict(
        unsafe_rate=float(unsafe.sum() / max(1, hz.sum())),
        auto_clear_miss=float((hz & (dec == PROCEED)).sum() / max(1, hz.sum())),
        late_takeover_hazard=float(late.sum() / max(1, hz.sum())),
        false_manoeuvre=float((nh & (dec == AVOID)).sum() / max(1, nh.sum())),
        total_manoeuvre=float((nh & ((dec == AVOID) | (tk & mrm))).sum() / max(1, nh.sum())),
        takeover_rate=float(tk.mean()),
        routed_rate=float(((decisions == TAKEOVER) & (dec == AVOID)).mean()),
        mrm_rate=float(mrm[tk].sum() / max(1, tk.sum())),
        utilisation=float(busy / (M_ops * span)),
        mean_wait=float(np.mean(waits)) if waits else 0.0,
    )
    if cert is not None:
        served = (decisions == TAKEOVER) & ~np.isnan(resolve)
        tr_all = resolve - t_arr_of
        out["cov_R"] = float(np.mean(tr_all[served] <= U[served])) if served.any() else np.nan
        hzt = hz & (decisions == TAKEOVER)
        out["cov_D"] = float(np.mean(deadline[hzt] >= L[hzt])) if hzt.any() else np.nan
        out["qR_final"] = float(qR); out["qD_final"] = qD.tolist()
    if return_arrays:
        out["_late"] = late; out["_unsafe"] = unsafe; out["_flag"] = flagged
        out["_W0"] = W0; out["_snom"] = s_nom; out["_tres"] = resolve - t_arr_of
        out["_dec"] = dec; out["_mrm"] = mrm
        out["_qR_trace"] = np.array(qR_trace); out["_qD_trace"] = np.array(qD_trace)
    return out


def calibrate_certificate(decisions, d, rng_seed, gamma=0.005, n_iter=3, fleet=None, T_man=30.0, n_bins=2,
                          mode="full", static_wait=None, delta_D=None, delta_R=0.1, subset="tk"):
    """Policy-consistent calibration on D2 (Alg. 2): iterate {simulate under current
    certificate -> recompute conformal quantiles} so that the calibration residuals are drawn
    under the same routing policy that will be deployed. q_D is calibrated on the D2 hazards in the
    TAKEOVER band (Mondrian over n_bins bins of t_hat) at delta_D = gamma / pi_T, pi_T = share of D2
    hazards in the band, so that late-and-kept <= gamma among hazards (Theorem 2). delta_R only sets
    how aggressively infeasible requests are routed (efficiency), not the guarantee."""
    fleet = fleet or {}
    hz = d["y"] == 1
    pi_T = max(1e-3, float(np.mean(decisions[hz] == TAKEOVER)))
    # Theorem 2: late-and-kept among hazards <= pi_T * delta_D = gamma
    dD = min(0.2, gamma / pi_T) if delta_D is None else delta_D
    dR = delta_R
    hzt = hz & (decisions == TAKEOVER)
    base = hzt if subset == "tk" else hz
    # Mondrian deadline quantiles over bins of the estimated time-to-CPA (Eq. 35)
    eD = (d["est_tcpa"] - d["tcpa_true"])
    if n_bins > 1:
        edges = np.quantile(d["est_tcpa"][base], np.linspace(0, 1, n_bins + 1)[1:-1])
    else:
        edges = np.array([])
    b = np.searchsorted(edges, d["est_tcpa"], side="right")
    qD = [conformal_quantile(eD[base & (b == k)], dD) for k in range(len(edges) + 1)]
    cert = dict(qR=1.0, qD=qD, edges=edges.tolist(), dR=dR, dD=dD, static_wait=static_wait)
    for _ in range(n_iter):
        r = simulate_f(decisions, d["y"], d["tcpa_true"], d["est_tcpa"], d["bw"], d["rtt"],
                       np.random.default_rng(rng_seed), cert=cert, route=True, mode="route",
                       return_arrays=True, T_man=T_man, **fleet)
        served = (decisions == TAKEOVER) & np.isfinite(r["_tres"])
        ratio = r["_tres"][served] / (r["_W0"][served] + r["_snom"][served])
        cert = dict(qR=conformal_quantile(ratio, dR), qD=qD, edges=edges.tolist(), dR=dR, dD=dD,
                    static_wait=static_wait)
    cert["delta"] = dD; cert["pi_T"] = pi_T
    return cert
