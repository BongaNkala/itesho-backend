from rest_framework import serializers
from .models import (
    UserProfile, Project, BOQItem, DailyLog, DailyLogEntry,
    ProjectAssignment, InspectionPoint, InspectionRecord,
    ApprovalLevel, ApprovalRecord, RFI, ChangeOrder, MaterialSubmittal,
    Invoice, InvoiceItem,
    ProjectComplianceRequirement,
    ContractorComplianceStatus,
    ContractorProjectAccess,
)

# ============================================================================
# USER PROFILE SERIALIZER
# ============================================================================

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'


# ============================================================================
# PROJECT SERIALIZER
# ============================================================================

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'


# ============================================================================
# BOQ ITEM SERIALIZER
# ============================================================================

class BOQItemSerializer(serializers.ModelSerializer):
    parent_id = serializers.IntegerField(source='parent.id', read_only=True, allow_null=True)
    children = serializers.SerializerMethodField()
    progress_percentage = serializers.FloatField(read_only=True)
    
    class Meta:
        model = BOQItem
        fields = [
            'id', 'project', 'item_code', 'description', 'unit', 'level',
            'planned_quantity', 'approved_quantity', 'rate',
            'parent', 'parent_id', 'children',
            'progress_percentage', 'order',
            'requires_inspection_before_work', 'requires_inspection_for_approval',
            'last_inspection_date', 'next_inspection_due_date', 'inspection_frequency_days'
        ]
    
    def get_children(self, obj):
        children = obj.children.all()
        return BOQItemSerializer(children, many=True).data


# ============================================================================
# DAILY LOG SERIALIZERS
# ============================================================================

class DailyLogEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyLogEntry
        fields = '__all__'


class DailyLogSerializer(serializers.ModelSerializer):
    contractor_name = serializers.CharField(source='contractor.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.username', read_only=True)

    class Meta:
        model = DailyLog
        fields = '__all__'


# ============================================================================
# PROJECT ASSIGNMENT SERIALIZER
# ============================================================================

class ProjectAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectAssignment
        fields = '__all__'


# ============================================================================
# INSPECTION SERIALIZERS
# ============================================================================

class InspectionPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = InspectionPoint
        fields = '__all__'


class InspectionRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = InspectionRecord
        fields = '__all__'


# ============================================================================
# APPROVAL SERIALIZERS
# ============================================================================

class ApprovalLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalLevel
        fields = '__all__'


class ApprovalRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalRecord
        fields = '__all__'


# ============================================================================
# DOCUMENT SERIALIZERS
# ============================================================================

class RFISerializer(serializers.ModelSerializer):
    class Meta:
        model = RFI
        fields = '__all__'


class ChangeOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChangeOrder
        fields = '__all__'


class MaterialSubmittalSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialSubmittal
        fields = '__all__'


# ============================================================================
# INVOICE SERIALIZERS
# ============================================================================

class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ['id', 'description', 'quantity', 'unit_price', 'amount']


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=False)
    project_name = serializers.CharField(source='project.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'project', 'project_name', 'invoice_number', 'invoice_date', 'due_date',
            'client_name', 'client_address', 'subtotal', 'tax_rate', 'tax_amount',
            'total_amount', 'notes', 'status', 'items', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
    
    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        invoice = Invoice.objects.create(**validated_data)
        
        for item_data in items_data:
            InvoiceItem.objects.create(invoice=invoice, **item_data)
        
        return invoice
    
    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', [])
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        instance.items.all().delete()
        for item_data in items_data:
            InvoiceItem.objects.create(invoice=instance, **item_data)
        
        return instance


# ============================================================================
# COMPLIANCE GATEKEEPER SERIALIZERS
# ============================================================================

class ProjectComplianceRequirementSerializer(serializers.ModelSerializer):
    """Serializer for Project Compliance Requirements"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    
    class Meta:
        model = ProjectComplianceRequirement
        fields = [
            'id', 'project', 'project_name', 'requirement_type', 'title', 'description',
            'is_mandatory', 'requires_upload', 'requires_approval', 'is_active',
            'created_at', 'updated_at'
        ]


class ContractorComplianceStatusSerializer(serializers.ModelSerializer):
    """Serializer for Contractor Compliance Status"""
    requirement_title = serializers.CharField(source='requirement.title', read_only=True)
    requirement_description = serializers.CharField(source='requirement.description', read_only=True)
    requirement_is_mandatory = serializers.BooleanField(source='requirement.is_mandatory', read_only=True)
    requirement_requires_upload = serializers.BooleanField(source='requirement.requires_upload', read_only=True)
    contractor_name = serializers.CharField(source='contractor.username', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = ContractorComplianceStatus
        fields = [
            'id', 'contractor', 'contractor_name', 'requirement', 'requirement_title',
            'requirement_description', 'requirement_is_mandatory', 'requirement_requires_upload',
            'status', 'status_display', 'submitted_at', 'approved_at', 'approved_by',
            'approved_by_name', 'document_url', 'document_name', 'notes', 'expiry_date',
            'created_at', 'updated_at'
        ]
    
    status_display = serializers.SerializerMethodField()
    
    def get_status_display(self, obj):
        return dict(ContractorComplianceStatus.STATUS_CHOICES).get(obj.status, obj.status)


class ContractorProjectAccessSerializer(serializers.ModelSerializer):
    """Serializer for Contractor Project Access"""
    contractor_name = serializers.CharField(source='contractor.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    granted_by_name = serializers.CharField(source='granted_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = ContractorProjectAccess
        fields = [
            'id', 'contractor', 'contractor_name', 'project', 'project_name',
            'is_allowed', 'granted_at', 'granted_by', 'granted_by_name',
            'notes', 'created_at', 'updated_at'
        ]


# ============================================================================
# COMPLIANCE SUMMARY SERIALIZER
# ============================================================================

class ComplianceSummarySerializer(serializers.Serializer):
    """Serializer for compliance summary response"""
    project_id = serializers.IntegerField()
    project_name = serializers.CharField()
    total_requirements = serializers.IntegerField()
    approved_count = serializers.IntegerField()
    pending_count = serializers.IntegerField()
    rejected_count = serializers.IntegerField()
    all_met = serializers.BooleanField()
    requirements = ProjectComplianceRequirementSerializer(many=True)


class ContractorComplianceStatusListSerializer(serializers.Serializer):
    """Serializer for contractor compliance status list"""
    contractor_id = serializers.IntegerField()
    contractor_name = serializers.CharField()
    company_name = serializers.CharField(allow_blank=True)
    approved_count = serializers.IntegerField()
    total_count = serializers.IntegerField()
    has_access = serializers.BooleanField()
    access_granted_at = serializers.DateTimeField(allow_null=True)