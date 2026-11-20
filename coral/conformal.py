"""
CORAL decision layer: link-stratified conformal risk control with
workload-equalised takeover budgets.

Three-way rule per assessment i (score r_i, link regime g_i):
    PROCEED   if r_i <  lam_lo[g]
    TAKEOVER  if lam_lo[g] <= r_i < lam_hi[g]
    AVOID     if r_i >= lam_hi[g]           (autonomous evasive manoeuvre)

lam_lo[g]: conformal risk control of the auto-clear miss rate among hazards
           P(r < lam | y = 1, g) <= alpha                       (Eq. 18)
lam_hi[g]: conformal control of the takeover-request rate
           P(lam_lo <= r < lam | g) <= beta_g                    (Eq. 20)
beta_g   : workload-equalised budget  beta_g = rho M / (K r_e tau_g)   (Eq. 22)
"""
import numpy as np

PROCEED, TAKEOVER, AVOID = 0, 1, 2


def crc_largest_lambda(losses_fn, n, alpha, grid, B=1.0):
    """Largest lambda in grid with  n/(n+1) * Rhat(lam) + B/(n+1) <= alpha.
    losses_fn(lam) returns the empirical mean loss Rhat(lam), non-decreasing in lam."""
    best = grid[0]
    feasible = False
    for lam in grid:
        if (n / (n + 1.0)) * losses_fn(lam) + B / (n + 1.0) <= alpha:
            best, feasible = lam, True
        else:
            break
    return best if feasible else grid[0]


def score(p_mean, p_std, kappa):
    return p_mean + kappa * p_std


def calibrate_lo(r, y, groups, alpha, grid, stratified=True):
    lam = {}
    keys = np.unique(groups) if stratified else [None]
    for g in keys:
        sel = (groups == g) if g is not None else np.ones_like(y, bool)
        rp = r[sel & (y == 1)]
        n = len(rp)
        lam[g] = crc_largest_lambda(lambda l: np.mean(rp < l), n, alpha, grid)
    if not stratified:
        return {g: lam[None] for g in np.unique(groups)}
    return lam


def calibrate_hi(r, groups, lam_lo, beta, grid):
    """beta: dict group -> budget. lam_hi >= lam_lo."""
    lam = {}
    for g in np.unique(groups):
        rg = r[groups == g]
        n = len(rg)
        lo = lam_lo[g]
        sub = grid[grid >= lo]
        if len(sub) == 0:
            lam[g] = lo
            continue
        lam[g] = crc_largest_lambda(lambda l: np.mean((rg >= lo) & (rg < l)), n, beta[g], sub)
    return lam


def decide(r, groups, lam_lo, lam_hi):
    lo = np.array([lam_lo[g] for g in groups])
    hi = np.array([lam_hi[g] for g in groups])
    d = np.full(len(r), AVOID, dtype=np.int8)
    d[r < hi] = TAKEOVER
    d[r < lo] = PROCEED
    return d


def service_time(bw_mbps, rtt_s, tau_h=20.0, payload_MB=4.0):
    """Operator service time: situational-picture uplink + 2 RTT + human assessment."""
    return tau_h + 8.0 * payload_MB / bw_mbps + 2.0 * rtt_s


def workload_budgets(groups_cal, bw_cal, rtt_cal, K, M_ops, r_e, rho=0.7, beta_cap=0.35, tau_h=20.0):
    """Workload-equalised budget per link regime: beta_g * tau_g = rho*M/(K r_e)."""
    budget = {}
    for g in np.unique(groups_cal):
        sel = groups_cal == g
        tau = np.median(service_time(bw_cal[sel], rtt_cal[sel], tau_h))
        budget[g] = float(min(beta_cap, rho * M_ops / (K * r_e * tau)))
    return budget


def uniform_budgets(groups_cal, beta):
    return {g: beta for g in np.unique(groups_cal)}


class OnlineCRC:
    """Adaptive (ACI-style) update of lam_lo per group under distribution shift.
    After the label of an assessment is revealed (delay d), for hazards only:
        lam <- lam - eta * (1[r < lam] - alpha)
    """

    def __init__(self, lam_lo, alpha, eta=0.02, lo=0.0, hi=1.0):
        self.lam = dict(lam_lo)
        self.alpha, self.eta, self.lo, self.hi = alpha, eta, lo, hi

    def update(self, g, r, y):
        if y == 1:
            err = float(r < self.lam[g])
            self.lam[g] = float(np.clip(self.lam[g] - self.eta * (err - self.alpha), self.lo, self.hi))


