import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

export const useLicenseStore = defineStore('license', () => {
  const features  = ref([])
  const tier      = ref('free')
  const loaded    = ref(false)
  const status    = ref({})

  async function load({ silent = false } = {}) {
    try {
      const { data } = await api.get('/system/license', { silent })
      status.value   = data || {}
      features.value = data.features || []
      tier.value     = data.type || data.plan || data.tier || 'free'
      loaded.value   = true
    } catch (e) {
      // Endpoint may 401 before login — leave defaults; next call will retry.
      // Once a state was loaded, preserve it across transient network errors;
      // the next silent poll or focus refresh will reconcile it.
      if (!loaded.value) {
        status.value   = {}
        features.value = []
        tier.value     = 'free'
      }
    }
  }

  function has(feature) {
    return features.value.includes(feature)
  }

  const isPaid = computed(() => tier.value !== 'free' && tier.value !== 'trial')
  const plan = computed(() => status.value.plan || tier.value)
  const isTrial = computed(() => Boolean(status.value.is_trial))
  const blocked = computed(() => Boolean(status.value.is_blocked))
  const blockedReason = computed(() => status.value.blocked_reason || '')
  const expiresAt = computed(() => status.value.expires_at || null)
  const trialDurationDays = computed(() => Number(status.value.trial_duration_days || 0))
  const daysRemaining = computed(() => {
    if (!expiresAt.value) return null
    const remainingMs = new Date(expiresAt.value).getTime() - Date.now()
    if (!Number.isFinite(remainingMs)) return null
    return Math.max(0, Math.ceil(remainingMs / 86400000))
  })

  return {
    features, tier, loaded, status, load, has, isPaid, plan, isTrial,
    blocked, blockedReason, expiresAt, trialDurationDays, daysRemaining,
  }
})
