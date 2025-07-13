from dashboard.views.imports import *

from django.utils.timezone import localtime
from rest_framework.permissions import IsAuthenticated

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def comment_list(request):
    video_id = request.data.get('video_id')
    pdf_note_id = request.data.get('pdf_note_id')
    user = request.user

    if not video_id and not pdf_note_id:
        return Response({"status": "error", "message": "Either video_id or pdf_note_id is required."}, status=status.HTTP_400_BAD_REQUEST)

    # Filter comments by the current user only
    if video_id:
        comments = Comment.objects.filter(video_id=video_id, user=user, parent_comment__isnull=True, is_deleted=False).order_by('-created')
    elif pdf_note_id:
        comments = Comment.objects.filter(pdf_note_id=pdf_note_id, user=user, parent_comment__isnull=True, is_deleted=False).order_by('-created')

    comment_data = []
    for comment in comments:
        like_count = CommentReaction.objects.filter(comment=comment, reaction='LIKE', is_deleted=False).count()
        dislike_count = CommentReaction.objects.filter(comment=comment, reaction='DISLIKE', is_deleted=False).count()

        user_reaction = CommentReaction.objects.filter(comment=comment, user=user, is_deleted=False).first()
        liked = user_reaction.reaction == 'LIKE' if user_reaction else False
        disliked = user_reaction.reaction == 'DISLIKE' if user_reaction else False

        comment_creator = comment.user
        user_image_url = comment_creator.image.url if comment_creator.image else ""

        # Get replies for this comment made by the current user only
        replies = []
        comment_replies = Comment.objects.filter(parent_comment=comment, is_deleted=False).order_by('created')
        
        for reply in comment_replies:
            reply_like_count = CommentReaction.objects.filter(comment=reply, reaction='LIKE', is_deleted=False).count()
            reply_dislike_count = CommentReaction.objects.filter(comment=reply, reaction='DISLIKE', is_deleted=False).count()
            
            reply_user_reaction = CommentReaction.objects.filter(comment=reply, user=user, is_deleted=False).first()
            reply_liked = reply_user_reaction.reaction == 'LIKE' if reply_user_reaction else False
            reply_disliked = reply_user_reaction.reaction == 'DISLIKE' if reply_user_reaction else False
            
            reply_creator = reply.user
            reply_user_image_url = reply_creator.image.url if reply_creator.image else ""
            
            reply_info = {
                'comment_id': reply.id,
                'user_id': reply_creator.id,
                'username': reply_creator.name,
                'user_image': reply_user_image_url,
                'content': reply.content,
                'created': localtime(reply.created).strftime("%Y-%m-%d %H:%M"),
                'like_count': reply_like_count,
                'dislike_count': reply_dislike_count,
                'liked': reply_liked,
                'disliked': reply_disliked
            }
            replies.append(reply_info)

        # Format comment data
        comment_info = {
            'comment_id': comment.id,
            'user_id': comment_creator.id,
            'username': comment_creator.name,
            'user_image': user_image_url,
            'content': comment.content,
            'created': localtime(comment.created).strftime("%Y-%m-%d %H:%M"),
            'like_count': like_count,         
            'dislike_count': dislike_count,
            'liked': liked,        
            'disliked': disliked,
            'replies': replies,
            'reply_count': len(replies)
        }
        comment_data.append(comment_info)

    return Response({"status": "success", "data": comment_data}, status=status.HTTP_200_OK)


