<template>
  <div v-if="apiaryTemplateGroup" class="privacy-notice-container">
    <div class="panel panel-info">
      <div class="panel-heading" @click="toggleCollapse" style="cursor: pointer;">
        <h4 class="panel-title">
          Personal Information Collection Notice
          <span v-if="isExpanded" class="glyphicon glyphicon-chevron-up pull-right"></span>
          <span v-else class="glyphicon glyphicon-chevron-down pull-right"></span>
        </h4>
      </div>
      <transition name="slide">
        <div v-show="isExpanded" class="panel-body">
          <p>
            The Department of Biodiversity, Conservation and Attractions (DBCA) collects this personal
            information to assess, approve and grant an Apiary Authority that allows you to
            legally carry out beekeeping activities in Western Australia's national parks, conservation
            reserves and certain Crown lands for beekeeping.
          </p>
          <p>
            You are required to provide this information under the
            <em>Conservation and Land Management Act 1984</em> and
            <em>Conservation and Land Management Regulations 2002</em>.
          </p>
          <p>
            If you choose not to provide personal information, you will not be able to legally carry
            out beekeeping activities in Western Australia's national parks, conservation reserves and
            certain Crown lands for beekeeping.
          </p>
          <p>
            For further details on how DBCA manage your personal information, you can read our
            <a :href="privacyPolicyUrl" target="_blank">Privacy Policy</a>.
            If you have any questions about how your personal information will be handled, or if you
            would like to access your personal information, please email
            <a href="mailto:privacy@dbca.wa.gov.au">privacy@dbca.wa.gov.au</a>.
          </p>
        </div>
      </transition>
    </div>
  </div>
</template>

<script>
export default {
  name: 'PrivacyNotice',
  data() {
    return {
      isExpanded: true,
      apiaryTemplateGroup: false,
      privacyPolicyUrl: '#'
    }
  },
  methods: {
    toggleCollapse() {
      this.isExpanded = !this.isExpanded;
    }
  },
  mounted() {
    // Get template group from API
    this.$http.get('/template_group', {
      emulateJSON: true
    }).then(res => {
      if (res.body.template_group === 'apiary') {
        this.apiaryTemplateGroup = true;
      }
    }, err => {
      console.error('Error fetching template group:', err);
    });

    // Get privacy policy URL from window.env
    if (window.env && window.env.privacy_policy_url) {
      this.privacyPolicyUrl = window.env.privacy_policy_url;
    }
  }
}
</script>

<style scoped>
.privacy-notice-container {
  margin-bottom: 20px;
}

.panel-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.slide-enter-active, .slide-leave-active {
  transition: max-height 0.3s ease, opacity 0.3s ease;
  max-height: 1000px;
  overflow: hidden;
}

.slide-enter, .slide-leave-to {
  max-height: 0;
  opacity: 0;
}
</style>
