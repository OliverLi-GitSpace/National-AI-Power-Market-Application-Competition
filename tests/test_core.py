import unittest
from power_market.__main__ import forecast, optimize

CFG = dict(capacity_mwh=10, max_power_mw=2, efficiency=.95,
           soc_min=.1, soc_max=.9, soc_initial=.5, soc_terminal_min=.5)

class CoreTests(unittest.TestCase):
    def test_forecast_alignment(self):
        self.assertEqual(forecast(list(range(24))*7), list(range(24)))
        with self.assertRaises(ValueError): forecast([1]*25)

    def test_dispatch_feasibility(self):
        for prices in ([20]*12+[100]*12, [-50]*12+[100]*12, [0]*24):
            rows = optimize(prices, CFG)
            soc=.5
            for h, power, actual_soc in rows:
                self.assertLessEqual(abs(power), 2+1e-7)
                soc += (-power*.95 if power < 0 else -power/.95)/10
                self.assertAlmostEqual(actual_soc,soc)
                self.assertGreaterEqual(soc,.1-1e-7)
                self.assertLessEqual(soc,.9+1e-7)
            self.assertGreaterEqual(soc,.5-1e-7)
            self.assertGreaterEqual(sum(prices[h]*p for h,p,s in rows),-1e-6)

    def test_invalid_parameters(self):
        with self.assertRaises(ValueError): optimize([1]*24, dict(CFG, efficiency=0))
        with self.assertRaises(ValueError): optimize([1]*23, CFG)
