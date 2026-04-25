from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.utils import timezone
import uuid

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('pm', 'Project Manager'),
        ('contractor', 'Contractor'),
        ('inspector', 'Inspector/Engineer'),
        ('consultant', 'Consultant/QS'),
        ('municipal', 'Municipal Inspector'),
        ('client', 'Client Representative'),
        ('reviewer', 'Reviewer'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='contractor')
    company_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    approval_pin = models.CharField(max_length=128, blank=True, help_text="Hashed PIN for approvals")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


class ApprovalLevel(models.Model):
    """Flexible approval levels - can be customized per project"""
    project = models.ForeignKey('Project', on_delete=models.CASCADE, related_name='approval_levels')
    level_order = models.IntegerField()
    level_name = models.CharField(max_length=50)  # e.g., "Site Engineer", "Consultant", "PM", "Municipal"
    required_role = models.CharField(max_length=50, blank=True)
    required_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='required_approvals')
    is_mandatory = models.BooleanField(default=True)
    notification_emails = models.TextField(blank=True, help_text="Comma-separated emails")
    timeout_hours = models.IntegerField(default=48, help_text="Hours before escalation")
    
    class Meta:
        ordering = ['level_order']
        unique_together = ['project', 'level_order']
    
    def __str__(self):
        return f"{self.project.name} - Level {self.level_order}: {self.level_name}"


class Project(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
    ]
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    client_name = models.CharField(max_length=255, blank=True)
    municipal_reference = models.CharField(max_length=100, blank=True, help_text="Government reference number")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    budget = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    actual_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    progress = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    project_manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='managed_projects')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def get_approval_flow(self):
        """Get the approval levels for this project"""
        return self.approval_levels.all().order_by('level_order')
    
    def get_approval_levels_list(self):
        """Return list of level names for display"""
        return [level.level_name for level in self.get_approval_flow()]
    
    def update_progress(self):
        boq_items = self.boq_items.filter(level=3)
        if boq_items.exists():
            total_planned = sum(item.planned_quantity * item.rate for item in boq_items)
            total_approved = sum(item.approved_quantity * item.rate for item in boq_items)
            self.progress = (total_approved / total_planned * 100) if total_planned > 0 else 0
            self.actual_cost = total_approved
            self.save()


