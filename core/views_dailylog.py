from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from .models import DailyLog, DailyLogEntry, BOQItem
from .serializers import DailyLogSerializer, DailyLogEntrySerializer

class DailyLogViewSet(viewsets.ModelViewSet):
    serializer_class = DailyLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        project_id = self.request.query_params.get('project_id')
        if project_id:
            return DailyLog.objects.filter(project_id=project_id).order_by('-log_date')
        return DailyLog.objects.all().order_by('-log_date')
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(contractor=request.user, status='draft')
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def add_entry(self, request, pk=None):
        daily_log = self.get_object()
        boq_item_id = request.data.get('boq_item')
        quantity = request.data.get('quantity', 0)
        notes = request.data.get('notes', '')
        
        if not boq_item_id:
            return Response({'error': 'boq_item required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            boq_item = BOQItem.objects.get(id=boq_item_id)
            
            # Create entry data with daily_log field
            entry_data = {
                'daily_log': daily_log.id,
                'boq_item': boq_item.id,
                'quantity': quantity,
                'notes': notes
            }
            
            serializer = DailyLogEntrySerializer(data=entry_data)
            if serializer.is_valid():
                entry = serializer.save()
                return Response({
                    'success': True,
                    'id': entry.id,
                    'quantity': entry.quantity,
                    'notes': entry.notes
                }, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except BOQItem.DoesNotExist:
            return Response({'error': f'BOQ item {boq_item_id} not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
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
        
        # Update BOQ approved quantities from entries
        for entry in daily_log.entries.all():
            boq_item = entry.boq_item
            boq_item.approved_quantity += entry.quantity
            boq_item.save()
            
            # Update parent items
            parent = boq_item.parent
            while parent:
                total_approved = sum(child.approved_quantity for child in parent.children.all())
                parent.approved_quantity = total_approved
                parent.save()
                parent = parent.parent
        
        daily_log.status = 'approved'
        daily_log.approved_by = request.user
        daily_log.approved_at = timezone.now()
        daily_log.save()
        
        # Update project progress
        project = daily_log.project
        total_planned = 0
        total_approved = 0
        for item in project.boq_items.filter(level=3):
            total_planned += float(item.planned_quantity) * float(item.rate)
            total_approved += float(item.approved_quantity) * float(item.rate)
        project.progress = (total_approved / total_planned * 100) if total_planned > 0 else 0
        project.actual_cost = total_approved
        project.save()
        
        return Response({'status': 'approved', 'message': 'BOQ updated successfully'})
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        daily_log = self.get_object()
        daily_log.status = 'rejected'
        daily_log.reviewed_by = request.user
        daily_log.reviewed_at = timezone.now()
        daily_log.rejection_reason = request.data.get('reason', '')
        daily_log.save()
        return Response({'status': 'rejected'})
