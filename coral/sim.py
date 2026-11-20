"""
Maritime encounter sandbox for satellite-supervised USV fleets.

Each sample is one encounter-assessment event of an own-ship USV:
  * ground truth: future relative motion of up to N target ships over a horizon H,
    including unannounced target manoeuvres (intent uncertainty);
  * observations: noisy marine radar (sea-state dependent noise and detection
    probability) and AIS (dropouts, report age, satellite AIS delay);
  * link state: LEO / GEO / degraded satellite regime with RTT and bandwidth.

Label y = 1 if, with the own-ship continuing its plan, any target enters the
safety domain (distance < D_SAFE) within the horizon.
All units SI (m, s, rad).
"""
import numpy as np

D_SAFE = 300.0      # m, safety domain radius
HORIZON = 300.0     # s, prediction horizon
DT_TRUE = 5.0       # s, integration step for ground truth
N_MAX = 8           # max number of target tokens
HIST = (-20.0, -10.0, 0.0)  # radar scan times used for velocity estimation

# satellite link regimes: (name, RTT range s, bandwidth range Mbit/s)
LINKS = {
    0: ("LEO", (0.04, 0.12), (20.0, 80.0)),
    1: ("GEO", (0.55, 0.80), (1.0, 4.0)),
    2: ("DEGRADED", (1.5, 6.0), (0.1, 0.5)),
}

DEFAULT_CFG = dict(
    sea=(0.0, 0.6),         # sea-state index range (0 calm .. 1 very rough)
    n_targets=(1, 6),       # inclusive range
    p_collision_course=0.18,
    p_manoeuvre=0.3,
    tgt_speed=(2.0, 12.0),
    ais_drop=0.10,
    ais_age=(0.0, 30.0),
    link_probs=(0.65, 0.25, 0.10),
    own_speed=(3.0, 8.0),
)


def _wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


