from django.contrib.auth.mixins import LoginRequiredMixin

from disturbance.components.organisations.models import Organisation
from reversion_compare.views import HistoryCompareDetailView


class OrganisationHistoryCompareView(LoginRequiredMixin, HistoryCompareDetailView):
    """
    View for reversion_compare
    """
    model = Organisation
    template_name = 'disturbance/reversion_history.html'
