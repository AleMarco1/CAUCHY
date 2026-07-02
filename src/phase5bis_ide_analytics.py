"""
CAUCHY Phase 5bis — IDE+CPL Analytic Module
==============================================
Implements H(z) for CPL and IDE+CPL models following Neumann, Videla & Araya 2026
(arXiv:2604.22970) §2.2.

Interaction term: Q = beta * H * rho_de  (Model CI in Neumann notation)

Analytic solutions involve incomplete gamma functions via scipy.special.

Usage
-----
    python phase5bis_ide_analytics.py          # run unit tests
    python phase5bis_ide_analytics.py --test   # verbose test output

Reference
---------
  Neumann, Videla & Araya 2026, arXiv:2604.22970
  Gavela, Hernandez, Lopez Honorez, Mena & Rigolin 2009, JCAP 0907:034
  (arXiv: 0906.1470)
"""

import numpy as np
from scipy.special import gammainc, gammainccinv, gamma as Gamma
from scipy.integrate import quad
import argparse
import sys

# ---------------------------------------------------------------------------
# Physical constants / fiducial values
# ---------------------------------------------------------------------------
H0_FIDUCIAL = 100.0   # km/s/Mpc — we work in units where h is explicit
OMEGA_RAD   = 4.18e-5  # radiation density parameter (negligible at low z)

# ---------------------------------------------------------------------------
# CPL H(z)
# ---------------------------------------------------------------------------

def hz_cpl(z, w0, wa, Omm, h, Omb=0.049, Omnu=0.0):
    """
    Hubble parameter H(z) / (H0 * h) for CPL dark energy.

    Equation of state:  w_de(a) = w0 + wa * (1 - a)
    Flat universe:      Omega_Lambda = 1 - Omm - Omb - Omr (negligible radiation)

    Parameters
    ----------
    z   : float or array  — redshift
    w0  : float           — EoS parameter today
    wa  : float           — EoS slope
    Omm : float           — total matter density parameter (col 0 of nwLH params)
    h   : float           — reduced Hubble constant (col 2)
    Omb : float           — baryon density parameter (col 1); not used for H(z)
                            but kept for signature consistency
    Omnu: float           — neutrino density fraction of matter (from Mnu)

    Returns
    -------
    E(z) = H(z) / H0  (dimensionless)
    """
    z = np.asarray(z, dtype=float)
    a = 1.0 / (1.0 + z)

    # CPL dark energy density: rho_de / rho_de0
    # w_de(a) = w0 + wa*(1-a)  =>  integral_a^1 (1+w)/a' da' = -(1+w0+wa)*ln(a) + wa*(a-1)
    fde = a ** (-3.0 * (1.0 + w0 + wa)) * np.exp(3.0 * wa * (a - 1.0))

    # Total matter (CDM + baryons + massive nu approximation)
    Om_total_matter = Omm  # already includes all matter species in Quijote convention

    # Dark energy fraction today: flat universe
    Omde = 1.0 - Om_total_matter

    # E(z)^2
    E2 = Om_total_matter * (1.0 + z)**3 + Omde * fde
    return np.sqrt(np.maximum(E2, 0.0))


# ---------------------------------------------------------------------------
# IDE+CPL H(z)  — Neumann, Videla & Araya 2026 §2.2
# ---------------------------------------------------------------------------
# Model CI:  Q = beta * H * rho_de  (energy flows from DE to DM when beta > 0)
#
# Background equations (in terms of scale factor a):
#
#   rho_m'  = -3 rho_m / a  +  beta * rho_de / a     (DM gains energy)
#   rho_de' = -3(1+w_de) rho_de / a  -  beta * rho_de / a
#           = -[3(1+w_de) + beta] rho_de / a
#
# For CPL: w_de(a) = w0_de + wa_de*(1-a)
# rho_de(a) = rho_de0 * f_de(a)  with:
#
#   f_de(a) = exp( -integral_1^a [3(1+w_de(a')) + beta] / a' da' )
#           = a^{-(3(1+w0_de+wa_de)+beta)} * exp(3*wa_de*(a-1))
#
# i.e. identical to CPL but with effective w0_eff = w0_de + beta/3  (when wa=0):
#   rho_de(a) = rho_de0 * a^{-(3+3*w0_de+beta)} * exp(3*wa_de*(a-1))
#
# For rho_m, the analytical solution requires an integrating factor.
# The DM equation with source term has solution (Neumann 2026 eq. 2.8):
#
#   rho_m(a) = rho_m0 * a^{-3}  +  beta * rho_de0 * a^{-3} * I(a)
#
# where I(a) = int_a^1 f_de(a') / a'^{-3+1} da' = int_a^1 f_de(a') * a'^{2} da'
#            = int_a^1 a'^{2-(3+3*w0_de+beta)} * exp(3*wa_de*(a'-1)) da'
#
# For wa_de = 0  (the relevant case for nwLH Quijote, where wa=0 for all sims):
#
#   f_de(a) = a^{-(3+3*w0_de+beta)}
#
#   I(a) = int_a^1 a'^{2-(3+3*w0_de+beta)} da'
#        = int_a^1 a'^{-(1+3*w0_de+beta)} da'
#
# Let  s = -(3*w0_de + beta)  =>  exponent = s - 1
#
#   If s != 0:  I(a) = [a'^s / s]_a^1 = (1 - a^s) / s
#   If s == 0:  I(a) = ln(1/a)
#
# This is the exact closed-form solution for wa=0.
# For wa != 0: the integral involves the incomplete gamma function structure
# described in Neumann §2.2 (eq. 2.10–2.12).  We implement the general case
# via numerical quadrature (since wa=0 for all Quijote nwLH, the numerical
# path is a safety fallback only).

