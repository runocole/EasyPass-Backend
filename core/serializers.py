from rest_framework import serializers
from .models import Student, Exam, Tag, Queue
from django.contrib.auth.password_validation import validate_password

class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'student_id', 'department', 'level', 'is_admin']
        extra_kwargs = {
            'password': {'write_only': True}
        }
class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = Student
        fields = ['username', 'email', 'password', 'confirm_password', 'first_name', 'last_name', 'student_id', 'department', 'level']

    def validate(self, attrs):
        print("Received Data:", attrs)
        # Skip password confirmation check if confirm_password is not provided
        if 'confirm_password' not in attrs:
            raise serializers.ValidationError({"confirm_password": "This field is required"}) 
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs
    
    def create(self, validated_data):
        if 'confirm_password' in validated_data:
            validated_data.pop('confirm_password')
            user = Student.objects.create_user(**validated_data)
        return user
    
class ExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = ['id', 'course_name', 'course_code', 'exam_date', 'start_time', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'

class QueueSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Queue
        fields = ['id', 'student', 'exam', 'tag_number', 'position', 'status', 'created_at', 'student_name', 'username']

    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}" if obj.student else ""

    def get_username(self, obj):
        return obj.student.username if obj.student else ""