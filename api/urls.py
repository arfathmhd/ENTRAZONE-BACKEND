
from django.urls import path
from django.contrib.auth import views as auth_views
from rest_framework_simplejwt import views as jwt_views
from api.views import (
  authentication,
  student,
  course,
  subject,
  chapter,
  lesson,
  comment,
  exam,
  talenthunt,
  home,
  notification,
  schedule,
  folder,
  video,
  live_class,
  booking,

)

urlpatterns = [
    # ==================================== Authentication ====================================== #
    path("v1/register/", authentication.register, name="api-v1-login"),
    path("v1/logout/", auth_views.LogoutView.as_view(), name="api-v1-logout"),
    path("v1/otp-auth/", authentication.otp_auth, name="api-v1-otp_auth"),  
    path("v1/signup-otp-auth/", authentication.otp_signup_verify, name="api-v1-signup-otp_auth"),

    path("v1/otp-login-verify/", authentication.otp_login_verify, name="api-v1-otp_login_verify"),
    path("v1/resend-otp/", authentication.resend_otp, name="api-v1-resend_otp"),
    path("v1/refresh-token/",jwt_views.TokenRefreshView.as_view(), name="api-v1-refresh_token"),

    path('v1/course-list/', course.course_list, name='api-v1-course-list'),
    path('v1/course-select/', course.course_select, name='api-v1-course-select'),
    
    # ==================================== Profile ============================================= #

    path('v1/get-profile/', student.get_profile, name='api-v1-get-profile'),
    path('v1/update-profile/', student.update_profile, name='api-v1-update-profile'),
    path('v1/result-result/', exam.get_exam_results, name='api-v1-result-result'),

    # ==================================== Home ============================================= #
    path('v1/home/', home.home, name='api-v1-home'),   
    path('v1/search/', home.search_courses, name='api-v1-search'),   
    path('v1/change-default-course/', home.update_default_course, name='api-v1-change-default-course'),
    path('v1/current-affairs/', home.currentaffairs, name='api-v1-current-affairs'),


    # ==================================== Notification ========================================= #

    path('v1/unread_notifications/', notification.unread_notifications, name='api-v1-notification-list'),

    # ==================================== My Class ============================================ #
   
    #insted of this api re-use home api subscribed_courses list 
    path('v1/subscribed/course-list/', course.subscribed_course, name='api-v1-subscribed-course-list'), 
    
    #this api re-use in two way my class and passing course id and show subjects  
    path('v1/course/subject-list/', course.course_subjects, name='api-v1-course-subject-list'), 


    # ==================================== Content ============================================= #
   

    
    path('v1/chapter-list/', chapter.chapter_list, name='api-v1-chapter-list'),
    path('v1/lesson-list/', lesson.lesson_list, name='api-v1-lesson-list'),
    path('v1/tpstream-token/', chapter.tpstream_token, name='api-v1-tpstream-token'),

    # ==================================== Comment ============================================= #
   
    path('v1/comment-list/', comment.comment_list, name='api-v1-comment-list'),
    path('v1/comment-replies/', comment.comment_replies, name='api-v1-comment-replies'),
    path('v1/comment-add/', comment.comment_add, name='api-v1-comment-add'),
    path('v1/comment-like/', comment.comment_react, name='api-v1-comment-like'),
    path('v1/comment-react/', comment.comment_reply, name='api-v1-comment-react'),

    # ==================================== Talent Hunt ========================================= #

    path('v1/talent-hunt-list/', talenthunt.talenthunt_list, name='api-v1-talent-hunt-list'),
    path('v1/talent-hunt/subject-list/', talenthunt.talenthunt_subject_list, name='api-v1-talent-hunt-subject-list'),
    path('v1/talent-hunt/level/', talenthunt.talenthunt_levels, name='api-v1-talent-hunt-level-list'),
    path('v1/talent-hunt/question-list/', talenthunt.talenthunt_question, name='api-v1-talent-hunt-level-list'),
    path('v1/talent-hunt/answer-submission/', talenthunt.talenthunt_answer_submission, name='api-v1-talent-hunt-answer-submission'),
    
    # both exam and talent hunt have same result api
    path('v1/result/', talenthunt.get_result, name='api-v1-talent-hunt-result'),


    # ==================================== Exam ============================================= #

    path('v1/exam-list/', exam.exam_list, name='api-v1-exam-list'),


    # no more use
    # path('v1/course/exam-list/', exam.course_exam_list, name='api-v1-course-exam-list'), 
    
    path('v1/exam/question-list/', exam.exam_question, name='api-v1-exam-question-list'),
    path('v1/exam/answer-submission/', exam.exam_answer_submission, name='api-v1-exam-answer-submission'),
    path('v1/exam/report-chart/', exam.exam_report_chart, name='api-v1-exam-report-chart'),


    # ==================================== Schedule ============================================= #

    path('v1/schedule-list/', schedule.schedule_list, name='api-v1-schedule-list'),


    # ==================================== Question Report ============================================= #

    path('v1/question-report/', exam.report, name='api-v1-question-report'),
    path('v1/folder/', folder.folder_detail, name='api-v1-folder'),



    # # ==================================== Video Pause and Resume ============================================= #


    path('v1/video-control/', video.video_pause_resume, name='api-v1-video-control'),
    path('v1/video-rating/', video.VideoRatingView.as_view(), name='api-v1-video-rating'),
    
    path('v1/live-class/', live_class.live_class, name='api-v1-live-class'),

    # path('v1/booking-session/', booking.booking_session, name='api-v1-booking-session'),
    # path('v1/current-slots/', booking.current_slots, name='api-v1-current-slots'),

]