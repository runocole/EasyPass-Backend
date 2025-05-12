from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Student, Exam, Tag, Queue

class StudentAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'student_id', 'department', 'level', 'is_admin')
    fieldsets = UserAdmin.fieldsets + (
        ('Student Info', {'fields': ('student_id', 'department', 'level', 'is_admin')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Student Info', {'fields': ('student_id', 'department', 'level', 'is_admin')}),
    )

class ExamAdmin(admin.ModelAdmin):
    list_display = ('course_code', 'course_name', 'exam_date', 'start_time', 'is_active', 'created_at')
    search_fields = ('course_name', 'course_code')
    list_filter = ('exam_date', 'is_active')
    date_hierarchy = 'exam_date'

class TagAdmin(admin.ModelAdmin):
    list_display = ('tag_number', 'student', 'exam', 'created_at')
    search_fields = ('tag_number',)
    list_filter = ('exam',)

class QueueAdmin(admin.ModelAdmin):
    list_display = [
        'student',
        'exam',
        'tag_number',
        'status',
        'created_at',  
        'checked_in_at',
        'checked_out_at',  # Changed from 'completed_at' to 'checked_out_at'
        'is_active'
    ]
    list_filter = ['status', 'is_active', 'exam']
    search_fields = ['student__username', 'tag_number']
    ordering = ['-created_at']  

# Register your models
admin.site.register(Student, StudentAdmin)
admin.site.register(Exam, ExamAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Queue, QueueAdmin)