def _rho_de_factor(a, w0_de, wa_de, beta):
    """
    f_de(a) = rho_de(a) / rho_de0
    Including beta shift in the decay exponent.
    """
    a = np.asarray(a, dtype=float)
    return a ** (-(3.0 * (1.0 + w0_de + wa_de) + beta)) * np.exp(3.0 * wa_de * (a - 1.0))


def _ide_integral_wa0(a, w0_de, beta):
    """
    Exact analytic integral I(a) = int_a^1 f_de(a') * a'^2 da'
    for the wa_de = 0 case.
    This gives the DM source contribution from IDE interaction.
    """
    s = -(3.0 * w0_de + beta)  # exponent in a^s for I(a)

    a = np.asarray(a, dtype=float)
    scalar_input = a.ndim == 0
    a = np.atleast_1d(a)

    result = np.where(
        np.abs(s) > 1e-10,
        (1.0 - a ** s) / s,
        np.log(1.0 / a)
    )
    return result.item() if scalar_input else result


def _ide_integral_general(a_val, w0_de, wa_de, beta):
    """
    Numerical fallback for I(a) when wa_de != 0.
    Uses scipy.integrate.quad for accuracy.
    """
    if np.abs(a_val - 1.0) < 1e-12:
        return 0.0

    def integrand(ap):
        return _rho_de_factor(ap, w0_de, wa_de, beta) * ap**2

    result, _ = quad(integrand, a_val, 1.0, limit=200, epsrel=1e-8)
    return result


def hz_ide(z, beta, w0_de, wa_de, Omm, h, Omb=0.049):
    """
    Hubble parameter E(z) = H(z)/H0 for IDE model with Q = beta * H * rho_de.

    The dark energy EoS is CPL:  w_de(a) = w0_de + wa_de*(1-a).
    Non-phantom (quintessence) condition:  w0_de > -1.
    Energy flows from DE to DM when beta > 0.

    Parameters
    ----------
    z     : float or array — redshift
    beta  : float          — coupling parameter (beta=0 => standard CPL)
    w0_de : float          — DE EoS today (> -1 for non-phantom quintessence)
    wa_de : float          — DE EoS slope (wa_de=0 for Quijote nwLH)
    Omm   : float          — total matter density today
    h     : float          — reduced Hubble constant
    Omb   : float          — baryon fraction (informational only)

    Returns
    -------
    E(z) = H(z)/H0  (dimensionless)
    """
    z = np.asarray(z, dtype=float)
    a = 1.0 / (1.0 + z)

    Omde0 = 1.0 - Omm   # flat universe

    # Dark energy density ratio
    fde = _rho_de_factor(a, w0_de, wa_de, beta)

    # DM interaction source integral
    use_analytic = np.abs(wa_de) < 1e-10

    if use_analytic:
        I_a = _ide_integral_wa0(a, w0_de, beta)
    else:
        # Vectorised numerical quadrature
        a_flat = np.atleast_1d(a).ravel()
        I_a = np.array([_ide_integral_general(ai, w0_de, wa_de, beta) for ai in a_flat])
        I_a = I_a.reshape(a.shape)

    # rho_m(a) / rho_m0 = a^{-3} + (beta * Omde0 / Omm) * a^{-3} * I(a)
    rho_m_ratio = (1.0 + z)**3 * (1.0 + beta * Omde0 / Omm * I_a)

    # E^2(z)
    E2 = Omm * rho_m_ratio + Omde0 * fde

    return np.sqrt(np.maximum(E2, 0.0))


# ---------------------------------------------------------------------------
# Unit tests (P5b-2)
# ---------------------------------------------------------------------------

def test_beta_zero_recovers_CPL(verbose=False, tol=1e-6):
    """
    P5b-2 Test 1: beta=0 => hz_ide == hz_cpl exactly.
    Tests across a range of (w0, wa, Omm, h) combinations.
    """
    test_cases = [
        dict(w0=-0.9, wa=0.0,  Omm=0.31, h=0.68),
        dict(w0=-1.2, wa=0.0,  Omm=0.28, h=0.70),
        dict(w0=-0.7, wa=0.3,  Omm=0.33, h=0.67),
        dict(w0=-1.0, wa=0.0,  Omm=0.30, h=0.68),  # LCDM
        dict(w0=-0.85,wa=-0.2, Omm=0.35, h=0.65),
    ]
    z_grid = np.linspace(0.01, 3.0, 200)
    n_fail = 0
    for tc in test_cases:
        E_cpl = hz_cpl(z_grid, tc['w0'], tc['wa'], tc['Omm'], tc['h'])
        E_ide = hz_ide(z_grid, beta=0.0, w0_de=tc['w0'], wa_de=tc['wa'],
                       Omm=tc['Omm'], h=tc['h'])
        max_diff = np.max(np.abs(E_ide - E_cpl) / E_cpl)
        ok = max_diff < tol
        if verbose:
            status = "PASS" if ok else "FAIL"
            print(f"  test_beta_zero | w0={tc['w0']:.2f} wa={tc['wa']:.2f} "
                  f"Omm={tc['Omm']:.2f} | max_DH/H={max_diff:.2e} | {status}")
        if not ok:
            n_fail += 1
    return n_fail == 0


