from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.db.models import Sum, Sum
from django.utils import timezone
from .models import (
    Project, BOQItem, DailyLog, DailyLogEntry, UserProfile,
    ProjectAssignment, InspectionPoint, InspectionRecord
)
from .serializers import (
    ProjectSerializer, BOQItemSerializer, DailyLogSerializer, DailyLogEntrySerializer,
    UserProfileSerializer, ProjectAssignmentSerializer, InspectionPointSerializer, InspectionRecordSerializer
)

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user_id'] = self.user.id
        data['email'] = self.user.email
        data['role'] = getattr(getattr(self.user, 'profile', None), 'role', 'contractor')
        return data

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Project.objects.all()
    
    def perform_create(self, serializer):
        serializer.save(project_manager=self.request.user)


class BOQItemViewSet(viewsets.ModelViewSet):
    serializer_class = BOQItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        project_id = self.request.query_params.get('project_id')
        if project_id:
            return BOQItem.objects.filter(project_id=project_id, parent__isnull=True).order_by('order', 'item_code')
        return BOQItem.objects.none()
    
    def create(self, request, *args, **kwargs):
        user = request.user
        if not hasattr(user, 'profile') or user.profile.role != 'pm':
            return Response({'error': 'Only Project Manager can create BOQ'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        user = request.user
        if not hasattr(user, 'profile') or user.profile.role != 'pm':
            return Response({'error': 'Only Project Manager can edit BOQ'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)


class DailyLogViewSet(viewsets.ModelViewSet):
    serializer_class = DailyLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        project_id = self.request.query_params.get('project_id')
        
        if project_id:
            if hasattr(user, 'profile') and user.profile.role == 'contractor':
                return DailyLog.objects.filter(project_id=project_id, contractor=user).order_by('-log_date')
            else:
                return DailyLog.objects.filter(project_id=project_id).order_by('-log_date')
        
        # If no project_id, return all logs (for dashboard/submissions page)
        if hasattr(user, 'profile') and user.profile.role == 'contractor':
            return DailyLog.objects.filter(contractor=user).order_by('-log_date')
        else:
            return DailyLog.objects.all().order_by('-log_date')
    
    def create(self, request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                contractor=user,
                status='draft'
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def add_entry(self, request, pk=None):
        daily_log = self.get_object()
        serializer = DailyLogEntrySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(daily_log=daily_log)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        daily_log = self.get_object()
        daily_log.status = 'submitted'
        daily_log.submitted_at = timezone.now()
        daily_log.save()
        return Response({'status': 'submitted'})
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        daily_log = self.get_object()
        daily_log.status = 'approved'
        daily_log.approved_by = request.user
        daily_log.approved_at = timezone.now()
        daily_log.save()
        return Response({'status': 'approved'})
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        daily_log = self.get_object()
        reason = request.data.get('reason', 'No reason provided')
        daily_log.status = 'rejected'
        daily_log.rejection_reason = reason
        daily_log.save()
        return Response({'status': 'rejected'})


class DashboardStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        projects = Project.objects.all()
        
        total_budget = sum(float(p.budget) for p in projects)
        total_actual = sum(float(p.actual_cost) for p in projects)
        total_projects = projects.count()
        active_projects = projects.filter(status='active').count()
        pending_count = DailyLog.objects.filter(status='submitted').count()
        
        return Response({
            'total_projects': total_projects,
            'active_projects': active_projects,
            'total_budget': total_budget,
            'total_actual': total_actual,
            'overall_progress': (total_actual / total_budget * 100) if total_budget > 0 else 0,
            'pending_approvals': pending_count
        })


class PendingApprovalsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        pending_logs = DailyLog.objects.filter(status='submitted').order_by('-submitted_at')
        serializer = DailyLogSerializer(pending_logs, many=True)
        return Response(serializer.data)


class ContractorProjectsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        projects = Project.objects.filter(assignments__contractor=request.user)
        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data)


class ContractorBOQView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, project_id):
        boq_items = BOQItem.objects.filter(project_id=project_id, parent__isnull=True).order_by('order', 'item_code')
        serializer = BOQItemSerializer(boq_items, many=True)
        return Response(serializer.data)


class MonthlyInspectionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        project_id = request.query_params.get('project_id')
        month = request.query_params.get('month')
        
        if not project_id or not month:
            return Response({'error': 'Missing parameters'}, status=400)
        
        year, month_num = map(int, month.split('-'))
        
        inspections = InspectionRecord.objects.filter(
            inspection_point__boq_item__project_id=project_id,
            inspection_date__year=year,
            inspection_date__month=month_num
        ).select_related('inspection_point', 'inspection_point__boq_item')
        
        data = [{
            'id': insp.id,
            'inspection_point_name': insp.inspection_point.name,
            'boq_item_description': insp.inspection_point.boq_item.description,
            'result': insp.result,
            'comments': insp.comments,
            'inspection_date': insp.inspection_date,
            'corrective_action_required': insp.corrective_action_required
        } for insp in inspections]
        
        return Response(data)