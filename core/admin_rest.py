    MaterialSubmittal,
)

# ============================================================================
# BRANDING
# ============================================================================

admin.site.site_header = "🏗 Elite Construction ERP"
admin.site.site_title = "Construction Control"
admin.site.index_title = "Executive Dashboard"


# ============================================================================
# DESIGN TOKENS
# ============================================================================

PRIMARY = "#f97316"
PRIMARY_DARK = "#ea580c"
SUCCESS = "#10b981"
DANGER = "#ef4444"
INFO = "#3b82f6"
WARNING = "#f59e0b"
SLATE = "#64748b"
DARK = "#0f172a"
LIGHT = "#f8fafc"
BORDER = "#e2e8f0"


# ============================================================================
# GLOBAL HELPERS
# ============================================================================

def currency(value):
    try:
        return f"R {float(value):,.2f}"
    except Exception:
        return "R 0.00"


def safe_percent(value):
    try:
        return max(0, min(100, int(value)))
    except Exception:
        return 0


def pill(text, color=SLATE):
    return format_html(
        """
        <span style="
            background:{};
            color:white;
            padding:5px 12px;
            border-radius:999px;
            font-size:11px;
            font-weight:700;
            letter-spacing:.4px;
            display:inline-block;">
            {}
        </span>
        """,
        color,
        str(text).upper().replace("_", " "),
    )


def modern_link(url, label, color=PRIMARY):
    return format_html(
        """
        <a href="{}" style="
            color:{};
            text-decoration:none;
            font-weight:700;">
            {}
        </a>
        """,
        url,
        color,
        label,
    )


def progress_bar(value):
    value = safe_percent(value)
    color = SUCCESS if value >= 80 else PRIMARY if value >= 45 else WARNING

    return format_html(
        """
        <div style="
            width:120px;
            height:8px;
            border-radius:999px;
            background:#e5e7eb;
            overflow:hidden;
            display:inline-block;">
            <div style="
                width:{}%;
                height:8px;
                background:{};
                border-radius:999px;">
            </div>
        </div>
        """,
        value,
        color,
    )


# ============================================================================
# BASE PREMIUM ADMIN
# ============================================================================

class LuxuryAdmin(admin.ModelAdmin):
    list_per_page = 25
    save_on_top = True

    class Media:
        css = {
            "all": (
                "admin/css/compact-inline.css",
            )
        }


# ============================================================================
# BOQ INLINE
# ============================================================================

