from rest_framework import serializers
from .models import UserProfile, Project, BOQItem, DailyLog, DailyLogEntry

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
