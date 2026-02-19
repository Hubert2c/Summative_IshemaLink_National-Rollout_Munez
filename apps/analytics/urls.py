from django.urls import path
from .views import (
    TopRoutesView, CommodityBreakdownView,
    RevenueHeatmapView, DriverLeaderboardView, MonthlySummaryView
)

urlpatterns = [
    path("routes/top/",            TopRoutesView.as_view(),         name="analytics-routes"),
    path("commodities/breakdown/", CommodityBreakdownView.as_view(),name="analytics-commodities"),
    path("revenue/heatmap/",       RevenueHeatmapView.as_view(),    name="analytics-revenue"),
    path("drivers/leaderboard/",   DriverLeaderboardView.as_view(), name="analytics-drivers"),
    path("monthly-summary/",       MonthlySummaryView.as_view(),    name="analytics-monthly"),
]
