import argparse
import csv
import json
import math
from pathlib import Path


def read_prices(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    values = [float(r['price']) for r in rows]
    if not values or not all(math.isfinite(x) for x in values):
        raise ValueError('price must contain finite numbers')
    return values


def forecast(values):
    """Mean of matching hours in up to seven complete previous days."""
    if len(values) < 24 or len(values) % 24:
        raise ValueError('history must contain complete 24-hour days, aligned at hour 0')
    days = min(len(values) // 24, 7)
    return [sum(values[-24 * d + h] for d in range(1, days + 1)) / days for h in range(24)]


def optimize(prices, cfg):
    """Hourly perfect-forecast MILP: positive output discharges (MW)."""
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    if len(prices) != 24:
        raise ValueError('exactly 24 hourly forecast prices required')
    capacity = float(cfg['capacity_mwh'])
    power = float(cfg['max_power_mw'])
    eta = float(cfg['efficiency'])
    lo, hi, initial = [float(cfg[k]) for k in ('soc_min', 'soc_max', 'soc_initial')]
    terminal = float(cfg.get('soc_terminal_min', initial))
    if not all(math.isfinite(x) for x in (capacity, power, eta, lo, hi, initial, terminal)):
        raise ValueError('battery parameters must be finite')
    if not (capacity > 0 and power > 0 and 0 < eta <= 1 and 0 <= lo <= initial <= hi <= 1 and lo <= terminal <= hi):
        raise ValueError('invalid battery parameters')
    # Variables: charge[24], discharge[24], charge-mode binary[24].
    cost = np.r_[prices, -np.array(prices), np.zeros(24)]
    acc = np.tril(np.ones((24, 24)))
    energy = np.c_[eta * acc, -acc / eta, np.zeros((24, 24))]
    lower = np.full(24, (lo - initial) * capacity)
    lower[-1] = (terminal - initial) * capacity
    mode_c = np.c_[np.eye(24), np.zeros((24,24)), -power * np.eye(24)]
    mode_d = np.c_[np.zeros((24,24)), np.eye(24), power * np.eye(24)]
    result = milp(cost, integrality=np.r_[np.zeros(48), np.ones(24)],
                  bounds=Bounds(np.zeros(72), np.r_[np.full(48,power), np.ones(24)]),
                  constraints=[LinearConstraint(energy, lower, (hi-initial)*capacity),
                               LinearConstraint(mode_c, -np.inf, 0),
                               LinearConstraint(mode_d, -np.inf, power)],
                  options={'time_limit': 30})
    if not result.success:
        raise RuntimeError(f'optimization failed: {result.message}')
    charge, discharge = result.x[:24], result.x[24:48]
    soc = initial + np.cumsum(eta * charge - discharge / eta) / capacity
    if np.any(soc < lo-1e-7) or np.any(soc > hi+1e-7) or soc[-1] < terminal-1e-7:
        raise RuntimeError('SOC validation failed')
    return [(h, float(discharge[h]-charge[h]), float(soc[h])) for h in range(24)]


def main():
    parser = argparse.ArgumentParser(description='Internal CSV format; not an official platform submission')
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('forecast', 'trade'):
        p = sub.add_parser(command)
        p.add_argument('--input', required=True)
        p.add_argument('--output', required=True)
        if command == 'trade':
            p.add_argument('--battery', required=True)
    args = parser.parse_args()
    prices = read_prices(args.input)
    if args.command == 'forecast':
        headers = ['hour', 'price']
        rows = list(enumerate(forecast(prices)))
    else:
        headers = ['hour', 'power_mw', 'soc_after']
        rows = optimize(prices, json.loads(Path(args.battery).read_text()))
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f'Wrote {len(rows)} rows to {target}; internal format only')


if __name__ == '__main__':
    main()
