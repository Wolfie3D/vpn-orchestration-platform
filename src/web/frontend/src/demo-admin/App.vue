<template>
  <D2App />
  <aside v-if="showExplorationCta" class="demo-exploration-cta" aria-live="polite">
    <p>{{ copy.explorationCta }}</p>
    <div>
      <a :href="trialUrl">{{ copy.trial }}</a>
      <button type="button" :aria-label="copy.dismiss" @click="dismissExplorationCta">×</button>
    </div>
  </aside>
  <nav class="demo-switcher" :aria-label="copy.navigation">
    <a :href="demoHomeUrl" class="demo-switcher-home" :title="copy.allApps" :aria-label="copy.allApps">←</a>
    <span class="demo-switcher-context"><strong>{{ copy.admin }}</strong><small>{{ copy.safePreview }}</small></span>
    <a :href="portalDemoUrl">{{ copy.openPortal }} →</a>
    <a :href="pricingUrl" class="demo-switcher-pricing">{{ copy.pricing }}</a>
    <a :href="trialUrl" class="demo-switcher-trial">{{ copy.trial }}</a>
  </nav>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import D2App from '../design2/D2App.vue'
import i18n from '../i18n'

const locale = i18n.global.locale
const route = useRoute()
const exploredRoutes = ref([])
const explorationDismissed = ref(false)
const labels = {
  en: { navigation: 'Demo navigation', allApps: 'All demos', admin: 'Admin Panel', safePreview: 'Interactive preview with synthetic data', openPortal: 'Open Client Portal', pricing: 'View pricing', trial: 'Start 7-Day Enterprise Trial', explorationCta: 'Ready to test Flirexa on your own infrastructure? Start your free 7-day Enterprise trial.', dismiss: 'Dismiss trial reminder' },
  ru: { navigation: 'Навигация демо', allApps: 'Все демо', admin: 'Админ-панель', safePreview: 'Интерактивный просмотр с тестовыми данными', openPortal: 'Открыть клиентский портал', pricing: 'Посмотреть цены', trial: 'Начать 7-дневный Enterprise trial', explorationCta: 'Готовы проверить Flirexa на своей инфраструктуре? Начните бесплатный 7-дневный Enterprise trial.', dismiss: 'Закрыть напоминание о trial' },
  de: { navigation: 'Demo-Navigation', allApps: 'Alle Demos', admin: 'Admin-Panel', safePreview: 'Interaktive Vorschau mit Testdaten', openPortal: 'Kundenportal öffnen', pricing: 'Preise ansehen', trial: '7-Tage-Enterprise-Test starten', explorationCta: 'Bereit, Flirexa auf Ihrer eigenen Infrastruktur zu testen? Starten Sie Ihren kostenlosen 7-Tage-Enterprise-Test.', dismiss: 'Testerinnerung schließen' },
  fr: { navigation: 'Navigation de la démo', allApps: 'Toutes les démos', admin: "Panneau d'administration", safePreview: 'Aperçu interactif avec des données fictives', openPortal: 'Ouvrir le portail client', pricing: 'Voir les tarifs', trial: 'Démarrer l’essai Enterprise de 7 jours', explorationCta: 'Prêt à tester Flirexa sur votre propre infrastructure ? Démarrez votre essai Enterprise gratuit de 7 jours.', dismiss: 'Fermer le rappel d’essai' },
  es: { navigation: 'Navegación de la demo', allApps: 'Todas las demos', admin: 'Panel de administración', safePreview: 'Vista interactiva con datos de prueba', openPortal: 'Abrir portal de clientes', pricing: 'Ver precios', trial: 'Iniciar prueba Enterprise de 7 días', explorationCta: '¿Listo para probar Flirexa en su propia infraestructura? Inicie su prueba Enterprise gratuita de 7 días.', dismiss: 'Cerrar recordatorio de prueba' },
}
const copy = computed(() => labels[locale.value] || labels.en)
const demoHomeUrl = computed(() => `/demo/?lang=${encodeURIComponent(locale.value || 'en')}`)
const portalDemoUrl = computed(() => `/demo-authentic/portal/?lang=${encodeURIComponent(locale.value || 'en')}#/login`)
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
</script>

<style>
.demo-switcher {
  position: fixed;
  left: 50%;
  bottom: 18px;
  transform: translateX(-50%);
  z-index: 9990;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px;
  border: 1px solid var(--border-strong);
  border-radius: 12px;
  background: color-mix(in srgb, var(--panel) 96%, transparent);
  box-shadow: 0 12px 34px rgba(15, 23, 42, .18);
  color: var(--text-2);
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  backdrop-filter: blur(14px);
}
.demo-switcher-context { display:grid; gap:1px; padding:0 9px; min-width:0; color:var(--text-3); }
.demo-switcher-context strong { color:var(--text-2); font-size:12px; line-height:1.15; }
.demo-switcher-context small { color:var(--text-3); font-size:9px; font-weight:500; line-height:1.15; }
.demo-switcher a {
  min-height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 12px;
  border-radius: 8px;
  color: #fff;
  background: var(--accent);
  text-decoration: none;
}
.demo-switcher a:hover { background: var(--accent-2); color: #fff; }
.demo-switcher .demo-switcher-home { width: 32px; padding: 0; color: var(--text-2); background: var(--panel-2); }
.demo-switcher .demo-switcher-home:hover { color: var(--text); background: var(--panel-3); }
.demo-switcher .demo-switcher-pricing { color: var(--accent); background: var(--panel); border: 1px solid color-mix(in srgb, var(--accent) 36%, var(--border-strong)); }
.demo-switcher .demo-switcher-pricing:hover { color: var(--accent); background: var(--accent-soft); }
.demo-switcher .demo-switcher-trial { background: var(--accent); }
.demo-exploration-cta {
  position: fixed;
  right: 18px;
  bottom: 76px;
  z-index: 9989;
  width: min(348px, calc(100vw - 36px));
  padding: 14px;
  border: 1px solid color-mix(in srgb, var(--accent) 35%, var(--border));
  border-radius: 13px;
  background: color-mix(in srgb, var(--panel) 97%, transparent);
  box-shadow: 0 16px 38px rgba(15, 23, 42, .2);
  backdrop-filter: blur(14px);
}
.demo-exploration-cta p { margin: 0; color: var(--text); font-size: 12px; font-weight: 600; line-height: 1.45; }
.demo-exploration-cta div { display: flex; align-items: center; justify-content: space-between; gap: 9px; margin-top: 11px; }
.demo-exploration-cta a { display: inline-flex; min-height: 31px; align-items: center; padding: 0 11px; border-radius: 8px; background: var(--accent); color: #fff; font-size: 11px; font-weight: 700; text-decoration: none; }
.demo-exploration-cta button { width: 31px; height: 31px; border: 1px solid var(--border); border-radius: 8px; background: var(--panel-2); color: var(--text-2); font: 20px/1 sans-serif; cursor: pointer; }
@media (max-width: 600px) {
  .demo-switcher { bottom: 9px; max-width: calc(100vw - 18px); gap: 3px; padding: 4px; font-size: 10px; }
  .demo-switcher-context { display:none; }
  .demo-switcher a { min-height: 30px; padding: 0 7px; }
  .demo-exploration-cta { right: 9px; bottom: 53px; width: min(348px, calc(100vw - 18px)); }
}
</style>
