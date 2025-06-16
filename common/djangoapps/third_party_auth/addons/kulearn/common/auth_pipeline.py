from social_django.models import UserSocialAuth
import requests
import json

def save_organizations(user, social=None, *args, **kwargs):
    if social:
        resp = requests.get("https://people.googleapis.com/v1/people/me",
                   params={
                       'access_token' : social.extra_data['access_token'],
                       'personFields' : "organizations",
                   })
        data = json.loads(resp.text)
        try:
            social.extra_data['organizations'] = data['organizations']
            social.save()
        except KeyError:
            pass

    return None