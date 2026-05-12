from django.contrib import admin
from .models import Campaign, Market, Sales, Client, Visit

admin.site.register(Campaign)
admin.site.register(Market)
admin.site.register(Sales)
admin.site.register(Client)
admin.site.register(Visit)