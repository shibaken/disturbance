from disturbance.components.organisations.models import Organisation
from disturbance.components.proposals.views import HistoryCompareDetailView


class OrganisationHistoryCompareView(HistoryCompareDetailView):
    """
    View for reversion_compare
    """
    model = Organisation
    template_name = 'disturbance/reversion_history.html'
