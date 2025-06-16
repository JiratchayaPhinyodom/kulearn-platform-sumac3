from django.contrib.auth.models import User
from social_django.models import UserSocialAuth

from celery import task
from celery.utils.log import get_task_logger

from cms.djangoapps.course_creators.models import CourseCreator
from cms.djangoapps.course_creators.views import add_user_with_status_granted

def is_ku_personnel(user):
    """Check if the user belongs to the type Personnel based Google People's
    organizational data stored during registration"""

    try:
        social = user.social_auth.get(provider="google-oauth2")
        data = social.extra_data
        return social.extra_data['organizations'][0]['title'] == 'Personnel'
    except UserSocialAuth.DoesNotExist:
        return False
    except KeyError:
        return False

def _delete_user(username):
    """Internal use for convenient removal of a user"""
    user = User.objects.get(username=username)
    user.social_auth.all().delete()
    user.delete()

LOG_PREFIX = "KU Learn"

LOGGER = get_task_logger(__name__)

@task(ignore_result=True)
def approve_course_creators():
    admin = User.objects.filter(is_superuser=True).first()
    pendings = CourseCreator.objects.filter(state=CourseCreator.PENDING)
    for req in pendings:
        user = req.user
        req.delete()
        if is_ku_personnel(user):
            add_user_with_status_granted(admin, user)
            LOGGER.info('[{}] Granted course creator rights to {}'.format(
                LOG_PREFIX, user.username))
        else:
            LOGGER.info('[{}] Denied course creator rights for {}'.format(
                LOG_PREFIX, user.username))