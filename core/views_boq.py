from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser
from .models import Project, BOQItem
from .serializers import BOQItemSerializer

class BOQItemViewSet(viewsets.ModelViewSet):
    serializer_class = BOQItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser]
    
    def get_queryset(self):
        project_id = self.request.query_params.get('project_id')
        if project_id:
            return BOQItem.objects.filter(project_id=project_id, parent__isnull=True).order_by('order', 'item_code')
        return BOQItem.objects.none()
    
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                self.perform_create(serializer)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def perform_create(self, serializer):
        serializer.save()
