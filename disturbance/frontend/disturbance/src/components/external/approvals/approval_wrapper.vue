<template>
<div class="container">
    <PrivacyNotice />
    <div v-if="approvalId">
        <div v-if="apiaryApproval">
            <ApiaryApproval 
                :approvalId="approvalId"
                :is_internal="false"
                :is_external="true"
            />
        </div>
        <div v-else>
            <Approval 
                :approvalId="approvalId"
                :is_internal="false"
                :is_external="true"
            />
        </div>
    </div>

</div>
</template>
<script>

import ApiaryApproval from './apiary_approval.vue';
import Approval from './approval.vue';
import PrivacyNotice from '@/components/common/privacy_notice.vue';
import Vue from 'vue';
import {
  api_endpoints,
  helpers
}
from '@/utils/hooks'
export default {
    name: 'ApprovalWrapper',
    data() {
        let vm = this;
        return {
            approvalId: null,
            apiaryApproval: false,
        }
    },
    components:{
        Approval,
        ApiaryApproval,
        PrivacyNotice,
    },
    watch: {},
    computed: {
    },
    methods: {
    },
    mounted: function () {
    },
    beforeRouteEnter: function(to, from, next) {
          Vue.http.get(`/api/approvals/${to.params.approval_id}/approval_wrapper.json`).then(res => {
              next(vm => {
                  console.log(res.body)
                  vm.approvalId = res.body.id;
                  vm.apiaryApproval = res.body.apiary_approval;
              });
            },
            err => {
              console.log(err);
            });
    },
}
</script>
