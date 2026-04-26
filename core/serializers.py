from rest_framework import serializers
from .models import (
    Project, BOQItem, DailyLog, DailyLogEntry, UserProfile,
    ProjectAssignment, InspectionPoint, InspectionRecord
)

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'


class BOQItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BOQItem
        fields = '__all__'
        depth = 1


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
        fields = [
            'id', 'project', 'project_name', 'contractor', 'contractor_name',
            'log_date', 'work_description', 'status', 'submitted_at',
            'reviewed_by', 'reviewed_by_name', 'reviewed_at', 'rejection_reason',
            'weather_morning', 'weather_afternoon', 'temperature_low', 'temperature_high',
            'rainfall', 'wind_speed', 'site_conditions',
            'toolbox_talk_topic', 'safety_talk_attendees', 'near_miss_count',
            'near_miss_description', 'first_aid_cases', 'safety_violations',
            'safety_inspection_done', 'non_conformance_count', 'non_conformance_details',
            'rework_hours', 'quality_checklist_used', 'delay_type', 'delay_duration_hours',
            'delay_reason', 'workers_idle', 'eot_claimed', 'subcontractors_on_site',
            'rfis_submitted', 'rfis_responded', 'drawing_revisions_received',
            'concrete_poured_m3', 'rebar_installed_ton', 'excavation_m3', 'backfill_m3',
            'formwork_m2', 'paving_m2', 'pipes_laid_m', 'painting_m2',
            'labour_cost_today', 'equipment_cost_today', 'material_cost_today',
            'subcontractor_cost_today', 'issues', 'photos', 'photo_captions',
            'next_day_plan', 'resources_needed', 'current_level_index',
            'total_approval_levels', 'created_at', 'updated_at'
        ]


class ProjectAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectAssignment
        fields = '__all__'


class InspectionPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = InspectionPoint
        fields = '__all__'


class InspectionRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = InspectionRecord
        fields = '__all__'
