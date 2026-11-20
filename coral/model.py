"""
Link- and sea-state-conditioned set attention network (LCSA) for encounter hazard
prediction, implemented in NumPy with analytic gradients (no autodiff dependency).

  H   = ReLU(X W1 + b1) * mask                   per-target embedding
  q   = tanh(c Wq + bq)                          context query (sea state, link, ...)
  e_n = <H_n Wk, q> / sqrt(d)                    context-conditioned attention logits
  a   = softmax_mask(e)
  z   = [sum_n a_n H_n , max_n H_n , q]          attention + worst-target pooling
  o   = ReLU(z W2 + b2);   logit = o w3 + b3

attention=False replaces the attention read-out by masked mean pooling (MLP-set
baseline); use_context=False zeroes the context query (ablation).
"""
import numpy as np


class LCSA:
    def __init__(self, F, Cdim, d=48, seed=0, attention=True, use_context=True):
        r = np.random.default_rng(seed)
        s = lambda a, b: r.normal(0, np.sqrt(2.0 / a), (a, b))
        self.p = dict(W1=s(F, d), b1=np.zeros(d), Wq=s(Cdim, d) * 0.5, bq=np.zeros(d),
                      Wk=s(d, d) * 0.5, W2=s(3 * d, d), b2=np.zeros(d),
                      w3=s(d, 1)[:, 0] * 0.5, b3=np.zeros(1))
        self.d = d
        self.attention = attention
        self.use_context = use_context
        self.T = 1.0  # temperature (post-hoc calibration)

    # ---------------- forward ----------------
    def forward(self, X, M, C, cache=False):
        p, d = self.p, self.d
        pre1 = X @ p["W1"] + p["b1"]
        H = np.maximum(pre1, 0) * M[..., None]
        Cin = C if self.use_context else np.zeros_like(C)
        qpre = Cin @ p["Wq"] + p["bq"]
        q = np.tanh(qpre)
        if self.attention:
            K = H @ p["Wk"]
            e = np.einsum("bnd,bd->bn", K, q) / np.sqrt(d)
            e = np.where(M > 0, e, -1e9)
            e = e - e.max(1, keepdims=True)
            a = np.exp(e) * M
            a = a / a.sum(1, keepdims=True)
        else:
            K = None
            a = M / M.sum(1, keepdims=True)
        A = np.einsum("bn,bnd->bd", a, H)
        idx = H.argmax(1)  # [B,d]
        Mx = np.take_along_axis(H, idx[:, None, :], 1)[:, 0]
        Z = np.concatenate([A, Mx, q], 1)
        pre2 = Z @ p["W2"] + p["b2"]
        O = np.maximum(pre2, 0)
        logit = O @ p["w3"] + p["b3"][0]
        if cache:
            self._c = dict(X=X, M=M, Cin=Cin, pre1=pre1, H=H, q=q, K=K, a=a, idx=idx, Z=Z, pre2=pre2, O=O)
        return logit

    def predict_proba(self, X, M, C, bs=4096):
        out = []
        for i in range(0, len(X), bs):
            out.append(self.forward(X[i:i + bs], M[i:i + bs], C[i:i + bs]))
        lg = np.concatenate(out)
        return 1.0 / (1.0 + np.exp(-lg / self.T)), lg

    # ---------------- backward ----------------
    def backward(self, dlogit):
        p, c, d = self.p, self._c, self.d
        g = {}
        O, Z = c["O"], c["Z"]
        g["w3"] = O.T @ dlogit
        g["b3"] = np.array([dlogit.sum()])
        dO = np.outer(dlogit, p["w3"]) * (c["pre2"] > 0)
        g["W2"] = Z.T @ dO
        g["b2"] = dO.sum(0)
        dZ = dO @ p["W2"].T
        dA, dMx, dq = dZ[:, :d], dZ[:, d:2 * d], dZ[:, 2 * d:].copy()
        H, a = c["H"], c["a"]
        dH = a[..., None] * dA[:, None, :]
        if self.attention:
            da = np.einsum("bd,bnd->bn", dA, H)
            de = a * (da - (a * da).sum(1, keepdims=True))
            q, K = c["q"], c["K"]
            dK = de[..., None] * q[:, None, :] / np.sqrt(d)
            dq += np.einsum("bn,bnd->bd", de, K) / np.sqrt(d)
            g["Wk"] = np.einsum("bnd,bne->de", H, dK)
            dH += dK @ p["Wk"].T
        else:
            g["Wk"] = np.zeros_like(p["Wk"])
        # max-pool routing
        B = H.shape[0]
        dHmax = np.zeros_like(H)
        bi = np.arange(B)[:, None]
        di = np.arange(d)[None, :]
        dHmax[bi, c["idx"], di] = dMx
        dH += dHmax
        dpre1 = dH * c["M"][..., None] * (c["pre1"] > 0)
        g["W1"] = np.einsum("bnf,bnd->fd", c["X"], dpre1)
        g["b1"] = dpre1.sum((0, 1))
        dqpre = dq * (1 - c["q"] ** 2)
        g["Wq"] = c["Cin"].T @ dqpre
        g["bq"] = dqpre.sum(0)
        return g

    # ---------------- training ----------------
    def fit(self, X, M, C, y, epochs=12, bs=256, lr=2e-3, wd=1e-5, seed=0, bootstrap=False, verbose=False):
        r = np.random.default_rng(seed)
        n = len(y)
        idx_all = r.integers(0, n, n) if bootstrap else np.arange(n)
        mom = {k: np.zeros_like(v) for k, v in self.p.items()}
        vel = {k: np.zeros_like(v) for k, v in self.p.items()}
        t = 0
        yf = y.astype(np.float64)
        for ep in range(epochs):
            perm = r.permutation(idx_all)
            lr_ep = lr * 0.5 * (1 + np.cos(np.pi * ep / epochs))
            tot = 0.0
            for i in range(0, n, bs):
                b = perm[i:i + bs]
                lg = self.forward(X[b], M[b], C[b], cache=True)
                pr = 1 / (1 + np.exp(-lg))
                tot += -np.sum(yf[b] * np.log(pr + 1e-9) + (1 - yf[b]) * np.log(1 - pr + 1e-9))
                gr = self.backward((pr - yf[b]) / len(b))
                t += 1
                for k in self.p:
                    gk = gr[k] + wd * self.p[k]
                    mom[k] = 0.9 * mom[k] + 0.1 * gk
                    vel[k] = 0.999 * vel[k] + 0.001 * gk ** 2
                    mh = mom[k] / (1 - 0.9 ** t)
                    vh = vel[k] / (1 - 0.999 ** t)
                    self.p[k] -= lr_ep * mh / (np.sqrt(vh) + 1e-8)
            if verbose:
                print(f"  epoch {ep+1}/{epochs} nll={tot/n:.4f}")
        return self

    def fit_temperature(self, X, M, C, y):
        _, lg = self.predict_proba(X, M, C)
        best, bestT = np.inf, 1.0
        for T in np.linspace(0.5, 3.0, 51):
            pr = np.clip(1 / (1 + np.exp(-lg / T)), 1e-7, 1 - 1e-7)
            nll = -np.mean(y * np.log(pr) + (1 - y) * np.log(1 - pr))
            if nll < best:
                best, bestT = nll, T
        self.T = bestT
        return bestT


