"""
Unit tests for home page view.
"""
import ddt
import pytz
from collections import OrderedDict
from datetime import datetime, timedelta
from django.conf import settings
from django.test import override_settings
from django.urls import reverse
from edx_toggles.toggles.testutils import (
    override_waffle_switch,
)
from rest_framework import status

from cms.djangoapps.contentstore.tests.utils import CourseTestCase
from cms.djangoapps.contentstore.tests.test_libraries import LibraryTestCase
from cms.djangoapps.contentstore.views.course import ENABLE_GLOBAL_STAFF_OPTIMIZATION
from openedx.core.djangoapps.content.course_overviews.tests.factories import CourseOverviewFactory
from xmodule.modulestore.tests.factories import CourseFactory


FEATURES_WITH_HOME_PAGE_COURSE_V2_API = settings.FEATURES.copy()
FEATURES_WITH_HOME_PAGE_COURSE_V2_API['ENABLE_HOME_PAGE_COURSE_API_V2'] = True
FEATURES_WITHOUT_HOME_PAGE_COURSE_V2_API = settings.FEATURES.copy()
FEATURES_WITHOUT_HOME_PAGE_COURSE_V2_API['ENABLE_HOME_PAGE_COURSE_API_V2'] = False


@ddt.ddt
class HomePageViewTest(CourseTestCase):
    """
    Tests for HomePageCoursesView.
    """

    def setUp(self):
        super().setUp()
        self.url = reverse("cms.djangoapps.contentstore:v1:home")
        self.expected_response = {
            "allow_course_reruns": True,
            "allow_to_create_new_org": True,
            "allow_unicode_course_id": False,
            "allowed_organizations": [],
            "allowed_organizations_for_libraries": [],
            "archived_courses": [],
            "can_access_advanced_settings": True,
            "can_create_organizations": True,
            "course_creator_status": "granted",
            "courses": [],
            "in_process_course_actions": [],
            "libraries": [],
            "libraries_enabled": True,
            "libraries_v1_enabled": True,
            "libraries_v2_enabled": False,
            "taxonomies_enabled": True,
            "taxonomy_list_mfe_url": 'http://course-authoring-mfe/taxonomies',
            "optimization_enabled": False,
            "request_course_creator_url": "/request_course_creator",
            "rerun_creator_status": True,
            "show_new_library_button": True,
            "show_new_library_v2_button": True,
            "split_studio_home": False,
            "studio_name": settings.STUDIO_NAME,
            "studio_short_name": settings.STUDIO_SHORT_NAME,
            "studio_request_email": "",
            "tech_support_email": "technical@example.com",
            "platform_name": settings.PLATFORM_NAME,
            "user_is_active": True,
        }

    def test_home_page_studio_response(self):
        """Check successful response content"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(self.expected_response, response.data)

    @override_settings(MEILISEARCH_ENABLED=True)
    def test_home_page_studio_with_meilisearch_enabled(self):
        """Check response content when Meilisearch is enabled"""
        response = self.client.get(self.url)

        expected_response = self.expected_response
        expected_response["libraries_v2_enabled"] = True

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(expected_response, response.data)

    @override_settings(ORGANIZATIONS_AUTOCREATE=False)
    def test_home_page_studio_with_org_autocreate_disabled(self):
        """Check response content when Organization autocreate is disabled"""
        response = self.client.get(self.url)

        expected_response = self.expected_response
        expected_response["allow_to_create_new_org"] = False

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(expected_response, response.data)

    def test_taxonomy_list_link(self):
        response = self.client.get(self.url)
        self.assertTrue(response.data['taxonomies_enabled'])
        self.assertEqual(
            response.data['taxonomy_list_mfe_url'],
            f'{settings.COURSE_AUTHORING_MICROFRONTEND_URL}/taxonomies'
        )


@override_settings(FEATURES=FEATURES_WITHOUT_HOME_PAGE_COURSE_V2_API)
@ddt.ddt
class HomePageCoursesViewTest(CourseTestCase):
    """
    Tests for HomePageView.
    """

    def setUp(self):
        super().setUp()
        self.url = reverse("cms.djangoapps.contentstore:v1:courses")
        self.course_overview = CourseOverviewFactory.create(
            id=self.course.id,
            org=self.course.org,
            display_name=self.course.display_name,
            display_number_with_default=self.course.number,
        )
        self.non_staff_client, _ = self.create_non_staff_authed_user_client()

    def test_home_page_response(self):
        """Check successful response content"""
        response = self.client.get(self.url)
        course_id = str(self.course.id)

        expected_response = {
            "archived_courses": [],
            "courses": [{
                "course_key": course_id,
                "display_name": self.course.display_name,
                "lms_link": f'//{settings.LMS_BASE}/courses/{course_id}/jump_to/{self.course.location}',
                "number": self.course.number,
                "org": self.course.org,
                "rerun_link": f'/course_rerun/{course_id}',
                "run": self.course.id.run,
                "url": f'/course/{course_id}',
            }],
            "in_process_course_actions": [],
        }

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        print(response.data)
        self.assertDictEqual(expected_response, response.data)

    @override_settings(FEATURES=FEATURES_WITH_HOME_PAGE_COURSE_V2_API)
    def test_home_page_response_with_api_v2(self):
        """Check successful response content with api v2 modifications.

        When the feature flag is enabled, the courses are exclusively fetched from the CourseOverview model, so
        the values in the courses' list are OrderedDicts instead of the default dictionaries.
        """
        course_id = str(self.course.id)
        expected_response = {
            "archived_courses": [],
            "courses": [
                OrderedDict([
                    ("course_key", course_id),
                    ("display_name", self.course.display_name),
                    ("lms_link", f'//{settings.LMS_BASE}/courses/{course_id}/jump_to/{self.course.location}'),
                    ("number", self.course.number),
                    ("org", self.course.org),
                    ("rerun_link", f'/course_rerun/{course_id}'),
                    ("run", self.course.id.run),
                    ("url", f'/course/{course_id}'),
                ]),
            ],
            "in_process_course_actions": [],
        }

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(expected_response, response.data)

    @override_settings(FEATURES=FEATURES_WITH_HOME_PAGE_COURSE_V2_API)
    @ddt.data(
        ("active_only", "true", 2, 0),
        ("archived_only", "true", 0, 1),
        ("search", "sample", 1, 0),
        ("search", "demo", 0, 1),
        ("order", "org", 2, 1),
        ("order", "display_name", 2, 1),
        ("order", "number", 2, 1),
        ("order", "run", 2, 1)
    )
    @ddt.unpack
    def test_filter_and_ordering_courses(
        self,
        filter_key,
        filter_value,
        expected_active_length,
        expected_archived_length
    ):
        """Test home page with org filter and ordering for a staff user.

        The test creates an active/archived course, and then filters/orders them using the query parameters.
        """
        archived_course_key = self.store.make_course_key("demo-org", "demo-number", "demo-run")
        CourseOverviewFactory.create(
            display_name="Course (Demo)",
            id=archived_course_key,
            org=archived_course_key.org,
            end=(datetime.now() - timedelta(days=365)).replace(tzinfo=pytz.UTC),
        )
        active_course_key = self.store.make_course_key("sample-org", "sample-number", "sample-run")
        CourseOverviewFactory.create(
            display_name="Course (Sample)",
            id=active_course_key,
            org=active_course_key.org,
        )

        response = self.client.get(self.url, {filter_key: filter_value})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["archived_courses"]), expected_archived_length)
        self.assertEqual(len(response.data["courses"]), expected_active_length)

    @override_settings(FEATURES=FEATURES_WITH_HOME_PAGE_COURSE_V2_API)
    @ddt.data(
        ("active_only", "true"),
        ("archived_only", "true"),
        ("search", "sample"),
        ("order", "org"),
    )
    @ddt.unpack
    def test_filter_and_ordering_no_courses_staff(self, filter_key, filter_value):
        """Test home page with org filter and ordering when there are no courses for a staff user."""
        self.course_overview.delete()

        response = self.client.get(self.url, {filter_key: filter_value})

        self.assertEqual(len(response.data["courses"]), 0)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @override_settings(FEATURES=FEATURES_WITH_HOME_PAGE_COURSE_V2_API)
    @ddt.data(
        ("active_only", "true"),
        ("archived_only", "true"),
        ("search", "sample"),
        ("order", "org"),
    )
    @ddt.unpack
    def test_home_page_response_no_courses_non_staff(self, filter_key, filter_value):
        """Test home page with org filter and ordering when there are no courses for a non-staff user."""
        self.course_overview.delete()

        response = self.non_staff_client.get(self.url)

        self.assertEqual(len(response.data["courses"]), 0)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @override_waffle_switch(ENABLE_GLOBAL_STAFF_OPTIMIZATION, True)
    def test_org_query_if_passed(self):
        """Test home page when org filter passed as a query param"""
        foo_course = self.store.make_course_key('foo-org', 'bar-number', 'baz-run')
        test_course = CourseFactory.create(
            org=foo_course.org,
            number=foo_course.course,
            run=foo_course.run
        )
        CourseOverviewFactory.create(id=test_course.id, org='foo-org')
        response = self.client.get(self.url, {"org": "foo-org"})
        self.assertEqual(len(response.data['courses']), 1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @override_waffle_switch(ENABLE_GLOBAL_STAFF_OPTIMIZATION, True)
    def test_org_query_if_empty(self):
        """Test home page with an empty org query param"""
        response = self.client.get(self.url)
        self.assertEqual(len(response.data['courses']), 0)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


@ddt.ddt
class HomePageLibrariesViewTest(LibraryTestCase):
    """
    Tests for HomePageLibrariesView.
    """

    def setUp(self):
        super().setUp()
        self.url = reverse("cms.djangoapps.contentstore:v1:libraries")

    def test_home_page_libraries_response(self):
        """Check successful response content"""
        response = self.client.get(self.url)

        expected_response = {
            "libraries": [{
                'display_name': 'Test Library',
                'library_key': 'library-v1:org+lib',
                'url': '/library/library-v1:org+lib',
                'org': 'org',
                'number': 'lib',
                'can_edit': True
            }],
        }

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        print(response.data)
        self.assertDictEqual(expected_response, response.data)
