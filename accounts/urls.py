from django.urls import path
from .views import login_view, logout_view


# URL patterns for authentication-related views
urlpatterns = [

    # Route for login page
    path('login/', login_view, name='login'),

    # Default homepage route
    path('', login_view, name='home'),

    # Route for logging out
    path('logout/', logout_view, name='logout'),
]