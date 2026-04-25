from rest_framework import serializers
from .models import (
    Project, BOQItem, DailyLog, DailyLogEntry, UserProfile, 
    ProjectAssignment, ApprovalLevel, ApprovalRecord,
    InspectionType, InspectionPoint, InspectionRecord
)

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'


class ProjectSerializer(serializers.ModelSerializer):
    project_manager_name = serializers.CharField(source='project_manager.username', read_only=True)
    approval_flow = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = '__all__'
    
    def get_approval_flow(self, obj):
        levels = obj.get_approval_flow()
        return [{'level': level.level_order, 'name': level.level_name, 'required_role': level.required_role} for level in levels]


class ApprovalLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalLevel
        fields = '__all__'


class ApprovalRecordSerializer(serializers.ModelSerializer):
    approver_name = serializers.CharField(source='approver.username', read_only=True)
    
    class Meta:
        model = ApprovalRecord
        fields = '__all__'
        read_only_fields = ['created_at']


class BOQItemSerializer(serializers.ModelSerializer):
    planned_cost = serializers.SerializerMethodField()
    approved_cost = serializers.SerializerMethodField()
    remaining_quantity = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()
    level_name = serializers.SerializerMethodField()
    
    class Meta:
        model = BOQItem
        fields = '__all__'
    
    def get_planned_cost(self, obj):
        return float(obj.planned_quantity * obj.rate)
    
    def get_approved_cost(self, obj):
        return float(obj.approved_quantity * obj.rate)
    
    def get_remaining_quantity(self, obj):
        return float(max(0, obj.planned_quantity - obj.approved_quantity))
    
    def get_progress_percentage(self, obj):
        if obj.planned_quantity > 0:
            return float((obj.approved_quantity / obj.planned_quantity) * 100)
        return 0.0
    
    def get_children(self, obj):
        if obj.children.exists():
            return BOQItemSerializer(obj.children.all(), many=True).data
        return []
    
    def get_level_name(self, obj):
        choices = dict(BOQItem.LEVEL_CHOICES)
        return choices.get(obj.level, f'Level {obj.level}')


class DailyLogEntrySerializer(serializers.ModelSerializer):
    boq_item_description = serializers.CharField(source='boq_item.description', read_only=True)
    boq_item_code = serializers.CharField(source='boq_item.item_code', read_only=True)
    
    class Meta:
        model = DailyLogEntry
        fields = '__all__'


class DailyLogSerializer(serializers.ModelSerializer):
    entries = DailyLogEntrySerializer(many=True, read_only=True)
    contractor_name = serializers.CharField(source='contractor.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.username', read_only=True)
    approval_status = serializers.SerializerMethodField()
    current_level_name = serializers.SerializerMethodField()
    next_level_name = serializers.SerializerMethodField()
    
    class Meta:
        model = DailyLog
        fields = '__all__'
    
    def get_approval_status(self, obj):
        return obj.get_approval_status_display()
    
    def get_current_level_name(self, obj):
        level = obj.get_current_level()
        return level.level_name if level else None
    
    def get_next_level_name(self, obj):
        level = obj.get_next_level()
        return level.level_name if level else None


class ProjectAssignmentSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    contractor_name = serializers.CharField(source='contractor.username', read_only=True)
    
    class Meta:
        model = ProjectAssignment
        fields = '__all__'


class InspectionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = InspectionType
        fields = '__all__'


class InspectionPointSerializer(serializers.ModelSerializer):
    inspection_type_name = serializers.CharField(source='inspection_type.name', read_only=True)
    boq_item_description = serializers.CharField(source='boq_item.description', read_only=True)
    
    class Meta:
        model = InspectionPoint
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class InspectionRecordSerializer(serializers.ModelSerializer):
    inspected_by_name = serializers.CharField(source='inspected_by.username', read_only=True)
    inspection_point_name = serializers.CharField(source='inspection_point.name', read_only=True)
    
    class Meta:
        model = InspectionRecord
        fields = '__all__'
        read_only_fields = ['created_at']