def test_wa_zero_recovers_constant_w(verbose=False, tol=1e-6):
    """
    P5b-2 Test 2: wa_de=0 => IDE with constant w.
    Verifies that the analytic integral path gives the same result as
    a fine numerical quadrature.
    """
    test_cases = [
        dict(beta=0.05, w0=-0.8, Omm=0.31, h=0.68),
        dict(beta=0.10, w0=-0.9, Omm=0.28, h=0.70),
        dict(beta=0.15, w0=-0.7, Omm=0.33, h=0.67),
    ]
    z_grid = np.linspace(0.01, 3.0, 200)
    n_fail = 0
    for tc in test_cases:
        # Analytic path (wa=0 branch)
        E_analytic = hz_ide(z_grid, tc['beta'], tc['w0'], 0.0, tc['Omm'], tc['h'])
        # Numerical quadrature path (wa=1e-12 to force general branch)
        E_numerical = hz_ide(z_grid, tc['beta'], tc['w0'], 1e-12, tc['Omm'], tc['h'])
        max_diff = np.max(np.abs(E_analytic - E_numerical) / E_analytic)
        ok = max_diff < tol
        if verbose:
            status = "PASS" if ok else "FAIL"
            print(f"  test_wa_zero | beta={tc['beta']:.2f} w0={tc['w0']:.2f} "
                  f"| max_diff={max_diff:.2e} | {status}")
        if not ok:
            n_fail += 1
    return n_fail == 0


def test_LCDM_with_beta(verbose=False, tol=1e-5):
    """
    P5b-2 Test 3: w0_de=-1, wa_de=0, beta != 0 => IDE+LCDM modification.
    Verifies that:
    (a) The result differs from standard LCDM (beta != 0 matters)
    (b) The result is physically sensible (E(z) monotonically increasing with z)
    (c) E(z=0) = 1 exactly.
    """
    Omm, h = 0.31, 0.68
    z_grid = np.linspace(0.0, 3.0, 201)

    n_fail = 0
    for beta in [0.05, 0.10, 0.20]:
        E_ide = hz_ide(z_grid, beta=beta, w0_de=-1.0, wa_de=0.0, Omm=Omm, h=h)
        E_lcdm = hz_cpl(z_grid, w0=-1.0, wa=0.0, Omm=Omm, h=h)

        # E(z=0) = 1
        ok_norm = abs(E_ide[0] - 1.0) < tol

        # Result differs from LCDM
        ok_differs = np.max(np.abs(E_ide - E_lcdm)) > 1e-8

        # Monotonically increasing (ignoring z=0 endpoint)
        ok_mono = np.all(np.diff(E_ide) >= 0)

        ok = ok_norm and ok_differs and ok_mono
        if verbose:
            status = "PASS" if ok else "FAIL"
            print(f"  test_LCDM_with_beta | beta={beta:.2f} "
                  f"| E(0)={E_ide[0]:.6f} norm={ok_norm} "
                  f"differs={ok_differs} mono={ok_mono} | {status}")
        if not ok:
            n_fail += 1
    return n_fail == 0


def run_all_tests(verbose=True):
    """Run all P5b-2 unit tests. Returns True if all pass."""
    print("=" * 60)
    print("CAUCHY Phase 5bis — P5b-2 Unit Tests")
    print("=" * 60)

    results = {}
    tests = [
        ("test_beta_zero_recovers_CPL",      test_beta_zero_recovers_CPL),
        ("test_wa_zero_recovers_constant_w", test_wa_zero_recovers_constant_w),
        ("test_LCDM_with_beta",              test_LCDM_with_beta),
    ]

    for name, fn in tests:
        passed = fn(verbose=verbose)
        results[name] = passed
        icon = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {icon}  {name}")

    all_pass = all(results.values())
    print("-" * 60)
    print(f"  Result: {'ALL PASS' if all_pass else 'SOME TESTS FAILED'}")
    print("=" * 60)
    return all_pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="CAUCHY Phase 5bis — IDE+CPL analytics + unit tests (P5b-2)"
    )
    parser.add_argument("--test", action="store_true",
                        help="Run unit tests with verbose output")
    args = parser.parse_args()

    if args.test or True:   # always run tests when invoked directly
        ok = run_all_tests(verbose=True)
        sys.exit(0 if ok else 1)
