from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import time
from django.core.validators import RegexValidator

class Student(AbstractUser):
    username_validator = RegexValidator(
        regex=r'^[0-9]{2}/[0-9]{4}$',  # Format: xx/yyyy (e.g., 21/2001)
        message="Username must be in the format xx/yyyy (e.g., 21/2001)."
    )
    
    username = models.CharField(
        max_length=10,  # Adjust based on your format
        unique=True,
        validators=[username_validator]
    )
    student_id = models.CharField(max_length=20, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    level = models.CharField(max_length=20, blank=True, null=True)
    is_admin = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.username} ({self.student_id})"

def default_exam_time():
    return timezone.now().replace(hour=9, minute=0, second=0, microsecond=0).time()

class Exam(models.Model):
    course_name = models.CharField(max_length=100)
    course_code = models.CharField(max_length=100)
    exam_date = models.DateField(default=timezone.now)
    start_time = models.TimeField(default=default_exam_time)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.course_code}: {self.course_name} - {self.exam_date} {self.start_time}"

class Tag(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='tags')
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='tags')
    tag_number = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.student.username} - {self.exam.course_code} - {self.tag_number}"

class Queue(models.Model):
    STATUS_CHOICES = (
        ('waiting', 'Waiting'),
        ('checked_in', 'Checked In'),
        ('completed', 'Completed'),
        ('checked_out', 'Checked Out'),
    )
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.SET_NULL, null=True, blank=True)
    position = models.IntegerField(null=True, blank=True)
    tag_number = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    first_check_in_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.student.username} - {self.exam.course_code} - Position: {self.position}"
    
    def save(self, *args, **kwargs):
        if self.position is None:
            # Get the highest position number for this exam
            highest_position = Queue.objects.filter(exam=self.exam).aggregate(
                models.Max('position'))['position__max']
            self.position = (highest_position or 0) + 1
            
            # Set tag number if not provided
            if not self.tag_number:
                self.tag_number = f"T{self.exam.id}-{self.position:04d}"
            
        super().save(*args, **kwargs)
    
    def check_in(self):
        self.status = 'checked_in'
        self.checked_in_at = timezone.now()
        self.save()
        return self
    
    def complete(self):
        """Mark a queue entry as completed"""
        self.checked_out_at = timezone.now()
        self.status = 'completed'
        self.is_active = False
        self.save()
        return self
    
    @classmethod
    def get_hall_capacity(cls):
        """Return the maximum hall capacity"""
        return 250  # Based on the constant in the frontend
    
    @classmethod
    def get_available_seats(cls, exam_id):
        """Calculate available seats for an exam"""
        hall_capacity = cls.get_hall_capacity()
        checked_in_count = cls.objects.filter(
            exam_id=exam_id,
            status='checked_in',
            is_active=True
        ).count()
        return max(0, hall_capacity - checked_in_count)