class BOQItemInline(admin.TabularInline):
    model = BOQItem
    extra = 1
    fk_name = "project"
    show_change_link = True

    fields = [
        "item_code",
        "description",
        "unit",
        "planned_quantity",
        "rate",
        "approved_quantity",
        "level",
        "parent",
    ]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parent":
            object_id = request.resolver_match.kwargs.get("object_id")
            if object_id:
                kwargs["queryset"] = BOQItem.objects.filter(project_id=object_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# ============================================================================
# PROJECT ADMIN
# ============================================================================

@admin.register(Project)
class ProjectAdmin(LuxuryAdmin):
    list_display = [
        "name",
        "status_view",
        "progress_view",
        "budget_view",
        "actual_cost_view",
        "variance_view",
    ]

    list_filter = ["status", "created_at"]
    search_fields = ["name", "client_name", "location"]
    readonly_fields = ["progress", "actual_cost"]
    inlines = [BOQItemInline]

    fieldsets = (
        ("🏗 Project Information", {
            "fields": ("name", "description", "location", "status")
        }),
        ("👤 Client Information", {
            "fields": ("client_name", "municipal_reference")
        }),
        ("💰 Financials", {
            "fields": ("budget", "actual_cost", "progress")
        }),
        ("📅 Timeline", {
            "fields": ("start_date", "end_date", "project_manager")
        }),
    )

    wizard_steps = [
        {"step": 1, "title": "Basic Information", "fields": ["name", "description", "location"]},
        {"step": 2, "title": "Client Details", "fields": ["client_name", "municipal_reference"]},
        {"step": 3, "title": "Schedule", "fields": ["start_date", "end_date", "status"]},
        {"step": 4, "title": "Budget", "fields": ["budget", "project_manager"]},
    ]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("add-wizard/", self.admin_site.admin_view(self.wizard_view), name="project_add_wizard"),
        ]
        return custom_urls + urls

    def add_view(self, request, form_url="", extra_context=None):
        return redirect("admin:project_add_wizard")

    def status_view(self, obj):
        colors = {"active": SUCCESS, "pending": WARNING, "completed": INFO, "cancelled": DANGER}
        return pill(obj.status, colors.get(obj.status, SLATE))
    status_view.short_description = "Status"

    def progress_view(self, obj):
        return progress_bar(obj.progress)
    progress_view.short_description = "Progress"

    def budget_view(self, obj):
        return format_html('<span style="font-weight:700;color:#0f172a;">{}</span>', currency(obj.budget))
    budget_view.short_description = "Budget"

    def actual_cost_view(self, obj):
        return format_html('<span style="font-weight:700;color:{};">{}</span>', PRIMARY, currency(obj.actual_cost))
    actual_cost_view.short_description = "Actual Cost"

    def variance_view(self, obj):
        try:
            variance = float(obj.budget or 0) - float(obj.actual_cost or 0)
            color = SUCCESS if variance >= 0 else DANGER
            return format_html('<span style="font-weight:800;color:{};">{}</span>', color, currency(variance))
        except Exception:
            return "-"
    variance_view.short_description = "Variance"

    def wizard_view(self, request):
        step = int(request.GET.get("step", 1))
        total_steps = len(self.wizard_steps)

        if request.method == "POST":
            if "project_data" not in request.session:
                request.session["project_data"] = {}

            current_step = self.wizard_steps[step - 1]
            for field in current_step["fields"]:
                if field in request.POST:
                    request.session["project_data"][field] = request.POST[field]

            request.session.modified = True

            if step >= total_steps or "save" in request.POST:
                data = request.session.get("project_data", {}).copy()

                if data.get("start_date"):
                    try:
                        data["start_date"] = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
                    except Exception:
                        data["start_date"] = None

                if data.get("end_date"):
                    try:
                        data["end_date"] = datetime.strptime(data["end_date"], "%Y-%m-%d").date()
                    except Exception:
                        data["end_date"] = None

                if data.get("budget"):
                    try:
                        data["budget"] = Decimal(str(data["budget"]))
                    except Exception:
                        data["budget"] = Decimal("0")

                if data.get("project_manager"):
                    try:
                        data["project_manager"] = User.objects.get(id=int(data["project_manager"]))
                    except Exception:
                        data.pop("project_manager", None)

                try:
                    project = Project.objects.create(**data)
                    messages.success(request, f'✅ Project "{project.name}" created successfully!')
                    del request.session["project_data"]
                    return redirect("admin:core_project_changelist")
                except Exception as e:
                    messages.error(request, f"❌ {str(e)}")
                    return redirect("admin:project_add_wizard")

            return redirect(f"{request.path}?step={step + 1}")

        managers = User.objects.filter(is_superuser=True) | User.objects.filter(profile__role="pm")

        context = {
            "title": f"Create Project • Step {step}",
            "step": step,
            "total_steps": total_steps,
            "step_title": self.wizard_steps[step - 1]["title"],
            "fields": self.wizard_steps[step - 1]["fields"],
            "step_data": request.session.get("project_data", {}),
            "progress_percent": int((step - 1) / total_steps * 100),
            "STATUS_CHOICES": Project.STATUS_CHOICES,
            "project_managers": managers,
            "opts": self.model._meta,
            "has_view_permission": True,
            "has_add_permission": True,
        }

        return TemplateResponse(request, "admin/project_wizard.html", context)


