<template>
  <Teleport to="body">
    <Transition name="trial-expiry">
      <div v-if="visible" class="trial-expiry-backdrop" @click.self="dismiss">
        <section
          class="trial-expiry-dialog"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="titleId"
        >
          <button
            type="button"
            class="trial-expiry-close"
            :aria-label="t('trialExpiry.close')"
            @click="dismiss"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
          </button>

          <div class="trial-expiry-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24"><path d="M12 8v5l3 2" /><circle cx="12" cy="12" r="8.5" /></svg>
          </div>

          <p class="trial-expiry-eyebrow">{{ t('trialExpiry.eyebrow') }}</p>
          <h2 :id="titleId">{{ t('trialExpiry.title') }}</h2>
          <p class="trial-expiry-copy">
            {{ t('trialExpiry.expires', { date: expiryDate }) }}
          </p>

          <div class="trial-expiry-count">
            <strong>{{ daysLeft }}</strong>
            <span>{{ dayLabel }}</span>
          </div>

          <p class="trial-expiry-note">{{ t('trialExpiry.body') }}</p>

          <div class="trial-expiry-actions">
            <a :href="buyUrl" target="_blank" rel="noopener noreferrer" @click="dismiss">
              {{ t('trialExpiry.buyLifetime') }}
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" /></svg>
            </a>
            <button type="button" @click="dismiss">{{ t('trialExpiry.remindTomorrow') }}</button>
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useLicenseStore } from '../../stores/license'

const license = useLicenseStore()
const { t, locale } = useI18n({ useScope: 'global' })
const dismissedDate = ref('')
const clock = ref(Date.now())
let clockTimer = null
const titleId = 'trial-expiry-title'
const buyUrl = 'https://flirexa.biz/?billing=lifetime#pricing'

const daysLeft = computed(() => {
  clock.value
  if (!license.expiresAt) return null
  const remainingMs = new Date(license.expiresAt).getTime() - Date.now()
  if (!Number.isFinite(remainingMs)) return null
  return Math.max(0, Math.ceil(remainingMs / 86400000))
})
const isSevenDayEnterpriseTrial = computed(() => (
  license.loaded
  && license.isTrial
  && license.trialDurationDays === 7
  && String(license.plan || '').toLowerCase() === 'enterprise'
  && !license.blocked
  && daysLeft.value !== null
  && daysLeft.value >= 1
  && daysLeft.value <= 3
))

const storageKey = computed(() => {
  const server = license.status?.server_id || 'panel'
  return `flirexa:trial-expiry:${server}:${license.expiresAt || 'unknown'}`
})

function today() {
  return new Date().toISOString().slice(0, 10)
}

function wasShownToday() {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey.value) || '{}')
    return saved.date === today() && Number(saved.days) === Number(daysLeft.value)
  } catch (_) {
    return false
  }
}

function remember() {
  try {
    localStorage.setItem(storageKey.value, JSON.stringify({
      date: today(),
      days: daysLeft.value,
    }))
  } catch (_) {}
}

function dismiss() {
  remember()
  dismissedDate.value = today()
}

const visible = computed(() => {
  clock.value
  return isSevenDayEnterpriseTrial.value
    && dismissedDate.value !== today()
    && !wasShownToday()
})
const expiryDate = computed(() => {
  if (!license.expiresAt) return ''
  try {
    return new Intl.DateTimeFormat(locale.value || 'en', {
      year: 'numeric', month: 'long', day: 'numeric',
    }).format(new Date(license.expiresAt))
  } catch (_) {
    return String(license.expiresAt).slice(0, 10)
  }
})
const dayLabel = computed(() => t(daysLeft.value === 1
  ? 'trialExpiry.dayOne'
  : 'trialExpiry.daysMany'))

watch(
  () => [license.expiresAt, license.blocked],
  () => { dismissedDate.value = '' },
)

onMounted(() => { clockTimer = window.setInterval(() => { clock.value = Date.now() }, 60 * 1000) })
onUnmounted(() => { if (clockTimer) window.clearInterval(clockTimer) })
</script>

