from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.db.models import Sum, Q, Count
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import (
    Project, BOQItem, DailyLog, DailyLogEntry, UserProfile,
    ProjectAssignment, InspectionPoint, InspectionRecord,
    Invoice, InvoiceItem,
    ProjectComplianceRequirement,
    ContractorComplianceStatus,
    ContractorProjectAccess,
)
from .serializers import (
    ProjectSerializer, BOQItemSerializer, DailyLogSerializer, DailyLogEntrySerializer,
    UserProfileSerializer, ProjectAssignmentSerializer, InspectionPointSerializer,
    InspectionRecordSerializer, InvoiceSerializer,
)


# ============================================================================
# JWT AUTHENTICATION
# ============================================================================

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user_id'] = self.user.id
        data['email'] = self.user.email
        data['role'] = getattr(getattr(self.user, 'profile', None), 'role', 'contractor')
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# ============================================================================
# PROJECT VIEWSET
# ============================================================================

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # If contractor, only show projects they have access to (compliance approved)
        if hasattr(user, 'profile') and user.profile.role == 'contractor':
            # Get projects where contractor has access
            access_ids = ContractorProjectAccess.objects.filter(
                contractor=user,
                is_allowed=True
            ).values_list('project_id', flat=True)
            return Project.objects.filter(id__in=access_ids)
        return Project.objects.all()
    
    def perform_create(self, serializer):
        serializer.save(project_manager=self.request.user)


# ============================================================================
# BOQ VIEWSET
# ============================================================================

class BOQItemViewSet(viewsets.ModelViewSet):
    serializer_class = BOQItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        project_id = self.request.query_params.get('project_id')
        if project_id:
            return BOQItem.objects.filter(project_id=project_id, parent__isnull=True).order_by('item_code')
        return BOQItem.objects.filter(parent__isnull=True).order_by('item_code')
    
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
    
    @action(detail=False, methods=['get'])
    def tree(self, request):
        project_id = request.query_params.get('project_id')
        if project_id:
            roots = BOQItem.objects.filter(project_id=project_id, parent__isnull=True).order_by('item_code')
            serializer = self.get_serializer(roots, many=True)
            return Response(serializer.data)
        return Response([])


