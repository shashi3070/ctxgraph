"""Subscription plans and pricing tiers."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from shared.logging import get_logger
from shared.metrics import get_collector


class BillingCycle(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMIANNUAL = "semiannual"
    ANNUAL = "annual"


class PlanTier(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class FeatureType(str, Enum):
    USAGE = "usage"
    BOOLEAN = "boolean"
    QUOTA = "quota"
    RATE_LIMIT = "rate_limit"


@dataclass
class Feature:
    key: str
    name: str
    description: Optional[str]
    type: FeatureType
    value: Any
    unit: Optional[str] = None
    display_order: int = 0
    is_public: bool = True

    def get_display_value(self) -> str:
        if self.type == FeatureType.BOOLEAN:
            return "Included" if self.value else "Not included"
        if self.unit:
            return f"{self.value} {self.unit}"
        return str(self.value)


@dataclass
class PricingTier:
    billing_cycle: BillingCycle
    price: Decimal
    currency: str = "USD"
    discount_percent: int = 0
    setup_fee: Decimal = Decimal("0")

    def effective_price(self) -> Decimal:
        if self.discount_percent > 0:
            return self.price * (Decimal("100") - Decimal(str(self.discount_percent))) / Decimal("100")
        return self.price

    def monthly_equivalent(self) -> Decimal:
        effective = self.effective_price()
        if self.billing_cycle == BillingCycle.ANNUAL:
            return effective / Decimal("12")
        elif self.billing_cycle == BillingCycle.QUARTERLY:
            return effective / Decimal("3")
        elif self.billing_cycle == BillingCycle.MONTHLY:
            return effective
        elif self.billing_cycle == BillingCycle.WEEKLY:
            return effective * Decimal("4.33")
        return effective


@dataclass
class SubscriptionPlan:
    plan_id: str
    name: str
    description: Optional[str]
    tier: PlanTier
    pricing: Dict[BillingCycle, PricingTier]
    features: List[Feature]
    is_active: bool = True
    is_public: bool = True
    trial_days: int = 14
    grace_period_days: int = 3
    max_users: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def get_feature(self, key: str) -> Optional[Feature]:
        for feature in self.features:
            if feature.key == key:
                return feature
        return None

    def has_feature(self, key: str) -> bool:
        feature = self.get_feature(key)
        if feature and feature.type == FeatureType.BOOLEAN:
            return bool(feature.value)
        return feature is not None

    def get_feature_value(self, key: str, default: Any = None) -> Any:
        feature = self.get_feature(key)
        return feature.value if feature else default

    def price_per_cycle(self, billing_cycle: BillingCycle) -> Decimal:
        tier = self.pricing.get(billing_cycle)
        return tier.effective_price() if tier else Decimal("0")

    def monthly_price(self, billing_cycle: BillingCycle) -> Decimal:
        tier = self.pricing.get(billing_cycle)
        return tier.monthly_equivalent() if tier else Decimal("0")

    def get_available_billing_cycles(self) -> List[BillingCycle]:
        return list(self.pricing.keys())

    def is_downgrade_from(self, other: "SubscriptionPlan") -> bool:
        tier_order = [t for t in PlanTier]
        return tier_order.index(self.tier) < tier_order.index(other.tier)

    def is_upgrade_from(self, other: "SubscriptionPlan") -> bool:
        tier_order = [t for t in PlanTier]
        return tier_order.index(self.tier) > tier_order.index(other.tier)


class PlanManager:
    def __init__(self):
        self.logger = get_logger("PlanManager", "billing-service")
        self.metrics = get_collector("billing-service")
        self._plans: Dict[str, SubscriptionPlan] = {}
        self._initialize_default_plans()

    def _initialize_default_plans(self) -> None:
        free_features = [
            Feature(key="api_calls_monthly", name="API Calls", description="Monthly API calls", type=FeatureType.QUOTA, value=1000, unit="calls/month"),
            Feature(key="storage_gb", name="Storage", description="Storage space", type=FeatureType.QUOTA, value=1, unit="GB"),
            Feature(key="users", name="Team Members", description="Number of team members", type=FeatureType.QUOTA, value=1, unit="users"),
            Feature(key="community_support", name="Community Support", description="Community forum access", type=FeatureType.BOOLEAN, value=True),
            Feature(key="priority_support", name="Priority Support", description="Priority email support", type=FeatureType.BOOLEAN, value=False),
            Feature(key="advanced_analytics", name="Advanced Analytics", description="Detailed analytics dashboard", type=FeatureType.BOOLEAN, value=False),
        ]

        starter_features = [
            Feature(key="api_calls_monthly", name="API Calls", type=FeatureType.QUOTA, value=100000, unit="calls/month"),
            Feature(key="storage_gb", name="Storage", type=FeatureType.QUOTA, value=10, unit="GB"),
            Feature(key="users", name="Team Members", type=FeatureType.QUOTA, value=5, unit="users"),
            Feature(key="community_support", name="Community Support", type=FeatureType.BOOLEAN, value=True),
            Feature(key="email_support", name="Email Support", type=FeatureType.BOOLEAN, value=True),
            Feature(key="priority_support", name="Priority Support", type=FeatureType.BOOLEAN, value=False),
            Feature(key="advanced_analytics", name="Advanced Analytics", type=FeatureType.BOOLEAN, value=True),
        ]

        pro_features = [
            Feature(key="api_calls_monthly", name="API Calls", type=FeatureType.QUOTA, value=1000000, unit="calls/month"),
            Feature(key="storage_gb", name="Storage", type=FeatureType.QUOTA, value=100, unit="GB"),
            Feature(key="users", name="Team Members", type=FeatureType.QUOTA, value=20, unit="users"),
            Feature(key="community_support", name="Community Support", type=FeatureType.BOOLEAN, value=True),
            Feature(key="email_support", name="Email Support", type=FeatureType.BOOLEAN, value=True),
            Feature(key="priority_support", name="Priority Support", type=FeatureType.BOOLEAN, value=True),
            Feature(key="advanced_analytics", name="Advanced Analytics", type=FeatureType.BOOLEAN, value=True),
            Feature(key="custom_integrations", name="Custom Integrations", type=FeatureType.BOOLEAN, value=True),
            Feature(key="sso", name="Single Sign-On", type=FeatureType.BOOLEAN, value=False),
        ]

        enterprise_features = [
            Feature(key="api_calls_monthly", name="API Calls", type=FeatureType.QUOTA, value=10000000, unit="calls/month"),
            Feature(key="storage_gb", name="Storage", type=FeatureType.QUOTA, value=1000, unit="GB"),
            Feature(key="users", name="Team Members", type=FeatureType.QUOTA, value=100, unit="users"),
            Feature(key="community_support", name="Community Support", type=FeatureType.BOOLEAN, value=True),
            Feature(key="email_support", name="Email Support", type=FeatureType.BOOLEAN, value=True),
            Feature(key="priority_support", name="Priority Support", type=FeatureType.BOOLEAN, value=True),
            Feature(key="dedicated_support", name="Dedicated Support", type=FeatureType.BOOLEAN, value=True),
            Feature(key="advanced_analytics", name="Advanced Analytics", type=FeatureType.BOOLEAN, value=True),
            Feature(key="custom_integrations", name="Custom Integrations", type=FeatureType.BOOLEAN, value=True),
            Feature(key="sso", name="Single Sign-On", type=FeatureType.BOOLEAN, value=True),
            Feature(key="saml", name="SAML Integration", type=FeatureType.BOOLEAN, value=True),
            Feature(key="custom_branding", name="Custom Branding", type=FeatureType.BOOLEAN, value=True),
            Feature(key="sla_999", name="99.9% SLA", type=FeatureType.BOOLEAN, value=True),
        ]

        free_plan = SubscriptionPlan(
            plan_id="free",
            name="Free",
            description="Get started with our free tier",
            tier=PlanTier.FREE,
            pricing={},
            features=free_features,
            trial_days=0
        )

        starter_plan = SubscriptionPlan(
            plan_id="starter",
            name="Starter",
            description="Perfect for small projects",
            tier=PlanTier.STARTER,
            pricing={
                BillingCycle.MONTHLY: PricingTier(
                    billing_cycle=BillingCycle.MONTHLY,
                    price=Decimal("29.00"),
                    currency="USD"
                ),
                BillingCycle.ANNUAL: PricingTier(
                    billing_cycle=BillingCycle.ANNUAL,
                    price=Decimal("290.00"),
                    currency="USD",
                    discount_percent=17
                )
            },
            features=starter_features
        )

        pro_plan = SubscriptionPlan(
            plan_id="pro",
            name="Pro",
            description="For growing businesses",
            tier=PlanTier.PRO,
            pricing={
                BillingCycle.MONTHLY: PricingTier(
                    billing_cycle=BillingCycle.MONTHLY,
                    price=Decimal("99.00"),
                    currency="USD"
                ),
                BillingCycle.ANNUAL: PricingTier(
                    billing_cycle=BillingCycle.ANNUAL,
                    price=Decimal("990.00"),
                    currency="USD",
                    discount_percent=17
                )
            },
            features=pro_features
        )

        enterprise_plan = SubscriptionPlan(
            plan_id="enterprise",
            name="Enterprise",
            description="For large organizations",
            tier=PlanTier.ENTERPRISE,
            pricing={
                BillingCycle.MONTHLY: PricingTier(
                    billing_cycle=BillingCycle.MONTHLY,
                    price=Decimal("499.00"),
                    currency="USD"
                ),
                BillingCycle.ANNUAL: PricingTier(
                    billing_cycle=BillingCycle.ANNUAL,
                    price=Decimal("4990.00"),
                    currency="USD",
                    discount_percent=17
                )
            },
            features=enterprise_features,
            is_public=False
        )

        self._plans = {
            "free": free_plan,
            "starter": starter_plan,
            "pro": pro_plan,
            "enterprise": enterprise_plan
        }

    def get_plan(self, plan_id: str) -> Optional[SubscriptionPlan]:
        return self._plans.get(plan_id)

    def list_plans(self, include_inactive: bool = False, include_private: bool = False) -> List[SubscriptionPlan]:
        plans = list(self._plans.values())
        if not include_inactive:
            plans = [p for p in plans if p.is_active]
        if not include_private:
            plans = [p for p in plans if p.is_public]
        return sorted(plans, key=lambda p: p.tier)

    def create_plan(self, plan: SubscriptionPlan) -> SubscriptionPlan:
        if plan.plan_id in self._plans:
            raise ValueError(f"Plan {plan.plan_id} already exists")
        self._plans[plan.plan_id] = plan
        self.logger.info(f"Created plan: {plan.plan_id}")
        return plan

    def update_plan(self, plan_id: str, updates: Dict[str, Any]) -> Optional[SubscriptionPlan]:
        plan = self._plans.get(plan_id)
        if not plan:
            return None

        for key, value in updates.items():
            if hasattr(plan, key):
                setattr(plan, key, value)

        plan.updated_at = datetime.utcnow()
        self.logger.info(f"Updated plan: {plan_id}")
        return plan

    def deactivate_plan(self, plan_id: str) -> bool:
        plan = self._plans.get(plan_id)
        if not plan:
            return False
        plan.is_active = False
        plan.updated_at = datetime.utcnow()
        self.logger.info(f"Deactivated plan: {plan_id}")
        return True
