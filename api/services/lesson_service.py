"""
Service layer for lesson-related business logic.
"""
from typing import Dict, List, Optional, Any
from django.db.models import Prefetch, Count, Q
from dashboard.models import (
    Chapter, Folder, Lesson, Video, PDFNote, 
    Exam, Question, VideoPause, StudentProgress
)


class LessonService:
    """Service class for lesson-related operations."""
    
    @staticmethod
    def get_video_info(video, user) -> Dict[str, Any]:
        """Extract video information including user progress."""
        video_url = video.url.split('=')[-1] if 'www.youtube.com' in video.url else video.url
        # Get video progress for current user if available
        video_progress = VideoPause.objects.filter(
            user=user, video=video, is_deleted=False
        ).first()
        
        return {
            'id': video.id,
            'title': video.title,
            'type': 'video',
            'url': video_url,
            "m3u8": video.m3u8 if video.m3u8 else "",
            "tp_stream": video.tp_stream if video.tp_stream else "",
            'is_downloadable': video.is_downloadable,
            'is_free': video.is_free,
            'minutes_watched': video_progress.minutes_watched if video_progress else "00:00:00",
            'total_duration': video_progress.total_duration if video_progress else "00:00:00"
        }
    
    @staticmethod
    def get_pdf_info(pdf_note) -> Dict[str, Any]:
        """Extract PDF note information."""
        return {
            'id': pdf_note.id,
            'title': pdf_note.title,
            'type': 'pdf',
            'file': pdf_note.file.url if pdf_note.file else None,
            'is_downloadable': pdf_note.is_downloadable,
            'is_free': pdf_note.is_free
        }
    
    @staticmethod
    def get_exam_info(exam, exam_attempted) -> Dict[str, Any]:
        """Extract exam information including question count and attempt status."""
        question_count = Question.objects.filter(exam=exam, is_deleted=False).count()
        exam_attempted_count = exam_attempted.filter(exam=exam).count()
        
        return {
            'id': exam.id,
            'title': exam.title,
            'type': 'exam',
            'exam_type': exam.exam_type if exam.exam_type else "",
            'exam_start_date': exam.start_date if exam.start_date else "",
            'exam_end_date': exam.end_date if exam.end_date else "",
            'duration': str(exam.duration) if exam.duration else None,
            'is_free': exam.is_free,
            'created': exam.created,
            'question_count': question_count,
            'number_of_attempt': exam.number_of_attempt,
            'attempted_count': exam_attempted_count
        }
    
    @staticmethod
    def get_lesson_content(lesson, user, exam_attempted) -> Dict[str, Any]:
        """Extract lesson information with all related content."""
        lesson_exams = Exam.objects.filter(lesson=lesson, is_deleted=False)
        lesson_attempted_count = exam_attempted.filter(exam__in=lesson_exams).count()
        
        lesson_info = {
            'id': lesson.id,
            'lesson_name': lesson.lesson_name,
            'type': 'lesson',
            'image': lesson.image.url if lesson.image else None,
            'description': lesson.description,
            'is_free': lesson.is_free,
            'videos': [],
            'pdf_notes': [],
            'exams': [],
            'attempted_count': lesson_attempted_count
        }
        
        # Add exams
        for exam in lesson_exams:
            lesson_info['exams'].append(
                LessonService.get_exam_info(exam, exam_attempted)
            )
        
        # Add videos
        try:
            if hasattr(lesson, 'videos'):
                videos = lesson.videos.filter(is_deleted=False)
                for video in videos:
                    lesson_info['videos'].append(
                        LessonService.get_video_info(video, user)
                    )
        except Exception:
            pass
        
        # Add PDF notes
        try:
            if hasattr(lesson, 'pdf_notes'):
                pdf_notes = lesson.pdf_notes.filter(is_deleted=False)
                for pdf_note in pdf_notes:
                    lesson_info['pdf_notes'].append(
                        LessonService.get_pdf_info(pdf_note)
                    )
        except Exception:
            pass
        
        return lesson_info
    
    @staticmethod
    def get_folder_content(folder, user, exam_attempted, include_subfolders=True) -> Dict[str, Any]:
        """Extract folder information with all related content."""
        folder_exams = Exam.objects.filter(folder=folder, is_deleted=False)
        folder_attempted_count = exam_attempted.filter(exam__in=folder_exams).count()
        
        folder_info = {
            'id': folder.id,
            'title': folder.title,
            'name': folder.name,
            'type': 'folder',
            'lesson_count': Lesson.objects.filter(folder=folder, is_deleted=False).count(),
            'subfolder_count': Folder.objects.filter(parent_folder=folder, is_deleted=False).count() if include_subfolders else 0,
            'exam_count': folder_exams.count(),
            'lessons': [],
            'sub_folders': [],
            'exams': [],
            'attempted_count': folder_attempted_count
        }
        
        # Add exams
        for exam in folder_exams:
            folder_info['exams'].append(
                LessonService.get_exam_info(exam, exam_attempted)
            )
        
        # Add lessons
        lessons_in_folder = Lesson.objects.filter(folder=folder, is_deleted=False).order_by('order')
        for lesson in lessons_in_folder:
            folder_info['lessons'].append(
                LessonService.get_lesson_content(lesson, user, exam_attempted)
            )
        
        # Add subfolders if requested
        if include_subfolders:
            sub_folders = Folder.objects.filter(parent_folder=folder, is_deleted=False).order_by('order')
            for sub_folder in sub_folders:
                folder_info['sub_folders'].append(
                    LessonService.get_folder_content(sub_folder, user, exam_attempted, include_subfolders=False)
                )
        
        return folder_info
    
    @staticmethod
    def get_chapter_content(chapter_id, user) -> Dict[str, Any]:
        """
        Get all content for a chapter including folders, lessons, and exams.
        
        Args:
            chapter_id: The ID of the chapter
            user: The current user
            
        Returns:
            Dict containing all chapter content
        """
        try:
            chapter = Chapter.objects.get(id=chapter_id, is_deleted=False)
        except Chapter.DoesNotExist:
            return None
        
        # Prefetch exam attempts for better performance
        exam_attempted = StudentProgress.objects.filter(student=user).prefetch_related('exam')
        
        # Get all top-level folders
        all_folders = Folder.objects.filter(chapter_id=chapter_id, is_deleted=False, parent_folder=None).order_by('order')
        folder_data = []
        
        # Process each top-level folder
        for folder in all_folders:
            folder_data.append(
                LessonService.get_folder_content(folder, user, exam_attempted)
            )
        
        # Get direct lessons (not in any folder)
        direct_lessons = Lesson.objects.filter(chapter_id=chapter_id, folder=None, is_deleted=False).order_by('order')
        direct_lessons_data = []
        
        for lesson in direct_lessons:
            direct_lessons_data.append(
                LessonService.get_lesson_content(lesson, user, exam_attempted)
            )
        
        # Get chapter-level exams
        chapter_exams = Exam.objects.filter(
            chapter_id=chapter_id, folder=None, lesson=None, is_deleted=False
        )
        chapter_exams_data = []
        
        for exam in chapter_exams:
            chapter_exams_data.append(
                LessonService.get_exam_info(exam, exam_attempted)
            )
        
        # Compile the response data
        response_data = {
            'chapter_name': chapter.chapter_name,
            'lesson_count': direct_lessons.count(),
            'module_count': Folder.objects.filter(chapter_id=chapter_id, parent_folder__isnull=True, is_deleted=False).count(),
            'exam_count': chapter_exams.count(),
            'folders': folder_data,
            'direct_lessons': direct_lessons_data,
            'exams': chapter_exams_data
        }
        
        return response_data
