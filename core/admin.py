from django.contrib import admin
from django.urls import path
from .models import *
from .views import DirectorDashboardView

# ============================================================================
# DIRECTOR DASHBOARD
# ============================================================================
_original_get_urls = admin.site.get_urls
def custom_get_urls():
    urls = _original_get_urls()
    custom_urls = [
        path('director-dashboard/', admin.site.admin_view(DirectorDashboardView.as_view()), name='director_dashboard'),
    ]
    return custom_urls + urls
admin.site.get_urls = custom_get_urls

# ============================================================================
# PROJECT ADMIN
# ============================================================================
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "municipality", "project_manager", "status", "budget"]
    list_filter = ["status", "municipality"]
    search_fields = ["name", "client_name", "location"]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            if request.user.managed_municipalities.exists():
                return qs.filter(municipality__director=request.user)
            elif request.user.managed_projects.exists():
                return qs.filter(project_manager=request.user)
        return qs

# ============================================================================
# COMPLIANCE ADMIN
# ============================================================================
@admin.register(ContractorComplianceStatus)
class ContractorComplianceStatusAdmin(admin.ModelAdmin):
    list_display = ('contractor', 'requirement', 'status', 'approved_at')
    list_filter = ('status',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            if request.user.managed_municipalities.exists():
                return qs.filter(requirement__project__municipality__director=request.user)
            elif request.user.managed_projects.exists():
                return qs.filter(requirement__project__project_manager=request.user)
        return qs
        
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "requirement":
            if not request.user.is_superuser:
                if request.user.managed_municipalities.exists():
                    kwargs["queryset"] = ProjectComplianceRequirement.objects.filter(project__municipality__director=request.user)
                elif request.user.managed_projects.exists():
                    kwargs["queryset"] = ProjectComplianceRequirement.objects.filter(project__project_manager=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(ContractorProjectAccess)
class ContractorProjectAccessAdmin(admin.ModelAdmin):
    list_display = ('contractor', 'project', 'is_allowed')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            if request.user.managed_municipalities.exists():
                return qs.filter(project__municipality__director=request.user)
            elif request.user.managed_projects.exists():
                return qs.filter(project__project_manager=request.user)
        return qs

@admin.register(ProjectComplianceRequirement)
class FilteredProjectComplianceRequirementAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'is_mandatory', 'is_active')
    list_filter = ('is_mandatory', 'is_active')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            if request.user.managed_municipalities.exists():
                return qs.filter(project__municipality__director=request.user)
            elif request.user.managed_projects.exists():
                return qs.filter(project__project_manager=request.user)
        return qs
        
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "project":
            if not request.user.is_superuser:
                if request.user.managed_municipalities.exists():
                    kwargs["queryset"] = Project.objects.filter(municipality__director=request.user)
                elif request.user.managed_projects.exists():
                    kwargs["queryset"] = Project.objects.filter(project_manager=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# ============================================================================
# OTHER ADMINS
# ============================================================================
@admin.register(Municipality)
class MunicipalityAdmin(admin.ModelAdmin):
    list_display = ('name', 'director')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'model_name', 'project')
    readonly_fields = ('user', 'project', 'action', 'model_name', 'record_id', 'old_value', 'new_value', 'timestamp')
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

@admin.register(BOQItem)
class BOQItemAdmin(admin.ModelAdmin):
    list_display = ('item_code', 'description', 'project', 'planned_quantity')
    list_filter = ('project',)