<style scoped>
.trial-expiry-backdrop {
  position: fixed;
  inset: 0;
  z-index: 10020;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(8, 10, 16, .58);
  backdrop-filter: blur(5px);
}
.trial-expiry-dialog {
  position: relative;
  width: min(100%, 520px);
  padding: 30px;
  overflow: hidden;
  color: var(--text);
  background: var(--panel);
  border: 1px solid var(--border-strong);
  border-radius: 20px;
  box-shadow: var(--shadow-md), 0 26px 70px rgba(0, 0, 0, .28);
}
.trial-expiry-dialog::before {
  content: '';
  position: absolute;
  inset: 0 0 auto;
  height: 3px;
  background: var(--accent);
}
.trial-expiry-close {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  color: var(--text-3);
  background: var(--panel-2);
  border: 1px solid var(--border);
  border-radius: 10px;
  cursor: pointer;
}
.trial-expiry-close:hover { color: var(--text); border-color: var(--border-strong); }
.trial-expiry-close svg { width: 16px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; }
.trial-expiry-mark {
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  color: var(--accent);
  background: var(--panel-2);
  border: 1px solid var(--accent-ring);
  border-radius: 14px;
}
.trial-expiry-mark svg { width: 24px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.trial-expiry-eyebrow {
  margin: 22px 0 8px;
  color: var(--accent);
  font-size: 11px;
  font-weight: 750;
  letter-spacing: .1em;
  text-transform: uppercase;
}
.trial-expiry-dialog h2 { margin: 0; max-width: 420px; font-size: clamp(24px, 4vw, 31px); line-height: 1.12; letter-spacing: -.025em; }
.trial-expiry-copy { margin: 12px 0 0; color: var(--text-2); font-size: 14px; line-height: 1.55; }
.trial-expiry-count {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin: 24px 0 16px;
  padding: 18px 20px;
  background: var(--panel-2);
  border: 1px solid var(--border);
  border-radius: 14px;
}
.trial-expiry-count strong { color: var(--accent); font-size: 40px; line-height: 1; letter-spacing: -.04em; }
.trial-expiry-count span { color: var(--text); font-size: 16px; font-weight: 650; }
.trial-expiry-note { margin: 0; color: var(--text-2); font-size: 13px; line-height: 1.55; }
.trial-expiry-actions { display: grid; grid-template-columns: 1fr auto; gap: 10px; margin-top: 24px; }
.trial-expiry-actions a,
.trial-expiry-actions button {
  min-height: 46px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 0 18px;
  border-radius: 12px;
  font: inherit;
  font-size: 13px;
  font-weight: 700;
  text-decoration: none;
  cursor: pointer;
}
.trial-expiry-actions a { color: #fff; background: var(--accent); border: 1px solid var(--accent); box-shadow: 0 8px 24px var(--accent-ring); }
.trial-expiry-actions a:hover { filter: brightness(1.05); transform: translateY(-1px); }
.trial-expiry-actions a svg { width: 17px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
.trial-expiry-actions button { color: var(--text-2); background: transparent; border: 1px solid var(--border-strong); }
.trial-expiry-actions button:hover { color: var(--text); background: var(--panel-2); }
.trial-expiry-enter-active, .trial-expiry-leave-active { transition: opacity .18s ease; }
.trial-expiry-enter-active .trial-expiry-dialog, .trial-expiry-leave-active .trial-expiry-dialog { transition: transform .18s ease, opacity .18s ease; }
.trial-expiry-enter-from, .trial-expiry-leave-to { opacity: 0; }
.trial-expiry-enter-from .trial-expiry-dialog, .trial-expiry-leave-to .trial-expiry-dialog { opacity: 0; transform: translateY(10px) scale(.985); }
@media (max-width: 600px) {
  .trial-expiry-backdrop { align-items: end; padding: 12px; }
  .trial-expiry-dialog { padding: 25px 20px 20px; border-radius: 18px; }
  .trial-expiry-actions { grid-template-columns: 1fr; }
  .trial-expiry-actions button { order: 2; }
}
</style>
