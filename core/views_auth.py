from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth.models import User
from .models import ContractorProfile

class ContractorRegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email')
        company_name = request.data.get('company_name')
        
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)
        
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email
        )
        
        ContractorProfile.objects.create(
            user=user,
            company_name=company_name,
            role='contractor'
        )
        
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'company_name': company_name,
            'role': 'contractor'
        }, status=status.HTTP_201_CREATED)
