from django.contrib import admin
from .models import Project, BOQItem, DailyLog, DailyLogEntry, UserProfile, ProjectAssignment, InspectionPoint, InspectionRecord

class BOQItemInline(admin.TabularInline):
    model = BOQItem
    fk_name = 'project'
    extra = 0
    fields = ['item_code', 'description', 'unit', 'level', 'parent', 'planned_quantity', 'rate', 'approved_quantity']
    show_change_link = True

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'status', 'budget', 'progress']
    list_filter = ['status']
    search_fields = ['name']
    inlines = [BOQItemInline]

@admin.register(BOQItem)
class BOQItemAdmin(admin.ModelAdmin):
    list_display = ['item_code', 'description', 'level', 'planned_quantity', 'rate']
    list_filter = ['level']
    search_fields = ['item_code', 'description']
    
    def has_module_permission(self, request):
        return False

@admin.register(DailyLog)
class DailyLogAdmin(admin.ModelAdmin):
    list_display = ['project', 'contractor', 'log_date', 'status']
    list_filter = ['status', 'log_date']

@admin.register(DailyLogEntry)
class DailyLogEntryAdmin(admin.ModelAdmin):
    list_display = ['daily_log', 'boq_item', 'quantity']

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'company_name']
    list_filter = ['role']

@admin.register(ProjectAssignment)
class ProjectAssignmentAdmin(admin.ModelAdmin):
    list_display = ['project', 'contractor', 'start_date', 'end_date']

@admin.register(InspectionPoint)
class InspectionPointAdmin(admin.ModelAdmin):
    list_display = ['name', 'boq_item', 'priority', 'status']

@admin.register(InspectionRecord)
class InspectionRecordAdmin(admin.ModelAdmin):
    list_display = ['inspection_point', 'inspection_date', 'result']
