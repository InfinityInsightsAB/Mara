"""Reusable numerical helpers for basis construction and regression."""

from __future__ import annotations

import numpy as np


def build_asset_grid(
    s0: float,
    strike: float,
    n_grid: int,
    low_factor: float,
    high_factor: float,
) -> np.ndarray:
    center = float(max(s0, 1e-8))
    low = float(max(center * low_factor, 0.5 * strike * low_factor))
    high = float(max(center, strike) * high_factor)
    return np.exp(np.linspace(np.log(low), np.log(high), int(n_grid)))


def build_vol_basis(v: np.ndarray, v_prime: np.ndarray, include_cross_term: bool = True) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    v_prime = np.asarray(v_prime, dtype=float)
    cols = [np.ones_like(v), v, v_prime]
    if include_cross_term:
        cols.append(v * v_prime)
    return np.column_stack(cols)


def build_lsmbasis_state(s: np.ndarray, v: np.ndarray, v_prime: np.ndarray, max_order: int = 2) -> np.ndarray:
    s = np.asarray(s, dtype=float)
    v = np.asarray(v, dtype=float)
    v_prime = np.asarray(v_prime, dtype=float)
    cols = [np.ones_like(s), s, v, v_prime]
    if max_order >= 2:
        cols.extend([s * s, v * v, v_prime * v_prime, s * v, s * v_prime, v * v_prime])
    return np.column_stack(cols)


def ridge_regression(X: np.ndarray, y: np.ndarray, ridge_lambda: float = 0.0) -> np.ndarray:
    XtX = X.T @ X
    Xty = X.T @ y
    if ridge_lambda > 0:
        XtX = XtX + ridge_lambda * np.eye(XtX.shape[0])
    try:
        return np.linalg.solve(XtX, Xty)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(X, y, rcond=None)[0]
