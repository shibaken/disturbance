<template>
<div class="container">
    <PrivacyNotice />
    <div v-if="proposalId">
        <div v-if="temporaryProposal">
            <ProposalTemporaryUse 
                :proposalId="proposalId"
                :is_internal="false"
                :is_external="true"
            />
        </div>
        <div v-else>
            <Proposal :proposalId="proposalId"/>
        </div>
    </div>
</div>
</template>

<script>
import Vue from 'vue';
import { api_endpoints, helpers } from '@/utils/hooks'
import ProposalTemporaryUse from '@/components/external/proposal_temporary_use.vue'
import Proposal from '@/components/external/proposal_external.vue'
import PrivacyNotice from '@/components/common/privacy_notice.vue'

export default {
    name: 'ExternalProposalWrapper',
    data() {
        let vm = this;
        return {
            proposalId: null,
            applicationTypeName: '',
        }
    },
    components:{
        ProposalTemporaryUse,
        Proposal,
        PrivacyNotice,
    },
    computed: {
        temporaryProposal: function() {
            let retVal = false;
            if (this.applicationTypeName === 'Temporary Use') {
                retVal = true;
            }
            return retVal;
        },

    },
    beforeRouteEnter: function(to, from, next) {
        let vm = this
        Vue.http.get(`/api/proposal/${to.params.proposal_id}/internal_proposal_wrapper.json`).then(res => {
            next(vm => {
                vm.proposalId = res.body.id;
                vm.applicationTypeName = res.body.application_type_name;
            });
          },
          err => {
            console.log(err);
          });
    },
}
</script>