# ============================================================================
# DAILY LOG ADMIN - CLEAN VERSION
# ============================================================================

@admin.register(DailyLog)
class DailyLogAdmin(LuxuryAdmin):
    list_display = [
        "log_date",
        "project_link",
        "contractor_name",
        "status_badge",
        "work_preview",
    ]

    list_filter = ["status", "log_date", "project"]
    search_fields = ["work_description", "contractor__username"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "log_date"

    # Admin actions
    actions = ["approve_selected", "reject_selected"]

    def save_model(self, request, obj, form, change):
        """Handle approval via admin save - updates BOQ quantities"""
        if change and 'status' in form.changed_data:
            new_status = form.cleaned_data.get('status')
            original = DailyLog.objects.get(pk=obj.pk) if obj.pk else None

            if new_status == 'approved' and original and original.status != 'approved':
                try:
                    obj.approve(
                        reviewer=request.user,
                        comments=form.cleaned_data.get('rejection_reason', 'Approved via admin'),
                        ip_address=request.META.get('REMOTE_ADDR')
                    )
                    messages.success(request, f'✅ Daily log approved! BOQ quantities updated.')
                    return
                except Exception as e:
                    messages.error(request, f'❌ Error approving log: {str(e)}')
                    return

        super().save_model(request, obj, form, change)

    def approve_selected(self, request, queryset):
        approved_count = 0
        error_count = 0

        for log in queryset:
            if log.status != 'approved':
                try:
                    log.approve(
                        reviewer=request.user,
                        comments='Approved via bulk action',
                        ip_address=request.META.get('REMOTE_ADDR')
                    )
                    approved_count += 1
                except Exception as e:
                    error_count += 1
                    self.message_user(request, f'Error approving log {log.id}: {str(e)}', level='ERROR')

        if approved_count > 0:
            self.message_user(request, f'✅ {approved_count} log(s) approved successfully! BOQ updated.', level='SUCCESS')
        if error_count > 0:
            self.message_user(request, f'⚠️ {error_count} log(s) failed to approve.', level='WARNING')

    approve_selected.short_description = "✅ Approve selected daily logs (updates BOQ)"

    def reject_selected(self, request, queryset):
        count = 0
        for log in queryset:
            if log.status != 'rejected':
                log.reject(
                    reviewer=request.user,
                    comments='Rejected via bulk action',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                count += 1

        self.message_user(request, f'❌ {count} log(s) rejected.', level='WARNING')

    reject_selected.short_description = "❌ Reject selected daily logs"

    def contractor_name(self, obj):
        return obj.contractor.username if obj.contractor else "-"

    def project_link(self, obj):
        if obj.project:
            url = reverse("admin:core_project_change", args=[obj.project.id])
            return modern_link(url, obj.project.name)
        return "-"

    def status_badge(self, obj):
        colors = {
            "submitted": WARNING,
            "approved": SUCCESS,
            "rejected": DANGER,
            "draft": SLATE,
            "partially_approved": INFO,
        }
        return pill(obj.status, colors.get(obj.status, SLATE))

    def work_preview(self, obj):
        text = obj.work_description or ""
        return text[:70] + "..." if len(text) > 70 else text

    # Hide these fields from the change form
    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        # Remove production quantity fields
        exclude = [
            'concrete_poured_m3', 'rebar_installed_ton', 'excavation_m3', 'backfill_m3',
            'formwork_m2', 'paving_m2', 'pipes_laid_m', 'painting_m2',
            'labour_cost_today', 'equipment_cost_today', 'material_cost_today', 'subcontractor_cost_today',
            'issues', 'photos', 'photo_captions', 'next_day_plan',
            'weather_morning', 'weather_afternoon', 'temperature_low', 'temperature_high',
            'rainfall', 'wind_speed', 'site_conditions',
            'toolbox_talk_topic', 'safety_talk_attendees', 'near_miss_count',
            'near_miss_description', 'first_aid_cases', 'safety_violations',
            'safety_inspection_done', 'non_conformance_count', 'non_conformance_details',
            'rework_hours', 'quality_checklist_used', 'delay_type',
            'delay_duration_hours', 'delay_reason', 'workers_idle', 'eot_claimed',
            'subcontractors_on_site', 'rfis_submitted', 'rfis_responded',
            'drawing_revisions_received'
        ]
        return [f for f in fields if f not in exclude]


# ============================================================================
# DAILY LOG ENTRY
# ============================================================================

@admin.register(DailyLogEntry)
class DailyLogEntryAdmin(LuxuryAdmin):
    list_display = ["daily_log", "boq_item", "quantity", "created_at"]


# ============================================================================
# USER PROFILE
# ============================================================================

@admin.register(UserProfile)
class UserProfileAdmin(LuxuryAdmin):
    list_display = ["user", "role", "company_name", "phone"]
    list_filter = ["role", "created_at"]
    search_fields = ["user__username", "company_name", "phone"]


# ============================================================================
# PROJECT ASSIGNMENT
# ============================================================================

@admin.register(ProjectAssignment)
class ProjectAssignmentAdmin(LuxuryAdmin):
    list_display = ["project", "contractor", "start_date", "end_date", "status"]
    list_filter = ["status", "start_date"]


# ============================================================================
# INSPECTIONS
# ============================================================================

@admin.register(InspectionPoint)
class InspectionPointAdmin(LuxuryAdmin):
    list_display = ["name", "boq_item", "priority", "status"]
    list_filter = ["priority", "status", "required_before_start"]


@admin.register(InspectionRecord)
class InspectionRecordAdmin(LuxuryAdmin):
    list_display = ["inspection_point", "result", "inspection_date", "inspected_by"]
    list_filter = ["result", "inspection_date"]
    date_hierarchy = "inspection_date"


# ============================================================================
# APPROVALS
# ============================================================================

@admin.register(ApprovalLevel)
class ApprovalLevelAdmin(LuxuryAdmin):
    list_display = ["project", "level_order", "level_name", "required_role", "is_mandatory"]
    ordering = ["project", "level_order"]


@admin.register(ApprovalRecord)
class ApprovalRecordAdmin(LuxuryAdmin):
    list_display = ["daily_log", "level_name", "action", "approver", "created_at"]
    list_filter = ["action", "created_at", "level_name"]
    date_hierarchy = "created_at"


# ============================================================================
# DOCUMENTS
# ============================================================================

@admin.register(RFI)
class RFIAdmin(LuxuryAdmin):
    list_display = ["rfi_number", "title", "project", "priority", "status", "created_at"]
    list_filter = ["priority", "status", "created_at"]


@admin.register(ChangeOrder)
class ChangeOrderAdmin(LuxuryAdmin):
    list_display = ["change_number", "title", "project", "change_type", "amount", "status"]


@admin.register(MaterialSubmittal)
class MaterialSubmittalAdmin(LuxuryAdmin):
    list_display = ["submittal_number", "title", "project", "manufacturer", "status"]
class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    fields = ['description', 'quantity', 'unit_price', 'amount']
    readonly_fields = ['amount']


@admin.register(Invoice)
class InvoiceAdmin(LuxuryAdmin):
    list_display = ['invoice_number', 'project', 'client_name', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['invoice_number', 'client_name', 'project__name']
    readonly_fields = ['subtotal', 'tax_amount', 'total_amount', 'created_at', 'updated_at']
    inlines = [InvoiceItemInline]
    
    fieldsets = (
        ('Invoice Information', {
            'fields': ('project', 'invoice_number', 'invoice_date', 'due_date')
        }),
        ('Client Details', {
            'fields': ('client_name', 'client_address')
        }),
        ('Financial', {
            'fields': ('subtotal', 'tax_rate', 'tax_amount', 'total_amount')
        }),
        ('Additional', {
            'fields': ('notes', 'status')
        }),
    )
