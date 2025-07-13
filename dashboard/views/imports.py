from django.shortcuts import redirect, render , get_object_or_404
from dashboard.models import *
from django.contrib import  messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from dashboard.models import CustomUser
from dashboard.forms.batch import BatchForm ,BatchCustomerForm
from django.db.models import Q
from django.utils import timezone
from django.db.models import Q ,Prefetch
from dashboard.forms.customer import CustomerForm ,SubscriptionCustomerForm, PaymentPlanForm
from django.contrib.auth.decorators import login_required
from django import forms    
from django.shortcuts import redirect, render , get_object_or_404
from dashboard.models import *
from django.contrib import auth, messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from dashboard.forms.chapter import ChapterForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render , get_object_or_404
from dashboard.models import *
from dashboard.forms.content.course import AddForm
from dashboard.forms.content.subject import SubjectForm
from dashboard.forms.content.chapter import ChapterForm
from dashboard.forms.content.lesson import LessonForm
from dashboard.forms.content.question import QuestionForm
from django.contrib import auth, messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render , get_object_or_404
from dashboard.models import *
from django.contrib import  messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from dashboard.models import CustomUser
from dashboard.forms.customer import CustomerForm
from django.db.models import Q ,Prefetch
from django.shortcuts import redirect, render , get_object_or_404
from dashboard.models import *
from django.contrib import  messages
from django.core.paginator import Paginator
from dashboard.forms.exam import ExamForm ,QuestionForm
from django.db.models import Q
from django.http import JsonResponse
import json
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect, render
from dashboard.models import *
from django.shortcuts import redirect, render , get_object_or_404
from dashboard.models import *
from django.contrib import auth, messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from dashboard.forms.lesson import LessonForm
from django.contrib.auth.decorators import login_required

from django.shortcuts import redirect, render , get_object_or_404
from dashboard.models import *
from django.contrib import  messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from dashboard.models import CustomUser
from dashboard.forms.level import LevelForm ,QuestionForm
from django.db.models import Q
import json
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render , get_object_or_404
from dashboard.models import *
from django.contrib import  messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from dashboard.models import CustomUser
from dashboard.forms.question import QuestionForm
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render , get_object_or_404
from dashboard.models import *
from django.contrib import  messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from dashboard.models import CustomUser
from dashboard.forms.schedule import ScheduleForm
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render , get_object_or_404
from dashboard.models import *
from django.contrib import auth, messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from dashboard.forms.subject import SubjectForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render , get_object_or_404
from dashboard.models import *
from django.contrib import  messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from dashboard.models import CustomUser
from dashboard.forms.talenthunt import TalentHuntForm
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render , get_object_or_404
from dashboard.models import *
from django.contrib import  messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from dashboard.models import CustomUser
from dashboard.forms.talenthuntsubject import TalentHuntSubjectForm
from django.db.models import Q
from django.contrib.auth.decorators import login_required

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, Group, Permission
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from ckeditor.fields import RichTextField

from dashboard.forms.staff import StaffForm,PasswordSettingForm
from django.contrib.auth import authenticate, login as auth_login


# from dashboard.forms.success_stories import SuccessStoriesForm
from django.db.models import Count

from django.template.loader import render_to_string


from django.http import HttpResponse
from datetime import datetime, timedelta


from dashboard.forms.content.folder import FolderForm


import csv
import json
from docx import Document
from django.urls import reverse
from rest_framework.response import Response
from django.contrib.auth import authenticate
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
import requests
from random import randint
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from rest_framework_simplejwt.tokens import RefreshToken