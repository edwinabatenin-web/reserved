"""Price binding configuration for Stripe billing runtime.

Maps internal Reserved plan keys to Stripe price IDs.

IMPORTANT: Stripe price IDs must be obtained from your Stripe Dashboard:
1. Go to https://dashboard.stripe.com/products
2. Click on each product
3. Find the "Prices" section
4. Copy the price ID (starts with "price_")
5. Replace the placeholder values below with actual Stripe price IDs
"""

from reserved.billing.stripe_runtime import PriceBinding

# Map internal plan keys to Stripe price IDs and configuration
# Amounts are in minor currency units (pence for GBP)
PRICE_BINDINGS = [
    PriceBinding(
        plan_key="standard_monthly",
        provider_price_id="price_reserved_standard_monthly",  # TODO: Replace with actual Stripe price ID
        currency="GBP",
        amount_minor=999,  # £9.99
        interval="month",
        interval_count=1
    ),
    PriceBinding(
        plan_key="premium_monthly",
        provider_price_id="price_reserved_premium_monthly",  # TODO: Replace with actual Stripe price ID
        currency="GBP",
        amount_minor=1999,  # £19.99
        interval="month",
        interval_count=1
    ),
    PriceBinding(
        plan_key="launch_offer_months_2_6",
        provider_price_id="price_reserved_launch_offer_2_6",  # TODO: Replace with actual Stripe price ID
        currency="GBP",
        amount_minor=499,  # £4.99
        interval="month",
        interval_count=5  # 5-month subscription
    ),
    PriceBinding(
        plan_key="free_tier_under_25",
        provider_price_id="price_reserved_free_under_25",  # TODO: Replace with actual Stripe price ID
        currency="GBP",
        amount_minor=0,  # Free
        interval="month",
        interval_count=12  # 12-month free subscription
    ),
    PriceBinding(
        plan_key="launch_offer_month_1",
        provider_price_id="price_reserved_launch_offer_month_1",  # TODO: Replace with actual Stripe price ID
        currency="GBP",
        amount_minor=0,  # Free
        interval="month",
        interval_count=1  # 1-month free trial
    ),
]

__all__ = ["PRICE_BINDINGS"]
