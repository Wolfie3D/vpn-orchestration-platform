<template>
  <div class="demo-portal-app">
    <nav class="demo-preview-bar" :aria-label="copy.demoNavigation">
      <a :href="demoHomeUrl" class="demo-preview-link demo-preview-back">
        <span aria-hidden="true">←</span>
        <span>{{ copy.allApps }}</span>
      </a>
      <span class="demo-preview-context">
        <span class="demo-preview-dot" aria-hidden="true"></span>
        <span>
          <strong>{{ copy.portal }}</strong>
          <small>{{ copy.safePreview }}</small>
        </span>
      </span>
      <a :href="adminDemoUrl" class="demo-preview-link demo-preview-admin">
        <span>{{ copy.openAdmin }}</span>
        <span aria-hidden="true">→</span>
      </a>
      <a :href="pricingUrl" class="demo-preview-link demo-preview-pricing">{{ copy.pricing }}</a>
      <a :href="trialUrl" class="demo-preview-link demo-preview-trial">{{ copy.trial }}</a>
    </nav>

    <router-view v-if="route.meta?.layout === 'auth'" />
    <PortalLayout v-else>
      <router-view />
    </PortalLayout>
    <aside v-if="showExplorationCta" class="demo-portal-exploration-cta" aria-live="polite">
      <p>{{ copy.explorationCta }}</p>
      <div>
        <a :href="trialUrl">{{ copy.trial }}</a>
        <button type="button" :aria-label="copy.dismiss" @click="dismissExplorationCta">×</button>
      </div>
    </aside>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import PortalLayout from '../components/Layout.vue'

const { locale } = useI18n()
const route = useRoute()
const exploredRoutes = ref([])
const explorationDismissed = ref(false)
const labels = {
  en: { demoNavigation: 'Demo navigation', allApps: 'All demos', portal: 'Client Portal', safePreview: 'Interactive preview with synthetic data', openAdmin: 'Admin Panel', pricing: 'View pricing', trial: 'Start 7-Day Enterprise Trial', explorationCta: 'Ready to test Flirexa on your own infrastructure? Start your free 7-day Enterprise trial.', dismiss: 'Dismiss trial reminder' },
  ru: { demoNavigation: 'Навигация демо', allApps: 'Все демо', portal: 'Клиентский портал', safePreview: 'Интерактивный просмотр с тестовыми данными', openAdmin: 'Админ-панель', pricing: 'Цены', trial: 'Начать 7-дневный Enterprise trial', explorationCta: 'Готовы проверить Flirexa на своей инфраструктуре? Начните бесплатный 7-дневный Enterprise trial.', dismiss: 'Закрыть напоминание о trial' },
  de: { demoNavigation: 'Demo-Navigation', allApps: 'Alle Demos', portal: 'Kundenportal', safePreview: 'Interaktive Vorschau mit Testdaten', openAdmin: 'Admin-Panel', pricing: 'Preise', trial: '7-Tage-Enterprise-Test starten', explorationCta: 'Bereit, Flirexa auf Ihrer eigenen Infrastruktur zu testen? Starten Sie Ihren kostenlosen 7-Tage-Enterprise-Test.', dismiss: 'Testerinnerung schließen' },
  fr: { demoNavigation: 'Navigation de la démo', allApps: 'Toutes les démos', portal: 'Portail client', safePreview: 'Aperçu interactif avec des données fictives', openAdmin: "Panneau d'administration", pricing: 'Tarifs', trial: 'Démarrer l’essai Enterprise de 7 jours', explorationCta: 'Prêt à tester Flirexa sur votre propre infrastructure ? Démarrez votre essai Enterprise gratuit de 7 jours.', dismiss: 'Fermer le rappel d’essai' },
  es: { demoNavigation: 'Navegación de la demo', allApps: 'Todas las demos', portal: 'Portal del cliente', safePreview: 'Vista interactiva con datos de prueba', openAdmin: 'Panel de administración', pricing: 'Precios', trial: 'Iniciar prueba Enterprise de 7 días', explorationCta: '¿Listo para probar Flirexa en su propia infraestructura? Inicie su prueba Enterprise gratuita de 7 días.', dismiss: 'Cerrar recordatorio de prueba' },
}
const copy = computed(() => labels[locale.value] || labels.en)
const demoHomeUrl = computed(() => `/demo/?lang=${encodeURIComponent(locale.value || 'en')}`)
const adminDemoUrl = computed(() => `/demo-authentic/admin/?lang=${encodeURIComponent(locale.value || 'en')}`)
const pricingUrl = computed(() => `/?lang=${encodeURIComponent(locale.value || 'en')}#pricing`)
const trialUrl = computed(() => `/?trial=1&lang=${encodeURIComponent(locale.value || 'en')}`)
const showExplorationCta = computed(() => !explorationDismissed.value && exploredRoutes.value.length >= 3)
watch(() => route.fullPath, path => {
  if (!exploredRoutes.value.includes(path)) {
    exploredRoutes.value = [...exploredRoutes.value, path].slice(-8)
  }
}, { immediate: true })
function dismissExplorationCta() {
  explorationDismissed.value = true
}
onMounted(() => {
  const demoLocale = window.__FLIREXA_DEMO_LOCALE__
  if (labels[demoLocale]) locale.value = demoLocale
})
</script>

