#!/usr/bin/env python3
"""Test CP/W' curve fitting with known values."""

import numpy as np

from src.strava_analyzer.metrics.power_curve import (
    estimate_cp_wprime,
    hyperbolic_model,
)

# Known CP model parameters
TRUE_CP = 250.0  # watts
TRUE_W_PRIME = 15000.0  # joules (15 kJ)

# Generate synthetic MMP data from the known model
# Test 1: Only up to 1 hour (current situation)
test_intervals_short = [120, 180, 300, 600, 900, 1200, 1800, 2400, 3600]
# Test 2: Extended to 4 hours (with long efforts)
test_intervals_long = [
    120,
    180,
    300,
    600,
    900,
    1200,
    1800,
    2400,
    3600,
    5400,
    7200,
    10800,
    14400,
]

print("=" * 70)
print("TEST 1: Fitting with data ONLY up to 1 hour (current situation)")
print("=" * 70)
print(f"True CP: {TRUE_CP} W")
print(f"True W': {TRUE_W_PRIME} J ({TRUE_W_PRIME / 1000} kJ)\n")

test_data_short = []
for t in test_intervals_short:
    power = hyperbolic_model(t, TRUE_CP, TRUE_W_PRIME)
    noise = np.random.normal(0, 2)
    power_noisy = power + noise
    test_data_short.append((t, power_noisy))
    print(f"{t:5d}s ({t / 3600:5.2f} hr): {power_noisy:6.2f} W")

result_short = estimate_cp_wprime(test_data_short, ftp=285.0)
print("\nFitted results (SHORT intervals):")
cp_error = result_short["cp"] - TRUE_CP
print(f"  CP: {result_short['cp']:.2f} W (true: {TRUE_CP} W, error: {cp_error:+.2f} W)")
w_prime_error = result_short["w_prime"] - TRUE_W_PRIME
print(
    f"  W': {result_short['w_prime']:.0f} J = {result_short['w_prime'] / 1000:.2f} kJ"
)
print(
    f"      (true: {TRUE_W_PRIME} J = {TRUE_W_PRIME / 1000} kJ, "
    f"error: {w_prime_error:+.0f} J = {w_prime_error / 1000:+.2f} kJ)"
)
print(f"  R²: {result_short['r_squared']:.6f}")

print("\n" + "=" * 70)
print("TEST 2: Fitting with data up to 4 hours (EXTENDED intervals)")
print("=" * 70)
print(f"True CP: {TRUE_CP} W")
print(f"True W': {TRUE_W_PRIME} J ({TRUE_W_PRIME / 1000} kJ)\n")

test_data_long = []
for t in test_intervals_long:
    power = hyperbolic_model(t, TRUE_CP, TRUE_W_PRIME)
    noise = np.random.normal(0, 2)
    power_noisy = power + noise
    test_data_long.append((t, power_noisy))
    if t <= 3600:
        print(f"{t:5d}s ({t / 3600:5.2f} hr): {power_noisy:6.2f} W")
    else:
        label = "← LONG EFFORT (closer to CP)"
        print(f"{t:5d}s ({t / 3600:5.2f} hr): {power_noisy:6.2f} W  {label}")

result_long = estimate_cp_wprime(test_data_long, ftp=285.0)
print("\nFitted results (LONG intervals):")
cp_error_long = result_long["cp"] - TRUE_CP
cp_str = f"{result_long['cp']:.2f} W (true: {TRUE_CP} W, error: {cp_error_long:+.2f} W)"
print(f"  CP: {cp_str}")
w_prime_error_long = result_long["w_prime"] - TRUE_W_PRIME
print(f"  W': {result_long['w_prime']:.0f} J = {result_long['w_prime'] / 1000:.2f} kJ")
print(
    f"      (true: {TRUE_W_PRIME} J = {TRUE_W_PRIME / 1000} kJ, "
    f"error: {w_prime_error_long:+.0f} J = {w_prime_error_long / 1000:+.2f} kJ)"
)
print(f"  R²: {result_long['r_squared']:.6f}")

print("\n" + "=" * 70)
print("COMPARISON:")
print("=" * 70)
cp_improvement = abs(result_short["cp"] - TRUE_CP) - abs(result_long["cp"] - TRUE_CP)
print(f"CP error improved by: {cp_improvement:+.2f} W")
w_prime_improvement = abs(result_short["w_prime"] - TRUE_W_PRIME) - abs(
    result_long["w_prime"] - TRUE_W_PRIME
)
print(
    f"W' error improved by: {w_prime_improvement:+.0f} J "
    f"({w_prime_improvement / 1000:+.2f} kJ)"
)
r2_improvement = result_long["r_squared"] - result_short["r_squared"]
print(f"R² improved by: {r2_improvement:+.6f}")