class BOQItem(models.Model):
    LEVEL_CHOICES = [
        (1, 'Trade / Work Category'),
        (2, 'Section'),
        (3, 'Subsection'),
        (4, 'Element / Component'),
        (5, 'Line Item'),
        (6, 'Resource'),
    ]
    
    UNIT_CHOICES = [
        ('m³', 'Cubic Meter (m³)'),
        ('m²', 'Square Meter (m²)'),
        ('m', 'Linear Meter (m)'),
        ('ton', 'Ton'),
        ('kg', 'Kilogram'),
        ('each', 'Each'),
        ('hour', 'Hour'),
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
        ('lump_sum', 'Lump Sum'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('suspended', 'Suspended'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='boq_items')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    item_code = models.CharField(max_length=50)
    description = models.TextField()
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='each')
    level = models.IntegerField(choices=LEVEL_CHOICES, default=1)
    
    planned_quantity = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    approved_quantity = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    rate = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    requires_inspection_before_work = models.BooleanField(default=False)
    requires_inspection_for_approval = models.BooleanField(default=True)
    last_inspection_date = models.DateField(null=True, blank=True)
    next_inspection_due_date = models.DateField(null=True, blank=True)
    inspection_frequency_days = models.IntegerField(default=30)
    
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_boq_items')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='updated_boq_items')
    
    class Meta:
        ordering = ['order', 'item_code']
    
    def __str__(self):
        return f"{self.item_code} - {self.description}"
    
    @property
    def planned_cost(self):
        return self.planned_quantity * self.rate
    
    @property
    def approved_cost(self):
        return self.approved_quantity * self.rate
    
    @property
    def remaining_quantity(self):
        return max(0, self.planned_quantity - self.approved_quantity)
    
    @property
    def progress_percentage(self):
        if self.planned_quantity > 0:
            return (self.approved_quantity / self.planned_quantity) * 100
        return 0.0


class DailyLog(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('partially_approved', 'Partially Approved'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='daily_logs')
    contractor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='submitted_logs')
    log_date = models.DateField()
    
    # Weather & Environment
    weather_morning = models.CharField(max_length=50, blank=True)
    weather_afternoon = models.CharField(max_length=50, blank=True)
    temperature_low = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    temperature_high = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    rainfall = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True, help_text="mm")
    wind_speed = models.IntegerField(null=True, blank=True, help_text="km/h")
    site_conditions = models.TextField(blank=True)
    
    # Work Description
    work_description = models.TextField()
    
    # Safety
    toolbox_talk_topic = models.CharField(max_length=200, blank=True)
    safety_talk_attendees = models.IntegerField(default=0)
    near_miss_count = models.IntegerField(default=0)
    near_miss_description = models.TextField(blank=True)
    first_aid_cases = models.IntegerField(default=0)
    safety_violations = models.IntegerField(default=0)
    safety_inspection_done = models.BooleanField(default=False)
    
    # Quality
    non_conformance_count = models.IntegerField(default=0)
    non_conformance_details = models.TextField(blank=True)
    rework_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    quality_checklist_used = models.CharField(max_length=200, blank=True)
    
    # Delays
    delay_type = models.CharField(max_length=50, blank=True)
    delay_duration_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    delay_reason = models.TextField(blank=True)
    workers_idle = models.IntegerField(default=0)
    eot_claimed = models.BooleanField(default=False)
    
    # Subcontractors
    subcontractors_on_site = models.TextField(blank=True, help_text="List of subcontractors and their workers")
    
    # Design & Documentation
    rfis_submitted = models.IntegerField(default=0)
    rfis_responded = models.IntegerField(default=0)
    drawing_revisions_received = models.TextField(blank=True)
    
    # Production Quantities
    concrete_poured_m3 = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rebar_installed_ton = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    excavation_m3 = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    backfill_m3 = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    formwork_m2 = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paving_m2 = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pipes_laid_m = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    painting_m2 = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Financial
    labour_cost_today = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    equipment_cost_today = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    material_cost_today = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subcontractor_cost_today = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Issues
    issues = models.TextField(blank=True)
    
    # Photos
    photos = models.JSONField(default=list, blank=True)
    photo_captions = models.JSONField(default=list, blank=True)
    
    # Next day planning
    next_day_plan = models.TextField(blank=True)
    resources_needed = models.TextField(blank=True)
    
    # Multi-level Approval Tracking
    current_level_index = models.IntegerField(default=0, help_text="Current approval level index (0-based)")
    total_approval_levels = models.IntegerField(default=0)
    
    # Status
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='draft')
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_logs')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Daily Log - {self.project.name} - {self.log_date}"
    
    def get_current_level(self):
        """Get the current approval level object"""
        levels = self.project.get_approval_flow()
        if self.current_level_index < len(levels):
            return levels[self.current_level_index]
        return None
    
    def get_next_level(self):
        """Get the next approval level object"""
        levels = self.project.get_approval_flow()
        if self.current_level_index + 1 < len(levels):
            return levels[self.current_level_index + 1]
        return None
    
    def get_levels_approved_count(self):
        """Get number of approved levels"""
        return ApprovalRecord.objects.filter(daily_log=self, action='approve').count()
    
    def get_approval_status_display(self):
        """Get approval status for UI display"""
        levels = self.project.get_approval_flow()
        approval_records = {record.level_order: record for record in self.approval_records.all()}
        
        status_list = []
        for level in levels:
            if level.level_order in approval_records:
                record = approval_records[level.level_order]
                status_list.append({
                    'level': level.level_name,
                    'level_order': level.level_order,
                    'status': record.action,
                    'approved_by': record.approver.username if record.approver else None,
                    'approved_at': record.created_at,
                    'comments': record.comments,
                    'seal_number': record.seal_number
                })
            elif self.current_level_index > level.level_order:
                status_list.append({
                    'level': level.level_name,
                    'level_order': level.level_order,
                    'status': 'approved_missing_record',
                    'approved_by': None,
                    'approved_at': None,
                    'comments': None
                })
            elif self.current_level_index == level.level_order and self.status != 'rejected':
                status_list.append({
                    'level': level.level_name,
                    'level_order': level.level_order,
                    'status': 'pending',
                    'approved_by': None,
                    'approved_at': None,
                    'comments': None
                })
            else:
                status_list.append({
                    'level': level.level_name,
                    'level_order': level.level_order,
                    'status': 'waiting',
                    'approved_by': None,
                    'approved_at': None,
                    'comments': None
                })
        
        return status_list
    
    def can_user_approve(self, user):
        """Check if user can approve at current level"""
        current_level = self.get_current_level()
        if not current_level:
            return False
        
        if current_level.required_user and current_level.required_user != user:
            return False
        
        if current_level.required_role:
            profile = getattr(user, 'profile', None)
            if not profile or profile.role != current_level.required_role:
                return False
        
        return True
    
    def approve(self, reviewer, comments, seal_number=None, ip_address=None):
        """Approve at current level and move to next"""
        current_level = self.get_current_level()
        
        if not current_level:
            raise ValueError("No approval level found")
        
        if not self.can_user_approve(reviewer):
            raise PermissionError("User not authorized to approve at this level")
        
        # Create approval record
        ApprovalRecord.objects.create(
            daily_log=self,
            level_order=current_level.level_order,
            level_name=current_level.level_name,
            approver=reviewer,
            action='approve',
            comments=comments,
            seal_number=seal_number or '',
            ip_address=ip_address
        )
        
        # Move to next level or mark as Approved
        levels = list(self.project.get_approval_flow())
        
        if self.current_level_index + 1 >= len(levels):
            self.status = 'approved'
            self.current_level_index = len(levels)
        else:
            self.current_level_index += 1
            self.status = 'partially_approved'
        
        self.save()
        
        # Update BOQ if Approved
        if self.status == 'approved':
            for entry in self.entries.all():
                entry.boq_item.approved_quantity += entry.quantity
                entry.boq_item.save()
                # Update parent items
                parent = entry.boq_item.parent
                while parent:
                    total_approved = parent.children.aggregate(total=models.Sum('approved_quantity'))['total'] or 0
                    parent.approved_quantity = total_approved
                    parent.save()
                    parent = parent.parent
            self.project.update_progress()
    
    def reject(self, reviewer, comments, ip_address=None):
        """Reject at current level"""
        current_level = self.get_current_level()
        
        ApprovalRecord.objects.create(
            daily_log=self,
            level_order=current_level.level_order if current_level else 0,
            level_name=current_level.level_name if current_level else 'Unknown',
            approver=reviewer,
            action='reject',
            comments=comments,
            ip_address=ip_address
        )
        
        self.status = 'rejected'
        self.rejection_reason = comments
        self.save()


