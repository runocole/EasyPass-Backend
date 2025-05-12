from django.urls import path
from .views import (
    StudentViewSet, ExamViewSet, TagViewSet, QueueViewSet, 
    SignupView, LoginView, GetTagView, GenerateQRCodeView,
    CheckInView, CheckoutView, CheckedInStudentsView, 
    NotificationView, ExamCapacityView
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'students', StudentViewSet)
router.register(r'exams', ExamViewSet)
router.register(r'tags', TagViewSet)
router.register(r'queues', QueueViewSet)

urlpatterns = [
    # Auth endpoints
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    
    # Queue management
    path('get-tag/', GetTagView.as_view(), name='get-tag'),
    path('generate-qr/', GenerateQRCodeView.as_view(), name='generate-qr'),
    path('check-in/', CheckInView.as_view(), name='check-in'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('checked-in/', CheckedInStudentsView.as_view(), name='checked-in'),
    
    # New capacity endpoints
    path('exam-capacity/', ExamCapacityView.as_view(), name='exam-capacity'),
    path('exam-capacity/<int:exam_id>/', ExamCapacityView.as_view(), name='exam-capacity-detail'),
    
    # Notifications
    path('notifications/', NotificationView.as_view(), name='notifications'),
]

urlpatterns += router.urls