@api_view(['GET'])
def comment_replies(request):
    comment_id = request.data.get('comment_id')
    
    if not comment_id:
        return Response({"status": "error", "message": "Comment ID is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        parent_comment = Comment.objects.get(id=comment_id, is_deleted=False)
        parent_like_count = CommentReaction.objects.filter(comment=parent_comment, reaction='LIKE', is_deleted=False).count()
        parent_dislike_count = CommentReaction.objects.filter(comment=parent_comment, reaction='DISLIKE', is_deleted=False).count()
        
        parent_data = {
            'comment_id': parent_comment.id,
            'user_id': parent_comment.user.id,
            'username': parent_comment.user.name,
            'user_image': parent_comment.user.image.url if parent_comment.user.image else "",
            'content': parent_comment.content,
            'created': localtime(parent_comment.created).strftime('%Y-%m-%d %H:%M'),
            'like_count': parent_like_count,
            'dislike_count': parent_dislike_count
        }
        
        replies = Comment.objects.filter(parent_comment_id=comment_id, is_deleted=False).select_related('user')
        reply_data = []
        
        for reply in replies:
            like_count = CommentReaction.objects.filter(comment=reply, reaction='LIKE', is_deleted=False).count()
            dislike_count = CommentReaction.objects.filter(comment=reply, reaction='DISLIKE', is_deleted=False).count()
            
            reply_info = {
                'comment_id': reply.id,
                'user_id': reply.user.id,
                'username': reply.user.name,
                'user_image': reply.user.image.url if reply.user.image else "",
                'content': reply.content,
               'created': localtime(reply.created).strftime('%Y-%m-%d %H:%M'),
                'like_count': like_count,
                'dislike_count': dislike_count
            }
            reply_data.append(reply_info)
            
        return Response({
            "status": "success", 
            "data": {
                "parent_comment": parent_data,
                "replies": reply_data
            }
        }, status=status.HTTP_200_OK)
        
    except Comment.DoesNotExist:
        return Response({"status": "error", "message": "Comment not found"}, status=status.HTTP_404_NOT_FOUND)



@api_view(['POST'])
@permission_classes([IsAuthenticated]) 
def comment_add(request):
    video_id = request.data.get('video_id')
    content = request.data.get('content')

    if not video_id or not content:
        return Response({"status": "error", "message": "Both video_id and content are required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        video = Video.objects.get(id=video_id)

        comment = Comment.objects.create(
            user=request.user, 
            video=video,
            content=content
        )

        response_data = {
            'comment_id': comment.id,
            'user_id': comment.user.id,
            'username': comment.user.username,
            'user_image': comment.user.image.url if comment.user.image else "",
            'content': comment.content,
            'created': comment.created.strftime('%d-%m-%Y %H:%M') 
        }

        return Response({"status": "success" ,"message":"comment added" ,"response_data":response_data}, status=status.HTTP_201_CREATED)

    except Video.DoesNotExist:
        return Response({"status": "error", "message": "Video not found."}, status=status.HTTP_404_NOT_FOUND)

  


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def comment_reply(request):
    parent_comment_id = request.data.get('parent_comment_id')
    content = request.data.get('content')

    if not parent_comment_id or not content:
        return Response({"status": "error", "message": "Parent comment ID and content are required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        parent_comment = Comment.objects.get(id=parent_comment_id)

        reply = Comment.objects.create(
            user=request.user,
            parent_comment=parent_comment,
            content=content
        )

        response_data = {
            'comment_id': reply.id if reply.id else "",
            'user_id': reply.user.id if reply.user else "",
            'username': reply.user.name if reply.user.name else "",
            'user_image': reply.user.image.url if reply.user.image else "",
            'content': reply.content if reply.content else "",
            'created': localtime(reply.created).strftime('%d-%m-%Y %H:%M') if  reply.created else "",
            # 'created': reply.created.strftime('%d-%m-%Y %H:%M'),
            # 'parent_comment_id': parent_comment.id
        }

        return Response({"status": "success", "message": "Reply added." ,"response_data":response_data}, status=status.HTTP_201_CREATED)

    except Comment.DoesNotExist:
        return Response({"status": "error", "message": "Parent comment not found."}, status=status.HTTP_404_NOT_FOUND)
    



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def comment_react(request):
    comment_id = request.data.get('comment_id')
    reaction = request.data.get('reaction')  

    if not comment_id or reaction not in ['LIKE', 'DISLIKE']:
        return Response({"status": "error", "message": "Comment ID and a valid reaction (LIKE/DISLIKE) are required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Fetch the comment
        comment = Comment.objects.get(id=comment_id)

        # Check or create the reaction for the current user and the comment
        comment_reaction, created = CommentReaction.objects.get_or_create(
            user=request.user,
            comment=comment,
            defaults={'reaction': reaction}
        )

        # If the reaction already exists, update it
        if not created:
            comment_reaction.reaction = reaction
            comment_reaction.save()

        # Calculate like and dislike counts for the specific comment
        total_likes = CommentReaction.objects.filter(comment=comment, reaction='LIKE', is_deleted=False).count()
        total_dislikes = CommentReaction.objects.filter(comment=comment, reaction='DISLIKE', is_deleted=False).count()

        return Response({
            "status": "success", 
            "message": f"Comment {reaction.lower()}d successfully.",
            "comment_id": comment.id,
            "total_likes": total_likes,         
            "total_dislikes": total_dislikes    
        }, status=status.HTTP_200_OK)

    except Comment.DoesNotExist:
        return Response({"status": "error", "message": "Comment not found."}, status=status.HTTP_404_NOT_FOUND)