class DailyLogEntry(models.Model):
    daily_log = models.ForeignKey(DailyLog, on_delete=models.CASCADE, related_name='entries')
    boq_item = models.ForeignKey(BOQItem, on_delete=models.CASCADE, related_name='daily_entries')
    
    quantity = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    labour_used = models.TextField(blank=True)
    equipment_used = models.TextField(blank=True)
    materials_used = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)


class ApprovalRecord(models.Model):
    """Record of each approval action"""
    ACTION_CHOICES = [
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
    ]
    
    daily_log = models.ForeignKey(DailyLog, on_delete=models.CASCADE, related_name='approval_records')
    level_order = models.IntegerField()
    level_name = models.CharField(max_length=50)
    approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='approval_actions')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    comments = models.TextField(blank=True)
    seal_number = models.CharField(max_length=50, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.daily_log} - {self.level_name}: {self.action}"


class InspectionType(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name


class InspectionPoint(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('waived', 'Waived'),
    ]
    
    boq_item = models.ForeignKey(BOQItem, on_delete=models.CASCADE, related_name='inspection_points')
    name = models.CharField(max_length=200)
    description = models.TextField()
    inspection_type = models.ForeignKey(InspectionType, on_delete=models.SET_NULL, null=True)
    
    required_before_start = models.BooleanField(default=False)
    required_during_execution = models.BooleanField(default=True)
    required_after_completion = models.BooleanField(default=False)
    
    acceptance_criteria = models.TextField(blank=True)
    reference_standard = models.CharField(max_length=100, blank=True)
    
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    order = models.IntegerField(default=0)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_inspections')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return f"{self.name} - {self.boq_item.description}"


class InspectionRecord(models.Model):
    RESULT_CHOICES = [
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('partial', 'Partial Pass'),
        ('deferred', 'Deferred'),
    ]
    
    inspection_point = models.ForeignKey(InspectionPoint, on_delete=models.CASCADE, related_name='records')
    inspection_date = models.DateTimeField(default=timezone.now)
    inspected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='inspections_performed')
    
    result = models.CharField(max_length=20, choices=RESULT_CHOICES)
    comments = models.TextField()
    measured_value = models.CharField(max_length=100, blank=True)
    
    corrective_action_required = models.BooleanField(default=False)
    corrective_action_taken = models.TextField(blank=True)
    corrected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='corrective_actions')
    corrected_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Inspection for {self.inspection_point.name} - {self.result}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.result == 'pass':
            self.inspection_point.status = 'passed'
        elif self.result == 'fail':
            self.inspection_point.status = 'failed'
        else:
            self.inspection_point.status = 'pending'
        self.inspection_point.save()


class ProjectAssignment(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='assignments')
    contractor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_projects')
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=50, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['project', 'contractor']
    
    def __str__(self):
        return f"{self.project.name} -> {self.contractor.username}"


class RFI(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('in_progress', 'In Progress'),
        ('answered', 'Answered'),
        ('closed', 'Closed'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='rfis')
    raised_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='raised_rfis')
    rfi_number = models.CharField(max_length=50)
    title = models.CharField(max_length=200)
    question = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    
    response = models.TextField(blank=True)
    responded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='responded_rfis')
    responded_at = models.DateTimeField(null=True, blank=True)
    
    attachments = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.rfi_number} - {self.title}"


class ChangeOrder(models.Model):
    TYPE_CHOICES = [
        ('addition', 'Addition'),
        ('deduction', 'Deduction'),
        ('change', 'Change'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='change_orders')
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='requested_changes')
    change_number = models.CharField(max_length=50)
    title = models.CharField(max_length=200)
    description = models.TextField()
    change_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    impact_days = models.IntegerField(default=0, help_text="Days added/removed from schedule")
    justification = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_changes')
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.change_number} - {self.title}"


class MaterialSubmittal(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('approved_as_noted', 'Approved as Noted'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='submittals')
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='submitted_submittals')
    submittal_number = models.CharField(max_length=50)
    title = models.CharField(max_length=200)
    description = models.TextField()
    manufacturer = models.CharField(max_length=100, blank=True)
    model_number = models.CharField(max_length=100, blank=True)
    specification_reference = models.CharField(max_length=100, blank=True)
    
    attachments = models.JSONField(default=list, blank=True)
    
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_submittals')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_comments = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='submitted')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.submittal_number} - {self.title}"