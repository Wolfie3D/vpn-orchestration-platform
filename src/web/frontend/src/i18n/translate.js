import { ref } from 'vue'
import i18n, { i18nMessages } from './index'

const translationLocale = ref(String(window.__FLIREXA_DEMO_LOCALE__ || i18n.global.locale.value || 'en'))

export function setTranslationLocale(locale) {
  translationLocale.value = String(locale || 'en')
  if (window.__FLIREXA_DEMO_LOCALE__) window.__FLIREXA_DEMO_LOCALE__ = translationLocale.value
}

// Design 2 keeps its small `tr()` wrappers for fallback-friendly copy. Reading
// the global locale here makes those wrappers reactive even when a standalone
// demo sets the language before the routed component is mounted.
export function translateGlobal(key, params = {}) {
  const requestedLocale = translationLocale.value
  if (window.__FLIREXA_DEMO_LOCALE__) {
    const value = String(key).split('.').reduce((node, part) => node?.[part], i18nMessages[requestedLocale])
    if (typeof value !== 'string') return ''
    return value.replace(/\{(\w+)\}/g, (match, name) => params?.[name] ?? match)
  }
  const value = i18n.global.t(key, params)
  return value === key ? '' : value
}
