from django.urls import path
from .views import (
    sales_dashboard,
    campaign_dashboard,
    marketing_dashboard,
    admin_dashboard,
    log_visit,
    my_clients,
    edit_visit,
    delete_visit,
    approve_campaign,
    reject_campaign
)

urlpatterns = [
    path('sales/', sales_dashboard, name='sales_dashboard'),
    path('sales/log-visit/', log_visit, name='log_visit'),
    path('sales/my-clients/', my_clients, name='my_clients'),
    path('sales/edit-visit/<int:visit_id>/', edit_visit, name='edit_visit'),
    path('sales/delete-visit/<int:visit_id>/', delete_visit, name='delete_visit'),

    path('campaign/', campaign_dashboard, name='campaign_dashboard'),
    path('campaign/approve/<int:campaign_id>/', approve_campaign, name='approve_campaign'),
    path('campaign/reject/<int:campaign_id>/', reject_campaign, name='reject_campaign'),

    path('marketing/', marketing_dashboard, name='marketing_dashboard'),
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
]