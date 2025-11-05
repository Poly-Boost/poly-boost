"""
测试最大交易金额按单价倍数下调的逻辑

复现场景：
- 单价 price = 0.9
- 最大交易金额 max_trade_amount = 5
- 期望最终交易金额 = 4.5（不超过5，且为0.9的整数倍）

运行: python tests/test_max_trade_multiple.py
"""

from decimal import Decimal, ROUND_FLOOR, getcontext


def adjust_by_price_multiple(max_amount: float, price: float) -> float:
    """按单价倍数下调到不超过最大值的金额（与实现一致，使用 Decimal）。"""
    if price <= 0:
        return float(max_amount)

    getcontext().prec = 28
    d_max = Decimal(str(max_amount))
    d_price = Decimal(str(price))
    units = (d_max / d_price).to_integral_value(rounding=ROUND_FLOOR)
    adjusted = (units * d_price).quantize(Decimal("0.000001"))
    return float(adjusted)


def main():
    price = 0.9
    max_amount = 5.0
    result = adjust_by_price_multiple(max_amount, price)
    expected = 4.5

    print("=== 测试: 最大交易金额按单价倍数下调 ===")
    print(f"单价: ${price}")
    print(f"最大金额: ${max_amount}")
    print(f"期望结果: ${expected}")
    print(f"实际结果: ${result}")

    ok = abs(result - expected) < 1e-9
    print("结果:", "通过" if ok else "失败")


if __name__ == "__main__":
    main()