def generate(n, rng, **overrides):
    """Generate n encounter-assessment samples. Returns dict of arrays."""
    cfg = dict(DEFAULT_CFG)
    cfg.update(overrides)
    F = 16  # token feature size (see token layout below)
    X = np.zeros((n, N_MAX, F), dtype=np.float32)
    M = np.zeros((n, N_MAX), dtype=np.float32)
    C = np.zeros((n, 6), dtype=np.float32)
    y = np.zeros(n, dtype=np.int8)
    tcpa_true = np.full(n, HORIZON, dtype=np.float32)   # time of first domain violation
    link = np.zeros(n, dtype=np.int8)
    rtt = np.zeros(n, dtype=np.float32)
    bw = np.zeros(n, dtype=np.float32)
    sea_arr = np.zeros(n, dtype=np.float32)
    est_tcpa = np.full(n, HORIZON, dtype=np.float32)  # sensor-based estimate (for urgency)

    t_grid = np.arange(0.0, HORIZON + 1e-9, DT_TRUE)
    for i in range(n):
        sea = rng.uniform(*cfg["sea"])
        v_own = rng.uniform(*cfg["own_speed"])
        nt = rng.integers(cfg["n_targets"][0], cfg["n_targets"][1] + 1)
        g = rng.choice(3, p=cfg["link_probs"])
        r_lo, r_hi = LINKS[g][1]
        b_lo, b_hi = LINKS[g][2]
        rtt_i = rng.uniform(r_lo, r_hi)
        bw_i = np.exp(rng.uniform(np.log(b_lo), np.log(b_hi)))
        own_pos_t = np.stack([v_own * t_grid, np.zeros_like(t_grid)], 1)  # own ship along +x

        min_d_all = np.inf
        first_violation = HORIZON
        k = 0
        best_tcpa_est = HORIZON
        for j in range(nt):
            # ---- ground-truth target kinematics ----
            v_t = rng.uniform(*cfg["tgt_speed"])
            if rng.random() < cfg["p_collision_course"]:
                tc = rng.uniform(40.0, 420.0)
                meet = np.array([v_own * tc, 0.0]) + rng.normal(0, 350.0, 2)
                brg = rng.uniform(-np.pi, np.pi)
                p0 = meet - v_t * tc * np.array([np.cos(brg), np.sin(brg)])
                crs = brg
            else:
                rng0 = rng.uniform(600.0, 4500.0)
                b0 = rng.uniform(-np.pi, np.pi)
                p0 = rng0 * np.array([np.cos(b0), np.sin(b0)])
                crs = rng.uniform(-np.pi, np.pi)
            # keep targets outside the domain at t=0 and within radar range
            r0 = np.linalg.norm(p0)
            if r0 < D_SAFE * 1.3:
                p0 = p0 / max(r0, 1e-6) * D_SAFE * 1.3
            if np.linalg.norm(p0) > 6000.0:
                p0 = p0 / np.linalg.norm(p0) * 6000.0
            # manoeuvre (unknown to own ship)
            man = rng.random() < cfg["p_manoeuvre"]
            t_m = rng.uniform(0.0, HORIZON) if man else np.inf
            dpsi = rng.choice([-1, 1]) * rng.uniform(np.deg2rad(20), np.deg2rad(90)) if man else 0.0
            # past trajectory (straight) for t<0, future piecewise
            vel0 = v_t * np.array([np.cos(crs), np.sin(crs)])
            vel1 = v_t * np.array([np.cos(crs + dpsi), np.sin(crs + dpsi)])
            tt = t_grid[:, None]
            pos_fut = np.where(tt <= t_m, p0 + vel0 * tt,
                               p0 + vel0 * min(t_m, HORIZON) + vel1 * (tt - t_m))
            d = np.linalg.norm(pos_fut - own_pos_t, axis=1)
            viol = np.where(d < D_SAFE)[0]
            if viol.size:
                first_violation = min(first_violation, t_grid[viol[0]])
            min_d_all = min(min_d_all, d.min())

            # ---- observations ----
            # radar: three scans in own-ship relative frame (own ship moves too)
            radar_ok = []
            radar_xy = []
            for ts in HIST:
                p_true = p0 + vel0 * ts - np.array([v_own * ts, 0.0])
                rr = np.linalg.norm(p_true)
                pd = np.clip(0.97 - 0.35 * sea * (rr / 5000.0) - 0.1 * sea, 0.3, 0.99)
                if rng.random() < pd:
                    sr = 8.0 + 25.0 * sea
                    sb = np.deg2rad(0.4 + 1.5 * sea)
                    rm = rr + rng.normal(0, sr)
                    bm = np.arctan2(p_true[1], p_true[0]) + rng.normal(0, sb)
                    radar_xy.append([rm * np.cos(bm), rm * np.sin(bm)])
                    radar_ok.append(1.0)
                else:
                    radar_xy.append([0.0, 0.0])
                    radar_ok.append(0.0)
            radar_xy = np.array(radar_xy)
            radar_ok = np.array(radar_ok)
            # AIS: stale position + SOG/COG
            ais_ok = float(rng.random() > cfg["ais_drop"])
            age = rng.uniform(*cfg["ais_age"]) + (2.0 * rtt_i if g > 0 else 0.0)
            if ais_ok:
                p_ais = p0 - vel0 * age - np.array([0.0, 0.0]) + rng.normal(0, 10.0, 2)
                v_ais = vel0 + rng.normal(0, 0.2, 2)
            else:
                p_ais = np.zeros(2)
                v_ais = np.zeros(2)
            # skip target if completely unobserved (realistic: own ship cannot know it)
            if radar_ok.sum() == 0 and ais_ok == 0:
                continue
            if k >= N_MAX:
                continue
            # fused estimate: position from latest radar else dead-reckoned AIS;
            # velocity from AIS else radar finite difference
            v_rel_r = np.zeros(2)
            vr_ok = 0.0
            okidx = np.where(radar_ok)[0]
            if okidx.size >= 2:
                a, b = okidx[0], okidx[-1]
                v_rel_r = (radar_xy[b] - radar_xy[a]) / (HIST[b] - HIST[a])
                vr_ok = 1.0
            if ais_ok:
                v_rel = v_ais - np.array([v_own, 0.0])
            elif vr_ok:
                v_rel = v_rel_r
            else:
                v_rel = np.array([-v_own, 0.0])
            if radar_ok[2]:
                p_est = radar_xy[2]
            elif ais_ok:
                p_est = p_ais + v_ais * age   # dead-reckon stale AIS report to t=0
            else:
                idx = np.where(radar_ok)[0][-1]
                p_est = radar_xy[idx] + v_rel * (-HIST[idx])
            # CPA from estimate
            vv = v_rel @ v_rel
            tcpa = -(p_est @ v_rel) / vv if vv > 1e-6 else 0.0
            tcpa_c = np.clip(tcpa, 0.0, HORIZON)
            dcpa = np.linalg.norm(p_est + v_rel * tcpa_c)
            if dcpa < 2 * D_SAFE:
                best_tcpa_est = min(best_tcpa_est, tcpa_c)
            rng_est = np.linalg.norm(p_est)
            # token layout (scaled)
            X[i, k] = [
                p_est[0] / 3000.0, p_est[1] / 3000.0,
                v_rel[0] / 10.0, v_rel[1] / 10.0,
                v_rel_r[0] / 10.0, v_rel_r[1] / 10.0,
                np.log1p(rng_est / 100.0) / 4.0,
                dcpa / 1000.0, tcpa_c / HORIZON,
                float(tcpa > 0),
                radar_ok.mean(), radar_ok[2], vr_ok,
                ais_ok, (age / 60.0) * ais_ok,
                np.linalg.norm(v_ais) / 10.0,
            ]
            M[i, k] = 1.0
            k += 1
        if k == 0:  # nothing observed: add an empty "no contact" token
            M[i, 0] = 1.0
        y[i] = int(min_d_all < D_SAFE)
        tcpa_true[i] = first_violation
        link[i] = g
        rtt[i] = rtt_i
        bw[i] = bw_i
        sea_arr[i] = sea
        est_tcpa[i] = best_tcpa_est
        C[i] = [sea, v_own / 8.0, k / N_MAX, np.log10(rtt_i * 1000) / 4.0,
                np.log10(bw_i) / 2.0, float(g)]
    return dict(X=X, M=M, C=C, y=y, tcpa_true=tcpa_true, link=link, rtt=rtt,
                bw=bw, sea=sea_arr, est_tcpa=est_tcpa)


def concat(*ds):
    return {k: np.concatenate([d[k] for d in ds]) for k in ds[0]}


def subset(d, idx):
    return {k: v[idx] for k, v in d.items()}
