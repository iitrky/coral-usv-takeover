"""
AIS replay testbed: encounter assessments built from REAL vessel trajectories.

Source: Danish Maritime Authority AIS (2019), as preprocessed and released by the TrAISformer
authors (Nguyen & Fablet, IEEE Access 2024; github.com/CIA-Oceanix/TrAISformer, data/ct_dma).
Tracks are resampled every 10 min and normalised to lat [55.5, 58], lon [10.3, 13].

What is real:      own-ship and target trajectories (past and future), traffic density,
                   speeds, true manoeuvres, and therefore the hazard label.
What is simulated: radar noise / detection, AIS dropouts and report age, sea state, satellite
                   link regime, operator queue (same models as the sandbox, coral/sim.py).

Each assessment picks an own vessel underway at time t0 and takes as targets every vessel within
7 km whose track covers [t0 - 30 s, t0 + H]. Assessments with a target already inside 1.3 d_s,
or with a nearby vessel whose track ends inside the horizon (unknown future), are skipped.
Label y = 1 if any target comes within d_s of the own vessel's ACTUAL future track within H.
Hazards are enriched by stratified sampling to a fixed fraction (natural rate is about 4%);
the auto-clear guarantee is conditional on y = 1 and is unaffected by this enrichment.
"""
import numpy as np
from .safe_pickle import load
from .sim import N_MAX, HIST, LINKS, DEFAULT_CFG

LAT0, LON0 = 56.75, 11.65
R_OBS = 7000.0


def load_tracks(path):
    D = load(path)
    tracks = []
    for d in D:
        tr = d["traj"]
        lat = 55.5 + tr[:, 0] * 2.5
        lon = 10.3 + tr[:, 1] * 2.7
        x = (lon - LON0) * 111320.0 * np.cos(np.deg2rad(LAT0))
        y = (lat - LAT0) * 110540.0
        t = tr[:, 4].astype(np.float64)
        o = np.argsort(t)
        t, x, y = t[o], x[o], y[o]
        keep = np.r_[True, np.diff(t) > 0]
        if keep.sum() >= 4:
            tracks.append((t[keep], x[keep], y[keep], int(d["mmsi"])))
    starts = np.array([tr[0][0] for tr in tracks])
    ends = np.array([tr[0][-1] for tr in tracks])
    return dict(tracks=tracks, starts=starts, ends=ends)


def _pos(tr, tq):
    t, x, y, _ = tr
    return np.stack([np.interp(tq, t, x), np.interp(tq, t, y)], -1)


def _vel(tr, t0, h=30.0):
    p = _pos(tr, np.array([t0 - h, t0 + h]))
    return (p[1] - p[0]) / (2 * h)


