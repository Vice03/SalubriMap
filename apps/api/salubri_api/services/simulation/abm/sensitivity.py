# SPDX-License-Identifier: AGPL-3.0-or-later
"""Analyse de sensibilité globale, en NumPy seul : criblage de Morris puis indices de Sobol.

- Morris (1991), mesure μ* de Campolongo et al. (2007) : effets élémentaires sur r trajectoires dans une grille à
  4 niveaux, Δ = 2/3. Sert à écarter les paramètres sans effet.
- Sobol : schéma de Saltelli (2010) avec les estimateurs de Saltelli (ordre 1) et de Jansen (total),
  intervalle de confiance à 95 % par bootstrap.

`f` reçoit une matrice (n × k) de points dans [0, 1]^k et rend un vecteur de n sorties ; `scale` passe du cube
unité aux bornes des paramètres.
"""

from collections.abc import Callable

import numpy as np

Model = Callable[[np.ndarray], np.ndarray]


def scale(u: np.ndarray, bounds: list[tuple[float, float]]) -> np.ndarray:
    lo, hi = np.array(bounds).T
    return lo + u * (hi - lo)


def morris(f: Model, k: int, r: int = 10, levels: int = 4, seed: int = 0) -> dict[str, np.ndarray]:
    """μ* (moyenne des |effets|), μ et σ des effets élémentaires, par paramètre. r × (k + 1) évaluations."""
    rng = np.random.default_rng(seed)
    delta = levels / (2 * (levels - 1))
    grid = np.arange(levels // 2) / (levels - 1)  # bases telles que x + Δ ≤ 1
    pts, moved = [], []
    for _ in range(r):
        x = rng.choice(grid, k)
        order = rng.permutation(k)
        traj = [x.copy()]
        for i in order:
            x = x.copy()
            x[i] += delta
            traj.append(x)
        pts.append(np.array(traj))
        moved.append(order)
    y = f(np.concatenate(pts)).reshape(r, k + 1)
    ee = np.zeros((r, k))
    for t, order in enumerate(moved):
        for step, i in enumerate(order):
            ee[t, i] = (y[t, step + 1] - y[t, step]) / delta
    return {"mu_star": np.abs(ee).mean(0), "mu": ee.mean(0), "sigma": ee.std(0, ddof=1)}


def sobol(f: Model, k: int, n: int = 64, seed: int = 0, boot: int = 200) -> dict[str, np.ndarray]:
    """Indices d'ordre 1 (S1) et totaux (ST) avec IC 95 % ; n × (k + 2) évaluations."""
    rng = np.random.default_rng(seed)
    a, b = rng.random((n, k)), rng.random((n, k))
    ab = np.repeat(a[None], k, 0)
    for i in range(k):
        ab[i, :, i] = b[:, i]
    y = f(np.concatenate([a, b, ab.reshape(k * n, k)]))
    y = y - y[: 2 * n].mean()  # centrer : l'estimateur d'ordre 1 est bien moins bruité (Saltelli et al., 2010)
    fa, fb, fab = y[:n], y[n : 2 * n], y[2 * n :].reshape(k, n)

    def indices(idx: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        va, vb, vab = fa[idx], fb[idx], fab[:, idx]
        var = np.var(np.r_[va, vb])
        if var <= 0:
            return np.zeros(k), np.zeros(k)
        s1 = (vb * (vab - va)).mean(1) / var
        st = 0.5 * ((va - vab) ** 2).mean(1) / var
        return s1, st

    s1, st = indices(np.arange(n))
    bs = [indices(rng.integers(0, n, n)) for _ in range(boot)]
    s1b, stb = np.array([x[0] for x in bs]), np.array([x[1] for x in bs])
    return {
        "S1": s1,
        "S1_ic": np.percentile(s1b, [2.5, 97.5], axis=0),
        "ST": st,
        "ST_ic": np.percentile(stb, [2.5, 97.5], axis=0),
    }
