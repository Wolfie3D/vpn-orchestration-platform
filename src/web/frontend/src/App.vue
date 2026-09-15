<template>
  <div v-if="isLoginPage">
    <router-view />
  </div>
  <template v-else>
    <D2App />
    <UpgradeBanner />
    <UpgradeModal />
    <D2TrialExpiryModal />
  </template>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import UpgradeBanner from './components/UpgradeBanner.vue'
import UpgradeModal from './components/UpgradeModal.vue'
import D2App from './design2/D2App.vue'
import D2TrialExpiryModal from './design2/shell/D2TrialExpiryModal.vue'
import { useSystemStore } from './stores/system'
import { useBrandingStore } from './stores/branding'
import { useLicenseStore } from './stores/license'

const route = useRoute()
const system = useSystemStore()
const branding = useBrandingStore()
const license = useLicenseStore()

const isLoginPage = computed(() => route.name === 'Login')
let licenseTimer = null

function hasSession() {
  try { return Boolean(localStorage.getItem('sb_token')) } catch (_) { return false }
}

function refreshLicense() {
  if (!isLoginPage.value && hasSession()) license.load({ silent: true })
}

function onLicenseInvalidated() {
  refreshLicense()
}

function onLicenseVisibility() {
  if (!document.hidden) refreshLicense()
}

onMounted(() => {
  system.initTheme()
  branding.fetchBranding()
  // Load license features once at app startup so feature-gated UI bits
  // (Mikrotik connection mode in Add Server, etc.) can read them
  // without each view having to remember to call `license.load()`.
  // Skip on the login page — /api/v1/system/license requires auth and
  // would just 401 anyway; will get loaded after login by the watcher below.
  if (!isLoginPage.value && !license.loaded) license.load()
  window.addEventListener('flirexa:license-invalidated', onLicenseInvalidated)
  window.addEventListener('focus', refreshLicense)
  document.addEventListener('visibilitychange', onLicenseVisibility)
  licenseTimer = window.setInterval(refreshLicense, 60 * 1000)
})

// When the user navigates away from the login page (i.e. just logged
// in), pull the license features. Without this, post-login renders use
// the empty default and feature-gated UI stays hidden until the next
// full-page reload.
watch(isLoginPage, (onLogin) => {
  if (!onLogin) refreshLicense()
})

onBeforeUnmount(() => {
  window.removeEventListener('flirexa:license-invalidated', onLicenseInvalidated)
  window.removeEventListener('focus', refreshLicense)
  document.removeEventListener('visibilitychange', onLicenseVisibility)
  if (licenseTimer) window.clearInterval(licenseTimer)
})
</script>