def generate_ais(pool, n, rng, H=1200.0, d_s=500.0, hazard_frac=0.25, dt_label=10.0, **overrides):
    cfg = dict(DEFAULT_CFG)
    cfg.update(overrides)
    tracks, starts, ends = pool["tracks"], pool["starts"], pool["ends"]
    n_haz = int(round(n * hazard_frac))
    quota = {1: n_haz, 0: n - n_haz}
    F = 16
    out = dict(X=[], M=[], C=[], y=[], tcpa_true=[], link=[], rtt=[], bw=[], sea=[], est_tcpa=[])
    tgrid = np.arange(0.0, H + 1e-9, dt_label)
    tries = 0
    natural = [0, 0]
    while quota[0] > 0 or quota[1] > 0:
        tries += 1
        if tries > 400 * n:
            raise RuntimeError("could not fill quotas")
        i = rng.integers(len(tracks))
        te = tracks[i]
        if te[0][-1] - te[0][0] < H + 120:
            continue
        t0 = rng.uniform(te[0][0] + 60, te[0][-1] - H)
        ve = _vel(te, t0)
        v_own = float(np.hypot(*ve))
        if v_own < 1.0:                       # own vessel must be underway
            continue
        pe0 = _pos(te, np.array([t0]))[0]
        alive = np.where((starts <= t0 - 30) & (ends >= t0 - 30))[0]
        alive = alive[alive != i]
        if len(alive) == 0:
            continue
        p_alive = np.array([_pos(tracks[j], np.array([t0]))[0] for j in alive])
        dist0 = np.hypot(*(p_alive - pe0).T)
        near = alive[dist0 < R_OBS]
        dn = dist0[dist0 < R_OBS]
        if len(near) == 0:
            continue
        if (ends[near] < t0 + H).any() or (dn < 1.3 * d_s).any():
            continue
        # ground truth from real futures
        pe = _pos(te, t0 + tgrid)
        dmin = np.inf
        first = H
        for j in near:
            d = np.hypot(*(_pos(tracks[j], t0 + tgrid) - pe).T)
            v = np.where(d < d_s)[0]
            if v.size:
                first = min(first, tgrid[v[0]])
            dmin = min(dmin, d.min())
        y = int(dmin < d_s)
        natural[y] += 1
        if quota[y] <= 0:
            continue
        quota[y] -= 1
        # ---- observation model in own-ship frame (heading along +x) ----
        psi = np.arctan2(ve[1], ve[0])
        Rm = np.array([[np.cos(-psi), -np.sin(-psi)], [np.sin(-psi), np.cos(-psi)]])
        sea = rng.uniform(*cfg["sea"])
        g = rng.choice(3, p=cfg["link_probs"])
        rtt_i = rng.uniform(*LINKS[g][1])
        bw_i = np.exp(rng.uniform(np.log(LINKS[g][2][0]), np.log(LINKS[g][2][1])))
        order = np.argsort(dn)[:N_MAX]
        X = np.zeros((N_MAX, F), np.float32)
        M = np.zeros(N_MAX, np.float32)
        k = 0
        best_tcpa = H
        for jj in order:
            tj = tracks[near[jj]]
            vel0 = Rm @ _vel(tj, t0)
            radar_xy, radar_ok = [], []
            for ts in HIST:
                p_true = Rm @ (_pos(tj, np.array([t0 + ts]))[0] - _pos(te, np.array([t0 + ts]))[0])
                rr = np.linalg.norm(p_true)
                pd = np.clip(0.97 - 0.35 * sea * (rr / 5000.0) - 0.1 * sea, 0.3, 0.99)
                if rng.random() < pd:
                    rm = rr + rng.normal(0, 8.0 + 25.0 * sea)
                    bm = np.arctan2(p_true[1], p_true[0]) + rng.normal(0, np.deg2rad(0.4 + 1.5 * sea))
                    radar_xy.append([rm * np.cos(bm), rm * np.sin(bm)]); radar_ok.append(1.0)
                else:
                    radar_xy.append([0.0, 0.0]); radar_ok.append(0.0)
            radar_xy = np.array(radar_xy); radar_ok = np.array(radar_ok)
            ais_ok = float(rng.random() > cfg["ais_drop"])
            age = rng.uniform(*cfg["ais_age"]) + (2.0 * rtt_i if g > 0 else 0.0)
            if ais_ok:
                p_ais = Rm @ (_pos(tj, np.array([t0 - age]))[0] - pe0) + rng.normal(0, 10.0, 2)
                v_ais = vel0 + rng.normal(0, 0.2, 2)
            else:
                p_ais = np.zeros(2); v_ais = np.zeros(2)
            if radar_ok.sum() == 0 and ais_ok == 0:
                continue
            v_rel_r = np.zeros(2); vr_ok = 0.0
            okidx = np.where(radar_ok)[0]
            if okidx.size >= 2:
                a, b = okidx[0], okidx[-1]
                v_rel_r = (radar_xy[b] - radar_xy[a]) / (HIST[b] - HIST[a]); vr_ok = 1.0
            if ais_ok:
                v_rel = v_ais - np.array([v_own, 0.0])
            elif vr_ok:
                v_rel = v_rel_r
            else:
                v_rel = np.array([-v_own, 0.0])
            if radar_ok[2]:
                p_est = radar_xy[2]
            elif ais_ok:
                p_est = p_ais + v_ais * age
            else:
                idx = okidx[-1]
                p_est = radar_xy[idx] + v_rel * (-HIST[idx])
            vv = v_rel @ v_rel
            tcpa = -(p_est @ v_rel) / vv if vv > 1e-6 else 0.0
            tcpa_c = np.clip(tcpa, 0.0, H)
            dcpa = np.linalg.norm(p_est + v_rel * tcpa_c)
            if dcpa < 2 * d_s:
                best_tcpa = min(best_tcpa, tcpa_c)
            X[k] = [p_est[0] / 3000.0, p_est[1] / 3000.0, v_rel[0] / 10.0, v_rel[1] / 10.0,
                    v_rel_r[0] / 10.0, v_rel_r[1] / 10.0, np.log1p(np.linalg.norm(p_est) / 100.0) / 4.0,
                    dcpa / 1000.0, tcpa_c / H, float(tcpa > 0), radar_ok.mean(), radar_ok[2], vr_ok,
                    ais_ok, (age / 60.0) * ais_ok, np.linalg.norm(v_ais) / 10.0]
            M[k] = 1.0
            k += 1
        if k == 0:
            M[0] = 1.0
        out["X"].append(X); out["M"].append(M)
        out["C"].append([sea, v_own / 8.0, k / N_MAX, np.log10(rtt_i * 1000) / 4.0, np.log10(bw_i) / 2.0, float(g)])
        out["y"].append(y); out["tcpa_true"].append(first); out["link"].append(g)
        out["rtt"].append(rtt_i); out["bw"].append(bw_i); out["sea"].append(sea); out["est_tcpa"].append(best_tcpa)
    res = {k: np.array(v) for k, v in out.items()}
    res["X"] = res["X"].astype(np.float32); res["M"] = res["M"].astype(np.float32)
    res["C"] = res["C"].astype(np.float32); res["y"] = res["y"].astype(np.int8)
    res["link"] = res["link"].astype(np.int8); res["tcpa_true"] = res["tcpa_true"].astype(np.float32)
    res["est_tcpa"] = res["est_tcpa"].astype(np.float32)
    res["natural_hazard_rate"] = np.array(natural[1] / max(1, sum(natural)))
    return res
