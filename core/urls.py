from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    ProjectViewSet, 
    CustomTokenObtainPairView, 
    DashboardStatsView, 
    BOQItemViewSet,
    DailyLogViewSet, 
    PendingApprovalsView, 
    ContractorProjectsView, 
    ContractorBOQView,
    MonthlyInspectionsView, 
    InvoiceViewSet,
    ComplianceViewSet,
)

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'boq', BOQItemViewSet, basename='boq')
router.register(r'daily-logs', DailyLogViewSet, basename='daily-log')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'compliance', ComplianceViewSet, basename='compliance')

urlpatterns = [
    # Authentication - No api/ prefix here (main urls.py handles it)
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Dashboard & Stats
    path('dashboard/stats/', DashboardStatsView.as_view(), name='dashboard_stats'),
    path('pending-approvals/', PendingApprovalsView.as_view(), name='pending-approvals'),
    
    # Contractor Endpoints
    path('contractor/projects/', ContractorProjectsView.as_view(), name='contractor-projects'),
    path('contractor/boq/<int:project_id>/', ContractorBOQView.as_view(), name='contractor-boq'),
    
    # Inspections
    path('monthly-inspections/', MonthlyInspectionsView.as_view(), name='monthly-inspections'),
    
    # Include router URLs (no api/ prefix)
    path('', include(router.urls)),
]
