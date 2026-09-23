from django.urls import path
from .views import PlansView, AssignPlanView

urlpatterns = [
    path('', PlansView.as_view()),
    path('assign/', AssignPlanView.as_view()),
]
