from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import ProjectAssignment, Project
from django.contrib.auth.models import User

class ProjectAssignmentView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        project_id = request.data.get('project')
        contractor_id = request.data.get('contractor')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response({'error': 'Project not found'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            contractor = User.objects.get(id=contractor_id)
        except User.DoesNotExist:
            return Response({'error': 'Contractor not found'}, status=status.HTTP_404_NOT_FOUND)
        
        assignment, created = ProjectAssignment.objects.get_or_create(
            project=project,
            contractor=contractor,
            defaults={
                'start_date': start_date,
                'end_date': end_date,
                'status': 'active'
            }
        )
        
        if not created:
            return Response({'error': 'Assignment already exists'}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'id': assignment.id,
            'project_id': assignment.project.id,
            'project_name': assignment.project.name,
            'contractor_id': assignment.contractor.id,
            'contractor_name': assignment.contractor.username,
            'start_date': assignment.start_date,
            'end_date': assignment.end_date,
            'status': assignment.status
        }, status=status.HTTP_201_CREATED)
    
    def get(self, request):
        assignments = ProjectAssignment.objects.all()
        data = [{
            'id': a.id,
            'project_id': a.project.id,
            'project_name': a.project.name,
            'contractor_id': a.contractor.id,
            'contractor_name': a.contractor.username,
            'start_date': a.start_date,
            'end_date': a.end_date,
            'status': a.status
        } for a in assignments]
        return Response(data)
