from django.urls import path
from .views import summary_view, timeseries_view

urlpatterns = [
    path('summary/', summary_view, name='analytics-summary'),
    path('timeseries/', timeseries_view, name='analytics-timeseries'),
]

