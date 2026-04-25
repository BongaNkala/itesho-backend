from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    ProjectViewSet, CustomTokenObtainPairView, DashboardStatsView, BOQItemViewSet,
    DailyLogViewSet, PendingApprovalsView, ContractorProjectsView, ContractorBOQView,
    MonthlyInspectionsView
)

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'boq', BOQItemViewSet, basename='boq')
router.register(r'daily-logs', DailyLogViewSet, basename='daily-log')

urlpatterns = [
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/dashboard/stats/', DashboardStatsView.as_view(), name='dashboard_stats'),
    path('api/pending-approvals/', PendingApprovalsView.as_view(), name='pending-approvals'),
    path('api/contractor/projects/', ContractorProjectsView.as_view(), name='contractor-projects'),
    path('api/contractor/boq/<int:project_id>/', ContractorBOQView.as_view(), name='contractor-boq'),
    path('api/monthly-inspections/', MonthlyInspectionsView.as_view(), name='monthly-inspections'),
    path('api/', include(router.urls)),
]