class Ensemble:
    """Deep ensemble of LCSA members -> mean hazard probability and epistemic spread."""

    def __init__(self, F, Cdim, m=5, **kw):
        self.members = [LCSA(F, Cdim, seed=100 + i, **kw) for i in range(m)]

    def fit(self, X, M, C, y, **kw):
        for i, mdl in enumerate(self.members):
            mdl.fit(X, M, C, y, seed=1000 + i, bootstrap=True, **kw)
        return self

    def calibrate(self, X, M, C, y):
        return [mdl.fit_temperature(X, M, C, y) for mdl in self.members]

    def predict(self, X, M, C):
        P = np.stack([mdl.predict_proba(X, M, C)[0] for mdl in self.members])
        return P.mean(0), P.std(0)


def grad_check(seed=0):
    """Finite-difference check of the analytic gradients."""
    r = np.random.default_rng(seed)
    B, N, F, Cd = 5, 4, 6, 3
    X = r.normal(size=(B, N, F)); M = (r.random((B, N)) > 0.3).astype(float); M[:, 0] = 1
    C = r.normal(size=(B, Cd)); y = r.integers(0, 2, B).astype(float)
    net = LCSA(F, Cd, d=7, seed=seed)

    def loss():
        lg = net.forward(X, M, C, cache=True)
        pr = 1 / (1 + np.exp(-lg))
        return -np.mean(y * np.log(pr) + (1 - y) * np.log(1 - pr)), pr

    L, pr = loss()
    g = net.backward((pr - y) / B)
    worst = 0.0
    for k, v in net.p.items():
        for _ in range(6):
            ix = tuple(r.integers(0, s) for s in v.shape)
            old = v[ix]
            v[ix] = old + 1e-6; Lp, _ = loss()
            v[ix] = old - 1e-6; Lm, _ = loss()
            v[ix] = old
            num = (Lp - Lm) / 2e-6
            rel = abs(num - g[k][ix]) / max(1e-8, abs(num) + abs(g[k][ix]))
            worst = max(worst, rel if abs(num) > 1e-9 else 0)
    return worst