# ---------------------------------------------------------------------------
# Extension: lateness-aware upper threshold (CORAL-L) and online budget update
# ---------------------------------------------------------------------------
def late_proxy(tcpa_true, est_tcpa, bw, rtt, wait_q, tau_h_q, T_man=30.0, T_min=10.0):
    """Calibration-time lateness indicator for a hazard sent to TAKEOVER.
    Resolution proxy = min(wait quantile + conservative service time, timeout);
    late if it exceeds the true deadline t* - T_man (known on labelled calibration data)."""
    svc = service_time(bw, rtt, tau_h=tau_h_q)
    t_out = np.maximum(est_tcpa - T_man, T_min)
    resolve = np.minimum(wait_q + svc, t_out)
    return resolve > (tcpa_true - T_man)


def calibrate_hi_lateness(r, y, groups, lam_lo, lam_hi_budget, late, gamma, grid):
    """Shrink lam_hi so that the share of hazards that are sent to TAKEOVER *and* would be
    late stays <= gamma (CRC on the hazards of D2), never exceeding the budget threshold (Eq. 27)."""
    lam = {}
    for g in np.unique(groups):
        sel = (groups == g) & (y == 1)
        rg, lg = r[sel], late[sel]
        n = len(rg)
        lo, hi_b = lam_lo[g], lam_hi_budget[g]
        sub = grid[(grid >= lo) & (grid <= hi_b)]
        if n == 0 or len(sub) == 0:
            lam[g] = hi_b
            continue
        lam[g] = crc_largest_lambda(lambda l: np.mean((rg >= lo) & (rg < l) & lg), n, gamma, sub)
    return lam


class OnlineBudget:
    """ACI-style tracking of the takeover rate per regime (Eq. 28):
        lam_hi <- lam_hi - eta_b * (1[takeover] - beta_g)
    applied at decision time (no label needed), clipped to [lam_lo, lam_hi_max]."""

    def __init__(self, lam_hi, beta, eta=0.002):
        self.lam = dict(lam_hi)
        self.cap = dict(lam_hi)
        self.beta, self.eta = beta, eta

    def update(self, g, took, lo):
        self.lam[g] = float(np.clip(self.lam[g] - self.eta * (float(took) - self.beta[g]), lo, max(self.cap[g], lo)))


# ---------------------------------------------------------------------------
# Baseline: Learn-then-Test (LTT) joint control of miss and help rate (RCIP-style)
# ---------------------------------------------------------------------------
def _binom_p(k, n, a):
    """Exact binomial p-value for H0: risk > a, given k losses out of n (P[Bin(n, a) <= k])."""
    from scipy.stats import binom
    return float(binom.cdf(k, n, a))


def ltt_thresholds(r, y, alpha, beta, delta=0.1, lo_grid=None, hi_step=0.01):
    """Global (lam_lo, lam_hi) with P(miss among hazards <= alpha and help rate <= beta) >= 1 - delta,
    via Bonferroni-corrected exact binomial tests over a 2-D grid (Learn then Test). Among valid
    pairs, the one with the fewest calibration false manoeuvres is returned."""
    if lo_grid is None:
        lo_grid = np.round(np.arange(0.0, 0.501, 0.01), 3)
    pairs = [(lo, hi) for lo in lo_grid for hi in np.round(np.arange(lo, 1.0001, hi_step), 3)]
    N = len(pairs)
    rp, n_p = r[y == 1], int((y == 1).sum())
    n = len(r)
    neg = r[y == 0]
    best, best_fm = None, np.inf
    for lo, hi in pairs:
        k1 = int((rp < lo).sum())
        p1 = _binom_p(k1, n_p, alpha)
        if p1 > delta / N:
            continue
        k2 = int(((r >= lo) & (r < hi)).sum())
        p2 = _binom_p(k2, n, beta)
        if p2 > delta / N:
            continue
        fm = float((neg >= hi).mean())
        if fm < best_fm:
            best, best_fm = (lo, hi), fm
    if best is None:            # nothing certified: send everything uncertain to AVOID
        best = (0.0, 0.0)
    return best, N


def online_bound(eta, T, rng_width=1.0, delay=0):
    """Deterministic long-run bound of Proposition 2: |avg error - target| <= (W + eta)/(eta T) + D/T."""
    return (rng_width + eta) / (eta * max(T, 1)) + delay / max(T, 1)
