from django.urls import path
from .views import whatsapp_bot

urlpatterns = [
    path('FYP/', whatsapp_bot, name='whatsapp_bot'),
]