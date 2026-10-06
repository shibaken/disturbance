from ledger.accounts.models import EmailUser
from rest_framework.test import APITestCase

# Endpoints that must require authentication (customer or internal users allowed).
AUTHENTICATED_URLS = [
    '/template_group',
    '/gisdata/?layer=wa_coast_smoothed&lat=-31.95&lng=115.86',
    '/api/countries',
    '/api/profile',
    '/api/proposal_type',
    '/api/empty_list',
]

# Endpoints that must be restricted to internal users.
INTERNAL_URLS = [
    '/api/amendment_request_reason_choices',
    '/api/compliance_amendment_reason_choices',
    '/api/search_keywords',
    '/api/organisation_access_group_members',
    '/api/history/versions/disturbance/proposals/Proposal/1/lodgement_number/',
    '/api/history/version/disturbance/proposals/Proposal/InternalProposalSerializer/1/1/',
    '/api/history/compare/disturbance/Proposal/1/2/1/',
    '/api/history/compare/serialized/disturbance/proposals/Proposal/InternalProposalSerializer/1/2/1/',
    '/api/history/compare/field/disturbance/Proposal/1/2/1/data/',
    '/api/history/compare/root/fields/disturbance/Proposal/1/2/1/',
]

# POST-only internal endpoints.
INTERNAL_POST_URLS = [
    '/api/search_reference',
    '/api/search_sections',
    '/api/get_search_geojson',
]

DENIED = (401, 403)


class StandaloneApiViewAuthorisationTests(APITestCase):
    def setUp(self):
        self.customer = EmailUser.objects.create(
            email='api.auth.customer@example.com',
            first_name='Api',
            last_name='Customer',
            is_staff=False,
            is_superuser=False,
        )

    def test_anonymous_is_denied(self):
        for url in AUTHENTICATED_URLS + INTERNAL_URLS:
            with self.subTest(url=url):
                self.assertIn(self.client.get(url).status_code, DENIED)
        for url in INTERNAL_POST_URLS:
            with self.subTest(url=url):
                self.assertIn(self.client.post(url, {}, format='json').status_code, DENIED)

    def test_customer_can_reach_authenticated_endpoints(self):
        self.client.force_authenticate(user=self.customer)
        for url in AUTHENTICATED_URLS:
            with self.subTest(url=url):
                # Only the permission layer is asserted here; handler results such as 404 are fine.
                self.assertNotIn(self.client.get(url).status_code, DENIED)

    def test_customer_is_denied_internal_endpoints(self):
        self.client.force_authenticate(user=self.customer)
        for url in INTERNAL_URLS:
            with self.subTest(url=url):
                self.assertIn(self.client.get(url).status_code, DENIED)
        for url in INTERNAL_POST_URLS:
            with self.subTest(url=url):
                self.assertIn(self.client.post(url, {}, format='json').status_code, DENIED)
