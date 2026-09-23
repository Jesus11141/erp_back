from django.urls import path
from .views import LoginView, UsersView, UserDetailView, MeView
from .roles_views import RoleListCreateView, RoleDetailView

urlpatterns = [
    path('login/', LoginView.as_view()),
    path('me/', MeView.as_view()),
    path('usuarios/', UsersView.as_view()),
    path('usuarios/<int:user_id>/', UserDetailView.as_view()),
    path('roles/', RoleListCreateView.as_view()),
    path('roles/<int:pk>/', RoleDetailView.as_view()),
]
