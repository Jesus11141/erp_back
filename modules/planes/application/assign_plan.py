from datetime import date, timedelta
from ..domain.entities import Plan, Subscription, PLANS


class AssignPlan:
    def execute(self, tenant_id: int, plan_key: str, months: int = 1) -> dict:
        if plan_key not in PLANS:
            raise ValueError(f"Invalid plan. Options: {list(PLANS.keys())}")
        plan = PLANS[plan_key]
        start_date = date.today()
        end_date = start_date + timedelta(days=30 * months)
        return {
            'tenant_id': tenant_id,
            'plan_key': plan_key,
            'activated_modules': plan['modules'],
            'start_date': start_date,
            'end_date': end_date,
            'total_price': plan['price'] * months,
        }

