from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.db import IntegrityError
import qrcode
import time
from .models import Student, Exam, Tag, Queue
import io
import base64
from django.utils import timezone
from .models import Student, Exam, Tag, Queue
from .serializers import StudentSerializer, ExamSerializer, TagSerializer, QueueSerializer, SignupSerializer
import logging
from rest_framework.permissions import AllowAny
from .serializers import SignupSerializer, StudentSerializer
from django.contrib.auth.models import User

# Set up logging
logger = logging.getLogger(__name__)

#Sign up View
class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logger.info("Received signup data: %s", request.data)
        serializer = SignupSerializer(data=request.data)

        if serializer.is_valid():
            try:
                user = serializer.save()
                token, created = Token.objects.get_or_create(user=user)
                return Response({
                    "user": StudentSerializer(user).data,
                    "token": token.key
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                logger.error("Error creating user: %s", str(e))
                return Response({"error": "An error occurred while creating the user."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.warning("Serializer errors: %s", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        #Login View
class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)

        if user is not None:
            token, created = Token.objects.get_or_create(user=user)

            role ="admin" if user.is_superuser else "student"

        return Response({
            "user": StudentSerializer(user).data,
            "role": role,
            "token": token.key
        })

    
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        
# Student View
class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

# Exam View Set
class ExamViewSet(viewsets.ModelViewSet):
    queryset = Exam.objects.all().order_by('exam_date', 'start_time')
    serializer_class = ExamSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

#Tag View Set
class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer

#Queue View Set
class QueueViewSet(viewsets.ModelViewSet):
    queryset = Queue.objects.all()
    serializer_class = QueueSerializer
    
    def create(self, request, *args, **kwargs):
        # Get the exam and student
        exam_id = request.data.get('exam')
        student_id = request.data.get('student')
        
        try:
            # Check if student is already in an active queue
            existing_queue = Queue.objects.filter(
                student_id=student_id,
                is_active=True
            ).first()
            
            if existing_queue:
                return Response(
                    {"error": "Already in queue"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create new queue entry
            queue_entry = Queue.objects.create(
                student_id=student_id,
                exam_id=exam_id,
                is_active=True
            )
            
            return Response(self.serializer_class(queue_entry).data)
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def status(self, request):
        student_id = request.query_params.get('student')
        if not student_id:
            return Response(
                {"error": "Student ID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Find the active queue entry for this student
            queue_entry = Queue.objects.filter(
                student_id=student_id,
                is_active=True
            ).select_related('exam').latest('created_at')
            
            # Calculate position and people ahead
            position = queue_entry.position
            people_ahead = position - 1 if position > 1 else 0
            
            # Get first check-in time for this exam
            first_check_in = Queue.objects.filter(
                exam=queue_entry.exam,
                checked_in_at__isnull=False
            ).order_by('checked_in_at').first()
            
            response_data = {
                "id": queue_entry.id,
                "student": queue_entry.student_id,
                 "exam": queue_entry.exam_id,
                "exam_name": f"{queue_entry.exam.course_code}: {queue_entry.exam.course_name}",
                "tag_number": queue_entry.tag_number,
                "position": position,
                "people_ahead": people_ahead,
                "first_check_in_time": first_check_in.checked_in_at if first_check_in else None,
                "is_active": queue_entry.is_active,
                "created_at": queue_entry.created_at,
                "status": queue_entry.status
            }
            
            return Response(response_data)
            
        except Queue.DoesNotExist:
            return Response(
                {"message": "Not in queue"},
                status=status.HTTP_404_NOT_FOUND
            )
# Get Tag View
class GetTagView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        exam_id = request.data.get('exam_id')
        
        if not exam_id:
            return Response({"error": "Exam ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            exam = Exam.objects.get(id=exam_id)
        except Exam.DoesNotExist:
            return Response({"error": "Exam not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if user already has a tag for this exam
        existing_tag = Tag.objects.filter(student=request.user, exam=exam).first()
        if existing_tag:
            return Response({"tag": TagSerializer(existing_tag).data})
        
        # Generate a new tag number
        tag_count = Tag.objects.filter(exam=exam).count()
        tag_number = f"T{exam.id}-{tag_count + 1:04d}"
        
        # Create a new tag
        tag = Tag.objects.create(
            student=request.user,
            exam=exam,
            tag_number=tag_number
        )
        
        return Response({"tag": TagSerializer(tag).data})

class GenerateQRCodeView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        tag_id = request.data.get('tag_id')
        
        if not tag_id:
            return Response({"error": "Tag ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            tag = Tag.objects.get(id=tag_id, student=request.user)
        except Tag.DoesNotExist:
            return Response({"error": "Tag not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(tag.tag_number)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return Response({"qr_code": qr_code_base64})


class CheckInView(APIView):
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        # Handle GET request to check exams
        exam_id = request.query_params.get('exam')
        if not exam_id:
            return Response({"error": "Exam ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # Get check-ins for the specified exam - use Queue model with checked-in status
            checked_in_queues = Queue.objects.filter(
                exam_id=exam_id, 
                status='checked_in'
            ).select_related('student', 'exam')
            
            # Format the response data
            response_data = []
            for queue in checked_in_queues:
                response_data.append({
                    'id': queue.id,
                    'student_id': queue.student.id,
                    'student_name': f"{queue.student.first_name} {queue.student.last_name}",
                    'tag_number': queue.tag_number,
                    'check_in_time': queue.checked_in_at,
                    'check_out_time': queue.checked_out_at
                })
                
            return Response(response_data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        # Extract data from request
        username = request.data.get('username')
        exam_code = request.data.get('exam_code')
        position = request.data.get('position')
        test_mode = request.data.get('test_mode', False)
        
        # Debug log
        print(f"Check-in request: username={username}, exam_code={exam_code}, test_mode={test_mode}")
        
        # Validate required fields
        if not username or not exam_code:
            return Response({"error": "Username and exam code are required"}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Find the student - try multiple ways to be flexible
            student = None
            
            # Try by username first
            try:
                student = Student.objects.get(username=username)
            except Student.DoesNotExist:
                pass
                
            # If not found, try by other fields
            if not student:
                try:
                    # Try by ID
                    student = Student.objects.get(id=username)
                except (Student.DoesNotExist, ValueError):
                    pass
            
            # If not found, try by email
            if not student and '@' in username:
                try:
                    student = Student.objects.get(email=username)
                except Student.DoesNotExist:
                    pass
            
            # If we're in test mode or development, create a test student if not found
            if not student and (test_mode or settings.DEBUG):
                # Create a test student
                student, created = Student.objects.get_or_create(
                    username=username,
                    defaults={
                        'first_name': 'Test',
                        'last_name': 'Student',
                        'email': f"{username}@test.com"
                    }
                )
                
                if created:
                    print(f"Created test student: {username}")
            
            # Still not found? Return error
            if not student:
                return Response({
                    "error": f"Student with ID '{username}' not found",
                    "suggestion": "Check the student ID or enable test mode for development"
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Find the exam by code
            try:
                exam = Exam.objects.get(course_code=exam_code)
            except Exam.DoesNotExist:
                # In test mode, create the exam if it doesn't exist
                if test_mode or settings.DEBUG:
                    exam = Exam.objects.create(
                        course_code=exam_code,
                        course_name="Test Exam",
                        exam_date=timezone.now().date(),
                        start_time="12:00",
                        is_active=True
                    )
                    print(f"Created test exam: {exam_code}")
                else:
                    return Response({"error": f"Exam with code '{exam_code}' not found"}, 
                                  status=status.HTTP_404_NOT_FOUND)
            
            # Generate a tag number
            tag_number = f"{student.username}-{exam.course_code}-{int(time.time())}"
            
            # Create a tag
            tag = Tag.objects.create(
                student=student,
                exam=exam,
                tag_number=tag_number
            )
            
            # Check for existing queue entry
            queue_entry = Queue.objects.filter(
                student=student, 
                exam=exam,
                is_active=True
            ).first()
            
            if not queue_entry:
                # Calculate position if not provided
                if not position:
                    position = Queue.objects.filter(exam=exam).count() + 1
                
                # Create a new queue entry
                queue_entry = Queue.objects.create(
                    student=student,
                    exam=exam,
                    tag=tag,
                    position=position,
                    status='waiting',
                    tag_number=tag_number
                )
            
            # Check in the student
            if queue_entry.status == 'waiting':
                queue_entry.check_in()
                return Response({
                    "message": f"Student {student.username} checked in successfully",
                    "queue": QueueSerializer(queue_entry).data,
                    "tag_number": tag.tag_number
                })
            else:
                return Response({
                    "message": "Student already checked in", 
                    "queue": QueueSerializer(queue_entry).data
                })
                
        except Exception as e:
            print(f"Check-in error: {str(e)}")
            return Response({"error": f"Check-in failed: {str(e)}"}, 
                           status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CheckoutView(APIView):
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        # Get parameters from request
        username = request.data.get('username')
        exam_code = request.data.get('exam_code')
        tag_number = request.data.get('tag_number')
        queue_id = request.data.get('queue_id')
        
        # Log the checkout attempt for debugging
        print(f"Checkout request: {request.data}")
        
        # First try to checkout by queue_id if provided
        if queue_id:
            try:
                queue_entry = Queue.objects.get(id=queue_id)
                exam_id = queue_entry.exam_id
                
                # Complete the queue entry
                queue_entry.complete()
                
                # Calculate available seats for this exam
                available_seats = Queue.get_available_seats(exam_id)
                hall_capacity = Queue.get_hall_capacity()
                
                return Response({
                    "message": "Student checked out successfully using queue ID", 
                    "queue": QueueSerializer(queue_entry).data,
                    "available_seats": available_seats,
                    "hall_capacity": hall_capacity
                })
            except Queue.DoesNotExist:
                return Response({"error": f"Queue entry with ID {queue_id} not found"}, 
                               status=status.HTTP_404_NOT_FOUND)
        
        # Try to checkout by tag_number if provided
        if tag_number:
            try:
                queue_entry = Queue.objects.get(tag_number=tag_number, status='checked_in')
                exam_id = queue_entry.exam_id
                
                # Complete the queue entry
                queue_entry.complete()
                
                # Calculate available seats for this exam
                available_seats = Queue.get_available_seats(exam_id)
                hall_capacity = Queue.get_hall_capacity()
                
                return Response({
                    "message": "Student checked out successfully using tag number", 
                    "queue": QueueSerializer(queue_entry).data,
                    "available_seats": available_seats,
                    "hall_capacity": hall_capacity
                })
            except Queue.DoesNotExist:
                return Response({"error": f"No checked-in student found with tag number {tag_number}"}, 
                               status=status.HTTP_404_NOT_FOUND)
        
        # Fall back to username + exam_code method
        if not username or not exam_code:
            return Response({"error": "Either tag_number, queue_id, or both username and exam_code are required"}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Try to find student by username (case-insensitive)
            try:
                student = Student.objects.get(username__iexact=username)
            except Student.DoesNotExist:
                # Try by ID as fallback
                try:
                    student = Student.objects.get(id=username)
                except (Student.DoesNotExist, ValueError):
                    # Try by full name
                    try:
                        first_name = username
                        last_name = "" 
                        if " " in username:
                            parts = username.split(" ", 1)
                            first_name = parts[0]
                            last_name = parts[1]
                        
                        student = Student.objects.filter(
                            first_name__iexact=first_name,
                            last_name__iexact=last_name
                        ).first()
                        
                        if not student:
                            raise Student.DoesNotExist()
                    except:
                        return Response({"error": f"Student with username '{username}' not found"}, 
                                       status=status.HTTP_404_NOT_FOUND)
            
            # Find the exam by course code (case-insensitive)
            try:
                exam = Exam.objects.get(course_code__iexact=exam_code)
            except Exam.DoesNotExist:
                return Response({"error": f"Exam with code '{exam_code}' not found"}, 
                               status=status.HTTP_404_NOT_FOUND)
            
            # Find the queue entry
            queue_entry = Queue.objects.filter(
                student=student, 
                exam=exam,
                status='checked_in',
                is_active=True
            ).first()
            
            if not queue_entry:
                return Response({"error": "No active check-in found for this student and exam"}, 
                               status=status.HTTP_404_NOT_FOUND)
            
            # Update the queue entry
            queue_entry.complete()
            
            # Calculate available seats for this exam
            available_seats = Queue.get_available_seats(exam.id)
            hall_capacity = Queue.get_hall_capacity()
            
            return Response({
                "message": "Student checked out successfully", 
                "queue": QueueSerializer(queue_entry).data,
                "available_seats": available_seats,
                "hall_capacity": hall_capacity
            })
        except Exception as e:
            print(f"Checkout error: {str(e)}")
            return Response({"error": f"Check-out failed: {str(e)}"}, 
                           status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#Checked in View
class CheckedInStudentsView(APIView):
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        exam_id = request.query_params.get('exam_id')
        
        if not exam_id:
            return Response({"error": "Exam ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            exam = Exam.objects.get(id=exam_id)
        except Exam.DoesNotExist:
            return Response({"error": "Exam not found"}, status=status.HTTP_404_NOT_FOUND)
        
        checked_in_students = Queue.objects.filter(exam=exam, status='checked_in')
        return Response({"students": QueueSerializer(checked_in_students, many=True).data})

class NotificationView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            "notifications": [
                {
                    "id": 1,
                    "message": "Welcome to EasyPass! Your digital queue management system.",
                    "created_at": timezone.now().isoformat()
                }
            ]
        })
class ExamCapacityView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, exam_id=None):
        """Get capacity information for exams"""
        if exam_id:
            try:
                # Get the exam
                exam = Exam.objects.get(id=exam_id)
                
                # Calculate capacity for the specific exam
                available_seats = Queue.get_available_seats(exam_id)
                hall_capacity = Queue.get_hall_capacity()
                
                # Also get the waiting count
                waiting_count = Queue.objects.filter(
                    exam_id=exam_id,
                    status='waiting',
                    is_active=True
                ).count()
                
                # Get checked-in count
                checked_in_count = Queue.objects.filter(
                    exam_id=exam_id,
                    status='checked_in',
                    is_active=True
                ).count()
                
                return Response({
                    "exam_id": exam_id,
                    "course_code": exam.course_code,
                    "course_name": exam.course_name,
                    "hall_capacity": hall_capacity,
                    "available_seats": available_seats,
                    "occupied_seats": checked_in_count,
                    "waiting_count": waiting_count
                })
            except Exam.DoesNotExist:
                return Response({"error": "Exam not found"}, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Calculate capacity for all active exams
            exams = Exam.objects.filter(is_active=True)
            results = []
            
            for exam in exams:
                available_seats = Queue.get_available_seats(exam.id)
                hall_capacity = Queue.get_hall_capacity()
                
                # Get checked-in count
                checked_in_count = Queue.objects.filter(
                    exam_id=exam.id,
                    status='checked_in',
                    is_active=True
                ).count()
                
                # Get waiting count
                waiting_count = Queue.objects.filter(
                    exam_id=exam.id,
                    status='waiting',
                    is_active=True
                ).count()
                
                results.append({
                    "exam_id": exam.id,
                    "course_code": exam.course_code,
                    "course_name": exam.course_name,
                    "hall_capacity": hall_capacity,
                    "available_seats": available_seats,
                    "occupied_seats": checked_in_count,
                    "waiting_count": waiting_count
                })
            
            return Response(results)
         
# a simple test endpoint
def api_test(request):
    from django.http import JsonResponse
    return JsonResponse({"message": "API is working!"})