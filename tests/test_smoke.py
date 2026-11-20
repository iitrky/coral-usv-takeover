"""Smoke tests: run with `python -m unittest discover -s tests -v` from the repository root."""
import os, sys, unittest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from coral.sim import generate
from coral.model import grad_check, Ensemble
from coral import conformal as cf
from coral.fleet import simulate
from coral.feasibility import conformal_quantile, simulate_f, calibrate_certificate

FLEET = dict(K=24, M_ops=2, r_e=1 / 60.0)
GRID = np.linspace(0, 1, 2001)


class TestCoral(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(0)
        cls.tr = generate(3000, rng)
        cls.c1, cls.c2, cls.te = generate(2000, rng), generate(2000, rng), generate(3000, rng)
        F, C = cls.tr["X"].shape[2], cls.tr["C"].shape[1]
        cls.ens = Ensemble(F, C, m=2)
        cls.ens.fit(cls.tr["X"], cls.tr["M"], cls.tr["C"], cls.tr["y"], epochs=2)
        cls.ens.calibrate(cls.c1["X"], cls.c1["M"], cls.c1["C"], cls.c1["y"])
        cls.r = {k: cf.score(*cls.ens.predict(d["X"], d["M"], d["C"]), 1.0)
                 for k, d in (("c1", cls.c1), ("c2", cls.c2), ("te", cls.te))}

    def test_gradient(self):
        self.assertLess(grad_check(), 1e-4)

    def test_data_shapes(self):
        d = self.te
        self.assertEqual(d["X"].shape[1:], (8, 16))
        self.assertTrue(set(np.unique(d["link"])) <= {0, 1, 2})
        self.assertTrue(0.05 < d["y"].mean() < 0.6)

    def test_conformal_quantile(self):
        x = np.arange(1, 100)
        self.assertEqual(conformal_quantile(x, 0.1), 90.0)
        self.assertTrue(np.isinf(conformal_quantile(np.arange(5), 0.01)))

    def test_thresholds_and_queue(self):
        c1, c2, te, r = self.c1, self.c2, self.te, self.r
        bud = cf.workload_budgets(c2["link"], c2["bw"], c2["rtt"], **FLEET)
        lo = cf.calibrate_lo(r["c1"], c1["y"], c1["link"], 0.05, GRID)
        hi = cf.calibrate_hi(r["c2"], c2["link"], lo, bud, GRID)
        for g in lo:
            self.assertLessEqual(lo[g], hi[g])
        dec = cf.decide(r["te"], te["link"], lo, hi)
        res = simulate(dec, te["y"], te["tcpa_true"], te["est_tcpa"], te["bw"], te["rtt"],
                       np.random.default_rng(1), **FLEET)
        self.assertGreaterEqual(res["unsafe_rate"], res["auto_clear_miss"])
        # without a certificate simulate_f reproduces simulate exactly
        res_f = simulate_f(dec, te["y"], te["tcpa_true"], te["est_tcpa"], te["bw"], te["rtt"],
                           np.random.default_rng(1), cert=None, **FLEET)
        self.assertAlmostEqual(res["unsafe_rate"], res_f["unsafe_rate"])
        self.assertAlmostEqual(res["takeover_rate"], res_f["takeover_rate"])

    def test_certificate_removes_late_takeovers(self):
        c1, c2, te, r = self.c1, self.c2, self.te, self.r
        bud = cf.workload_budgets(c2["link"], c2["bw"], c2["rtt"], **FLEET)
        lo = cf.calibrate_lo(r["c1"], c1["y"], c1["link"], 0.05, GRID)
        hi = cf.calibrate_hi(r["c2"], c2["link"], lo, bud, GRID)
        cert = calibrate_certificate(cf.decide(r["c2"], c2["link"], lo, hi), c2, 5, gamma=0.005, fleet=FLEET)
        self.assertTrue(cert["qR"] >= 1.0 or np.isinf(cert["qR"]))
        dec = cf.decide(r["te"], te["link"], lo, hi)
        base = simulate_f(dec, te["y"], te["tcpa_true"], te["est_tcpa"], te["bw"], te["rtt"],
                          np.random.default_rng(2), **FLEET)
        f = simulate_f(dec, te["y"], te["tcpa_true"], te["est_tcpa"], te["bw"], te["rtt"],
                       np.random.default_rng(2), cert=cert, mode="full", **FLEET)
        self.assertLessEqual(f["late_takeover_hazard"], base["late_takeover_hazard"] + 1e-12)
        self.assertLessEqual(f["takeover_rate"], base["takeover_rate"] + 1e-12)


if __name__ == "__main__":
    unittest.main()
