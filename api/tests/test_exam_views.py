import json
from datetime import time
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from dashboard.models import (
    Course, Subject, Chapter, Folder, Lesson, Exam, Question, StudentProgress
)
from django.contrib.auth import get_user_model

User = get_user_model()


class ExamListAPITestCase(TestCase):
    """Test cases for the exam_list API endpoint"""
    
    def setUp(self):
        """Set up test data for all test methods"""
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Create course
        self.course = Course.objects.create(
            course_name='Test Course',
            is_deleted=False
        )
        
        # Set as default course for user
        self.user.default_course = self.course
        self.user.save()
        
        # Create subject
        self.subject = Subject.objects.create(
            subject_name='Test Subject',
            course=self.course,
            is_deleted=False
        )
        
        # Create chapter
        self.chapter = Chapter.objects.create(
            chapter_name='Test Chapter',
            subject=self.subject,
            is_deleted=False
        )
        
        # Create folder (top-level)
        self.folder = Folder.objects.create(
            title='Test Folder',
            chapter=self.chapter,
            parent_folder=None,
            is_deleted=False
        )
        
        # Create sub-folder
        self.sub_folder = Folder.objects.create(
            title='Test Sub-Folder',
            chapter=self.chapter,
            parent_folder=self.folder,
            is_deleted=False
        )
        
        # Create lessons
        self.chapter_lesson = Lesson.objects.create(
            lesson_name='Chapter Lesson',
            chapter=self.chapter,
            folder=None,
            is_deleted=False
        )
        
        self.folder_lesson = Lesson.objects.create(
            lesson_name='Folder Lesson',
            chapter=None,
            folder=self.folder,
            is_deleted=False
        )
        
        self.sub_folder_lesson = Lesson.objects.create(
            lesson_name='Sub-Folder Lesson',
            chapter=None,
            folder=self.sub_folder,
            is_deleted=False
        )
        
        # Create exams at different levels
        self.course_exam = Exam.objects.create(
            title='Course Exam',
            course=self.course,
            subject=None,
            chapter=None,
            folder=None,
            lesson=None,
            duration=time(hour=1, minute=30),
            is_free=True,
            number_of_attempt=3,
            is_deleted=False
        )
        
        self.subject_exam = Exam.objects.create(
            title='Subject Exam',
            course=self.course,
            subject=self.subject,
            chapter=None,
            folder=None,
            lesson=None,
            duration=time(hour=0, minute=45),
            is_free=False,
            number_of_attempt=2,
            is_deleted=False
        )
        
        self.chapter_exam = Exam.objects.create(
            title='Chapter Exam',
            course=self.course,
            subject=self.subject,
            chapter=self.chapter,
            folder=None,
            lesson=None,
            duration=time(hour=0, minute=30),
            is_free=True,
            number_of_attempt=1,
            is_deleted=False
        )
        
        self.folder_exam = Exam.objects.create(
            title='Folder Exam',
            course=self.course,
            subject=self.subject,
            chapter=self.chapter,
            folder=self.folder,
            lesson=None,
            duration=time(hour=0, minute=20),
            is_free=False,
            number_of_attempt=2,
            is_deleted=False
        )
        
        self.lesson_exam = Exam.objects.create(
            title='Lesson Exam',
            course=self.course,
            subject=self.subject,
            chapter=self.chapter,
            folder=None,
            lesson=self.chapter_lesson,
            duration=time(hour=0, minute=15),
            is_free=True,
            number_of_attempt=1,
            is_deleted=False
        )
        
        # Create questions for each exam
        for exam in [self.course_exam, self.subject_exam, self.chapter_exam, 
                     self.folder_exam, self.lesson_exam]:
            for i in range(5):  # 5 questions per exam
                Question.objects.create(
                    exam=exam,
                    question_description=f'Question {i+1} for {exam.title}',
                    is_deleted=False
                )
        
        # Create student progress (attempts) for some exams
        StudentProgress.objects.create(
            student=self.user,
            exam=self.course_exam,
            total_marks=100.00,  # Required field
            marks_obtained=75.00,  # Optional but good to include
            passed=True,
            is_deleted=False
        )
        
        # Create multiple attempts for chapter exam (to test max attempts)
        StudentProgress.objects.create(
            student=self.user,
            exam=self.chapter_exam,
            total_marks=50.00,  # Required field
            marks_obtained=30.00,  # Optional but good to include
            passed=True,
            is_deleted=False
        )
        
        # Set up API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # URL for the exam list endpoint
        self.url = reverse('api-v1-exam-list')
    
    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access the endpoint"""
        # Create a new client without authentication
        client = APIClient()
        response = client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_no_default_course(self):
        """Test response when user has no default course set"""
        # Remove default course
        self.user.default_course = None
        self.user.save()
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['status'], 'error')
        self.assertEqual(response.data['message'], 'No default course set for user')
    
    def test_successful_response_structure(self):
        """Test that the response has the expected structure"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['message'], 'Exam data fetched successfully')
        
        # Check basic structure
        data = response.data['data']
        self.assertIn('course', data)
        self.assertIn('subjects', data)
        
        # Check course data
        course_data = data['course']
        self.assertEqual(course_data['course_id'], self.course.id)
        self.assertEqual(course_data['course_name'], 'Test Course')
        self.assertIn('exams', course_data)
        
        # Check subjects
        self.assertEqual(len(data['subjects']), 1)
        subject_data = data['subjects'][0]
        self.assertEqual(subject_data['subject_id'], self.subject.id)
        self.assertEqual(subject_data['subject_name'], 'Test Subject')
        self.assertIn('chapters', subject_data)
        
        # Check chapters
        self.assertEqual(len(subject_data['chapters']), 1)
        chapter_data = subject_data['chapters'][0]
        self.assertEqual(chapter_data['chapter_id'], self.chapter.id)
        self.assertEqual(chapter_data['chapter_name'], 'Test Chapter')
        self.assertIn('folders', chapter_data)
        self.assertIn('lessons', chapter_data)
        
        # Check folders
        self.assertEqual(len(chapter_data['folders']), 1)
        folder_data = chapter_data['folders'][0]
        self.assertEqual(folder_data['folder_id'], self.folder.id)
        self.assertEqual(folder_data['folder_name'], 'Test Folder')
        self.assertIn('sub_folders', folder_data)
        
        # Check sub-folders
        self.assertEqual(len(folder_data['sub_folders']), 1)
        subfolder_data = folder_data['sub_folders'][0]
        self.assertEqual(subfolder_data['folder_id'], self.sub_folder.id)
    
    def test_exam_data_content(self):
        """Test that exam data contains all required fields"""
        response = self.client.get(self.url)
        data = response.data['data']
        
        # Check course exam
        course_exams = data['course']['exams']
        self.assertEqual(len(course_exams), 1)
        exam_data = course_exams[0]
        
        self.assertEqual(exam_data['exam_id'], self.course_exam.id)
        self.assertEqual(exam_data['exam_title'], 'Course Exam')
        self.assertEqual(exam_data['duration'], '90 mins')
        self.assertEqual(exam_data['exam_is_free'], True)
        self.assertEqual(exam_data['total_questions'], 5)
        self.assertEqual(exam_data['number_of_attempt'], 3)
        self.assertEqual(exam_data['attempted_count'], 1)
    
    def test_max_attempts_filtering(self):
        """Test that exams with exhausted attempts are filtered out"""
        # Add another attempt to reach the max for chapter exam
        StudentProgress.objects.create(
            student=self.user,
            exam=self.chapter_exam,
            total_marks=50.00,
            marks_obtained=25.00,
            passed=False,
            is_deleted=False
        )
        
        response = self.client.get(self.url)
        
        # Extract chapter exams from the response
        data = response.data['data']
        chapter_exams = data['subjects'][0]['chapters'][0]['exams']
        
        # The chapter exam should be filtered out as attempts are exhausted
        chapter_exam_ids = [exam['exam_id'] for exam in chapter_exams]
        self.assertNotIn(self.chapter_exam.id, chapter_exam_ids)
    
    def test_deleted_items_filtering(self):
        """Test that deleted items are not included in the response"""
        # Mark an exam as deleted
        self.subject_exam.is_deleted = True
        self.subject_exam.save()
        
        response = self.client.get(self.url)
        
        # Extract subject exams from the response
        data = response.data['data']
        subject_exams = data['subjects'][0]['exams']
        
        # The deleted exam should not be in the response
        subject_exam_ids = [exam['exam_id'] for exam in subject_exams]
        self.assertNotIn(self.subject_exam.id, subject_exam_ids)
    
    def test_nested_structure(self):
        """Test that the nested structure of folders and lessons is correct"""
        response = self.client.get(self.url)
        data = response.data['data']
        
        # Navigate to the sub-folder
        chapter = data['subjects'][0]['chapters'][0]
        folder = chapter['folders'][0]
        subfolder = folder['sub_folders'][0]
        
        # Check that the lessons are in the right place
        chapter_lesson_ids = [lesson['lesson_id'] for lesson in chapter['lessons']]
        folder_lesson_ids = [lesson['lesson_id'] for lesson in folder['lessons']]
        subfolder_lesson_ids = [lesson['lesson_id'] for lesson in subfolder['lessons']]
        
        self.assertIn(self.chapter_lesson.id, chapter_lesson_ids)
        self.assertIn(self.folder_lesson.id, folder_lesson_ids)
        self.assertIn(self.sub_folder_lesson.id, subfolder_lesson_ids)
    
    def test_performance_optimization(self):
        """Test that the API uses optimized queries with select_related"""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        
        # Use CaptureQueriesContext to count the actual number of queries
        with CaptureQueriesContext(connection) as context:
            self.client.get(self.url)
        
        # Check that the number of queries is reasonable (less than 20)
        # The exact number may vary depending on the database state and Django version
        query_count = len(context)
        self.assertLess(query_count, 20, f"Expected fewer than 20 queries, got {query_count}")
        
        # Log the actual number of queries for reference
        print(f"Number of queries executed: {query_count}")
