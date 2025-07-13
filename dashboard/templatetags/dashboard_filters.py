from django import template
from dashboard.models import Exam
from django.db.models import Avg
register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Custom template filter to access dictionary items by key.
    Usage: {{ my_dict|get_item:key_variable }}
    """
    if dictionary is None:
        return None
    
    try:
        return dictionary.get(key)
    except (KeyError, AttributeError, TypeError):
        return None


@register.filter
def count_active(batches):
    return len([b for b in batches if not b.is_deleted])


@register.filter
def calculate_percentage(paid, total):
    """
    Calculate percentage of paid amount from total amount.
    Usage: {{ paid_amount|calculate_percentage:total_amount }}
    """
    try:
        if float(total) > 0:
            percentage = (float(paid) / float(total)) * 100
            return int(percentage)
        return 0
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def exam_type_choices(_=None):
    exam_type = Exam.EXAM_TYPE_CHOICES
    return exam_type

@register.filter
def percentage(value, total):
    """
    Calculate percentage of one value from another.
    Usage: {{ value|percentage:total }}
    """
    try:
        if float(total) > 0:
            percentage = (float(value) / float(total)) * 100
            return round(percentage, 1)
        return 0
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def passed_exams(exam_details):
    """
    Count the number of passed exams in a list of exam details.
    Usage: {{ exam_details|passed_exams }}
    """
    if not exam_details:
        return 0
    return sum(1 for detail in exam_details if detail.get('passed', False))

@register.filter
def avg_score(exam_details):
    """
    Calculate the average score from a list of exam details.
    Usage: {{ exam_details|avg_score }}
    """
    if not exam_details:
        return 0
    total_percentage = sum(detail.get('percentage', 0) for detail in exam_details)
    if len(exam_details) > 0:
        return round(total_percentage / len(exam_details), 1)
    return 0

@register.filter
def highest_score(exam_details):
    """
    Find the highest score from a list of exam details.
    Usage: {{ exam_details|highest_score }}
    """
    if not exam_details:
        return 0
    scores = [detail.get('percentage', 0) for detail in exam_details]
    return max(scores) if scores else 0