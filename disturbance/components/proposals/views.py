import json

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.views.generic import View
from django.core.cache import cache
from django.db.models import Q

import requests
from requests.auth import HTTPBasicAuth

from disturbance.components.proposals.models import Proposal, Referral, ProposalType, HelpPage
from disturbance.components.approvals.models import Approval
from disturbance.components.compliances.models import Compliance

from reversion.models import Version
from reversion_compare.views import HistoryCompareDetailView as BaseHistoryCompareDetailView

from disturbance.helpers import is_internal

import csv
from datetime import datetime


class HistoryCompareDetailView(LoginRequiredMixin, UserPassesTestMixin, BaseHistoryCompareDetailView):
    template_name = 'disturbance/reversion_history.html'

    def test_func(self):
        return is_internal(self.request)

class ProposalHistoryCompareView(HistoryCompareDetailView):
    """
    View for reversion_compare
    """
    model = Proposal
    template_name = 'disturbance/reversion_history.html'


class ProposalHistoryLatestCompareView(HistoryCompareDetailView):
    """
    View for reversion_compare that returns on the x most recent revisions
    """
    model = Proposal
    template_name = 'disturbance/reversion_history.html'


class ProposalFilteredHistoryCompareView(HistoryCompareDetailView):
    """
    View for reversion_compare - with 'status' in the comment field only'
    """

    model = Proposal
    template_name = 'disturbance/reversion_history.html'

    def _get_action_list(self,):
        """ Get only versions when processing_status changed, and add the most recent (current) version """
        current_revision_id = Version.objects.get_for_object(self.get_object()).first().revision_id
        action_list = [
            {"version": version, "revision": version.revision}
            for version in self._order_version_queryset(
                #Version.objects.get_for_object(self.get_object()).select_related("revision__user").filter(revision__comment__icontains='status')
                Version.objects.get_for_object(self.get_object()).select_related("revision__user").filter(Q(revision__comment__icontains='status') | Q(revision_id=current_revision_id))
            )
        ]
        return action_list


class ReferralHistoryCompareView(HistoryCompareDetailView):
    """
    View for reversion_compare
    """
    model = Referral
    template_name = 'disturbance/reversion_history.html'


# def success_view(request):
#     pass


class ApprovalHistoryCompareView(HistoryCompareDetailView):
    """
    View for reversion_compare
    """
    model = Approval
    template_name = 'disturbance/reversion_history.html'


class ComplianceHistoryCompareView(HistoryCompareDetailView):
    """
    View for reversion_compare
    """
    model = Compliance
    template_name = 'disturbance/reversion_history.html'



class ProposalTypeHistoryCompareView(HistoryCompareDetailView):
    """
    View for reversion_compare
    """
    model = ProposalType
    template_name = 'disturbance/reversion_history.html'


class HelpPageHistoryCompareView(HistoryCompareDetailView):
    """
    View for reversion_compare
    """
    model = HelpPage
    template_name = 'disturbance/reversion_history.html'


class PreviewLicencePDFView(View):
    def post(self, request, *args, **kwargs):
        response = HttpResponse(content_type='application/pdf')

        proposal = self.get_object()
        details = json.loads(request.POST.get('formData'))

        #response.write(proposal.preview_approval(request, details))
        response.content = proposal.preview_approval(request, details)
        return response

    def get_object(self):
        return get_object_or_404(Proposal, id=self.kwargs['proposal_pk'])