<style>
.demo-portal-app { min-height: 100vh; }
.demo-preview-bar {
  position: relative;
  z-index: 70;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  min-height: 48px;
  padding: 7px max(20px, calc((100vw - 1320px) / 2 + 24px));
  border-bottom: 1px solid var(--border);
  background: var(--bg-elev);
  color: var(--text-2);
  font-size: 12px;
  font-weight: 500;
}
.demo-preview-link {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 32px;
  padding: 0 11px;
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  background: var(--bg-elev);
  color: var(--text-2);
  text-decoration: none;
  white-space: nowrap;
  transition: border-color .15s ease, background .15s ease, color .15s ease;
}
.demo-preview-link:hover {
  border-color: var(--border-strong);
  background: var(--bg-hover);
  color: var(--text);
}
.demo-preview-admin {
  border-color: color-mix(in oklab, var(--accent) 34%, var(--border));
  color: var(--accent);
}
.demo-preview-pricing { color: var(--accent); border-color: color-mix(in oklab, var(--accent) 34%, var(--border)); }
.demo-preview-trial { color: #fff; background: var(--accent); border-color: var(--accent); }
.demo-preview-context {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  min-width: 0;
  text-align: left;
}
.demo-preview-context > span:last-child { display: grid; gap: 1px; }
.demo-preview-context strong { color: var(--text); font-size: 12px; font-weight: 600; }
.demo-preview-context small { color: var(--text-3); font-size: 10px; }
.demo-preview-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--success);
  box-shadow: 0 0 0 3px var(--success-soft);
  flex: 0 0 auto;
}
.demo-portal-app .fx-login-theme-toggle { top: 60px; }
.demo-portal-exploration-cta { position: fixed; right: 18px; bottom: 18px; z-index: 82; width: min(348px,calc(100vw - 36px)); padding: 14px; border: 1px solid color-mix(in oklab,var(--accent) 35%,var(--border)); border-radius: 13px; background: color-mix(in oklab,var(--bg-elev) 97%,transparent); box-shadow: 0 16px 38px rgba(15,23,42,.2); backdrop-filter: blur(14px) }
.demo-portal-exploration-cta p { margin: 0; color: var(--text); font-size: 12px; font-weight: 600; line-height: 1.45 }
.demo-portal-exploration-cta div { display:flex;align-items:center;justify-content:space-between;gap:9px;margin-top:11px }
.demo-portal-exploration-cta a { display:inline-flex;min-height:31px;align-items:center;padding:0 11px;border-radius:8px;background:var(--accent);color:#fff;font-size:11px;font-weight:700;text-decoration:none }
.demo-portal-exploration-cta button { width:31px;height:31px;border:1px solid var(--border);border-radius:8px;background:var(--bg-hover);color:var(--text-2);font:20px/1 sans-serif;cursor:pointer }
@media (max-width: 600px) {
  .demo-preview-bar { min-height: 44px; padding: 6px 12px; gap: 6px; flex-wrap: wrap; justify-content: flex-start; }
  .demo-preview-context { display: none; }
  .demo-preview-link { min-height: 31px; padding: 0 9px; font-size: 11px; }
  .demo-preview-admin { margin-left: auto; }
  .demo-portal-app .fx-login-theme-toggle { top: 56px; }
  .demo-portal-exploration-cta { right: 9px;bottom: 9px;width:min(348px,calc(100vw - 18px)) }
}
</style>
