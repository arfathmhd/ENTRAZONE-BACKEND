
# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def current_slots(request):
#     default_course = request.user.default_course
#     subjects = Subject.objects.filter(course=default_course, is_deleted=False)

#     start_of_week = timezone.now() - timezone.timedelta(days=timezone.now().weekday())
#     end_of_week = start_of_week + timezone.timedelta(days=7)

#     # Fetch slots related to the course
#     slots = Slot.objects.filter(course=default_course, is_deleted=False)

#     # Aggregate slot availability
#     slot_summary = slots.aggregate(
#         total_available_sessions=Sum('available_sessions'),
#         total_total_slots=Sum('total_slots')
#     )

#     available_slots = slot_summary.get('total_available_sessions', 0)
#     total_slots = slot_summary.get('total_total_slots', 0)

#     response_data = {
#         'default_course': default_course.course_name,
#         'subjects': []
#     }

#     for subject in subjects:
#         # Get chapters for the subject
#         chapters = Chapter.objects.filter(subject=subject, is_deleted=False)

#         # Get slots for this subject
#         subject_slots = slots.filter(subject=subject)

#         subject_slot_summary = subject_slots.aggregate(
#             available_sessions=Sum('available_sessions'),
#             total_slots=Sum('total_slots')
#         )

#         response_data['subjects'].append({
#             'subject_name': subject.subject_name,
#             'subject_id': subject.id,
#             'available_slots': subject_slot_summary.get('available_sessions', 0),
#             'total_slots': subject_slot_summary.get('total_slots', 0),
#             'chapters': [
#                 {
#                     'chapter_name': chapter.chapter_name,
#                     'chapter_id': chapter.id
#                 }
#                 for chapter in chapters
#             ]
#         })

#     return Response({
#         "status": "success",
#         "data": response_data,
#     }, status=status.HTTP_200_OK)


# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def booking_session(request):
#     subject_id = request.data.get('subject_id')
#     chapter_id = request.data.get('chapter_id')
#     lesson_id = request.data.get('lesson_id')
#     duration = request.data.get('duration')
#     date = request.data.get('date')
#     time_slot = request.data.get('time_slot')
#     agenda = request.data.get('agenda')

#     # Correct the filter to find slots with available sessions greater than 0
#     slot = Slot.objects.filter(
#         subject_id=subject_id,
#         # available_sessions__gt=0  # Use gt (greater than) to find slots with available sessions
#     ).first()
#     if not slot:
#         return Response({"status": "error", "message": "No doubt clearing session for this subject."}, status=status.HTTP_200_OK)
   
#     if slot.available_sessions < 0:
#         return Response({"status": "error", "message": "No available slot available."}, status=status.HTTP_200_OK)
    
#     booking = Booking.objects.create(
#         user=request.user,
#         subject_id=subject_id,
#         lesson_id=lesson_id, 
#         chapter_id=chapter_id, 
#         slot=slot,
#         description=agenda
#     )

#     # Decrement the available sessions only if a slot is found
#     slot.available_sessions -= 1
#     slot.save()

#     return Response({
#         "status": "success",
#         "data": {
#             "booking_id": booking.id,
#             "subject": booking.subject.subject_name,
#             "date": booking.slot.date,
#             # "time_slot": booking.slot.start_time,
#             "description": booking.description
#         }
#     }, status=status.HTTP_200_OK)