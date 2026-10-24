import math
class _Norm:
    @staticmethod
    def cdf(x): return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
    @staticmethod
    def pdf(x): return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)
norm = _Norm()
