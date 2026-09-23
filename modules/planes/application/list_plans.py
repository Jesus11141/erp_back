from datetime import date, timedelta
from ..domain.entities import Plan, Subscription, PLANS


class ListPlans:
    def execute(self) -> list:
        return [Plan(key=k, **v) for k, v in PLANS.items()]