# ============================================================================
# DAILY LOG VIEWSET
# ============================================================================

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
        
        if hasattr(user, 'profile') and user.profile.role == 'contractor':
            return DailyLog.objects.filter(contractor=user).order_by('-log_date')
        else:
            return DailyLog.objects.all().order_by('-log_date')
    
    def create(self, request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            status_value = request.data.get('status', 'submitted')
            serializer.save(
                contractor=user,
                status=status_value
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
        daily_log.reviewed_by = request.user
        daily_log.reviewed_at = timezone.now()
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


# ============================================================================
# INVOICE VIEWSET
# ============================================================================

class InvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        project_id = self.request.query_params.get('project_id')
        
        queryset = Invoice.objects.all()
        
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        if not user.is_superuser:
            queryset = queryset.filter(created_by=user)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# ============================================================================
# COMPLIANCE VIEWSET - FIXED WITH CORRECT URL PATHS
# ============================================================================

class ComplianceViewSet(viewsets.ViewSet):
    """
    ViewSet for Compliance Gatekeeper operations.
    """
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='contractor-requirements')
    def contractor_requirements(self, request):
        """
        Get all compliance requirements for a contractor for a specific project.
        """
        project_id = request.query_params.get('project_id')
        if not project_id:
            return Response(
                {'error': 'Project ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response(
                {'error': 'Project not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        user = request.user

        # Check if user is assigned to this project
        is_assigned = ProjectAssignment.objects.filter(
            project=project,
            contractor=user
        ).exists()

        if not is_assigned:
            return Response(
                {'error': 'You are not assigned to this project'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get all active requirements
        requirements = ProjectComplianceRequirement.objects.filter(
            project=project,
            is_active=True
        ).order_by('-is_mandatory', 'title')

        result = []
        for req in requirements:
            # Get or create status for this contractor
            status_obj, created = ContractorComplianceStatus.objects.get_or_create(
                contractor=user,
                requirement=req,
                defaults={'status': 'pending'}
            )

            result.append({
                'id': req.id,
                'title': req.title,
                'description': req.description,
                'requirement_type': req.requirement_type,
                'is_mandatory': req.is_mandatory,
                'requires_upload': req.requires_upload,
                'requires_approval': req.requires_approval,
                'status': status_obj.status,
                'status_display': dict(ContractorComplianceStatus.STATUS_CHOICES).get(status_obj.status, 'Pending'),
                'document_url': status_obj.document_url,
                'document_name': status_obj.document_name,
                'submitted_at': status_obj.submitted_at,
                'approved_at': status_obj.approved_at,
                'notes': status_obj.notes,
                'expiry_date': status_obj.expiry_date,
                'can_submit': status_obj.status in ['pending', 'rejected']
            })

        # Calculate stats
        total_count = len(result)
        approved_count = sum(1 for r in result if r['status'] == 'approved')
        pending_count = sum(1 for r in result if r['status'] in ['pending', 'submitted'])
        rejected_count = sum(1 for r in result if r['status'] == 'rejected')
        all_met = approved_count == total_count and total_count > 0

        return Response({
            'project_id': project.id,
            'project_name': project.name,
            'requirements': result,
            'total_count': total_count,
            'approved_count': approved_count,
            'pending_count': pending_count,
            'rejected_count': rejected_count,
            'all_met': all_met,
        })

    @action(detail=False, methods=['post'], url_path='submit-requirement')
    def submit_requirement(self, request):
        """
        Submit a compliance requirement for approval.
        """
        requirement_id = request.data.get('requirement_id')
        notes = request.data.get('notes', '')
        document_url = request.data.get('document_url', '')
        document_name = request.data.get('document_name', '')

        if not requirement_id:
            return Response(
                {'error': 'Requirement ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            requirement = ProjectComplianceRequirement.objects.get(id=requirement_id)
        except ProjectComplianceRequirement.DoesNotExist:
            return Response(
                {'error': 'Requirement not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        user = request.user

        # Get or create status
        status_obj, created = ContractorComplianceStatus.objects.get_or_create(
            contractor=user,
            requirement=requirement
        )

        # Update status
        status_obj.status = 'submitted'
        status_obj.submitted_at = timezone.now()
        if notes:
            status_obj.notes = notes
        if document_url:
            status_obj.document_url = document_url
        if document_name:
            status_obj.document_name = document_name
        status_obj.save()

        # Check if all requirements are now met
        all_requirements = ProjectComplianceRequirement.objects.filter(
            project=requirement.project,
            is_active=True
        )

        all_statuses = ContractorComplianceStatus.objects.filter(
            contractor=user,
            requirement__in=all_requirements
        )

        all_approved = all(
            s.status == 'approved' for s in all_statuses
        ) if all_statuses.count() == all_requirements.count() else False

        # Grant access if all requirements are approved
        if all_approved:
            access, created = ContractorProjectAccess.objects.get_or_create(
                contractor=user,
                project=requirement.project
            )
            if not access.is_allowed:
                access.is_allowed = True
                access.granted_at = timezone.now()
                access.save()

        return Response({
            'status': status_obj.status,
            'all_approved': all_approved,
            'message': 'Requirement submitted successfully'
        })

    @action(detail=False, methods=['get'], url_path='check-access')
    def check_access(self, request):
        """
        Check if the current user has access to a project.
        """
        project_id = request.query_params.get('project_id')
        if not project_id:
            return Response(
                {'error': 'Project ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response(
                {'error': 'Project not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        user = request.user

        # Check if user has access
        access = ContractorProjectAccess.objects.filter(
            contractor=user,
            project=project
        ).first()

        if access and access.is_allowed:
            return Response({
                'has_access': True,
                'granted_at': access.granted_at
            })

        # Check if all requirements are met
        requirements = ProjectComplianceRequirement.objects.filter(
            project=project,
            is_active=True
        )

        if not requirements.exists():
            return Response({
                'has_access': True,
                'message': 'No compliance requirements'
            })

        statuses = ContractorComplianceStatus.objects.filter(
            contractor=user,
            requirement__in=requirements
        )

        all_approved = all(
            s.status == 'approved' for s in statuses
        ) if statuses.count() == requirements.count() else False

        return Response({
            'has_access': all_approved,
            'requirements_count': requirements.count(),
            'approved_count': statuses.filter(status='approved').count()
        })

    @action(detail=False, methods=['post'], url_path='approve-requirement')
    def approve_requirement(self, request):
        """
        Admin: Approve a compliance requirement submission.
        """
        status_id = request.data.get('status_id')
        if not status_id:
            return Response(
                {'error': 'Status ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            status_obj = ContractorComplianceStatus.objects.get(id=status_id)
        except ContractorComplianceStatus.DoesNotExist:
            return Response(
                {'error': 'Status not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        user = request.user
        if not user.is_superuser:
            return Response(
                {'error': 'Only superusers can approve requirements'},
                status=status.HTTP_403_FORBIDDEN
            )

        status_obj.status = 'approved'
        status_obj.approved_at = timezone.now()
        status_obj.approved_by = user
        status_obj.save()

        # Check if all requirements for this project are now approved
        all_requirements = ProjectComplianceRequirement.objects.filter(
            project=status_obj.requirement.project,
            is_active=True
        )

        all_statuses = ContractorComplianceStatus.objects.filter(
            contractor=status_obj.contractor,
            requirement__in=all_requirements
        )

        all_approved = all(
            s.status == 'approved' for s in all_statuses
        ) if all_statuses.count() == all_requirements.count() else False

        if all_approved:
            access, created = ContractorProjectAccess.objects.get_or_create(
                contractor=status_obj.contractor,
                project=status_obj.requirement.project
            )
            if not access.is_allowed:
                access.is_allowed = True
                access.granted_at = timezone.now()
                access.granted_by = user
                access.save()

        return Response({
            'status': 'approved',
            'all_approved': all_approved,
            'message': 'Requirement approved successfully'
        })

    @action(detail=False, methods=['get'], url_path='project-summary')
    def project_summary(self, request):
        """
        Get a summary of compliance status for a project (for project managers).
        """
        project_id = request.query_params.get('project_id')
        if not project_id:
            return Response(
                {'error': 'Project ID required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        project = get_object_or_404(Project, id=project_id)
        
        # Check if user is project manager or superuser
        user = request.user
        if not (user.is_superuser or project.project_manager == user):
            return Response(
                {'error': 'You do not have permission to view compliance summary for this project'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        requirements = ProjectComplianceRequirement.objects.filter(
            project=project,
            is_active=True
        )
        
        # Get all contractors assigned to this project
        contractors = ProjectAssignment.objects.filter(
            project=project
        ).select_related('contractor')
        
        summary = {
            'project_id': project.id,
            'project_name': project.name,
            'requirements': [],
            'contractors': [],
        }
        
        # Requirements summary
        for req in requirements:
            status_counts = ContractorComplianceStatus.objects.filter(
                requirement=req
            ).values('status').annotate(count=Count('id'))
            
            counts = {s['status']: s['count'] for s in status_counts}
            
            summary['requirements'].append({
                'id': req.id,
                'title': req.title,
                'is_mandatory': req.is_mandatory,
                'total_contractors': contractors.count(),
                'approved_count': counts.get('approved', 0),
                'pending_count': counts.get('pending', 0) + counts.get('submitted', 0),
                'rejected_count': counts.get('rejected', 0),
            })
        
        # Contractors compliance status
        for assignment in contractors:
            contractor = assignment.contractor
            statuses = ContractorComplianceStatus.objects.filter(
                contractor=contractor,
                requirement__in=requirements
            )
            
            approved = statuses.filter(status='approved').count()
            total = requirements.count()
            
            access = ContractorProjectAccess.objects.filter(
                contractor=contractor,
                project=project
            ).first()
            
            summary['contractors'].append({
                'id': contractor.id,
                'name': contractor.username,
                'company_name': getattr(contractor, 'profile', None) and contractor.profile.company_name or '',
                'approved_count': approved,
                'total_count': total,
                'has_access': access and access.is_allowed,
                'access_granted_at': access and access.granted_at,
            })
        
        return Response(summary)


# ============================================================================
# DASHBOARD STATS VIEW
# ============================================================================

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


# ============================================================================
# PENDING APPROVALS VIEW
# ============================================================================

class PendingApprovalsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        pending_logs = DailyLog.objects.filter(status='submitted').order_by('-submitted_at')
        serializer = DailyLogSerializer(pending_logs, many=True)
        return Response(serializer.data)


# ============================================================================
# CONTRACTOR PROJECTS VIEW
# ============================================================================

class ContractorProjectsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        projects = Project.objects.filter(assignments__contractor=request.user)
        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data)


# ============================================================================
# CONTRACTOR BOQ VIEW
# ============================================================================

class ContractorBOQView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, project_id):
        boq_items = BOQItem.objects.filter(project_id=project_id, parent__isnull=True).order_by('order', 'item_code')
        serializer = BOQItemSerializer(boq_items, many=True)
        return Response(serializer.data)


# ============================================================================
# MONTHLY INSPECTIONS VIEW
# ============================================================================

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