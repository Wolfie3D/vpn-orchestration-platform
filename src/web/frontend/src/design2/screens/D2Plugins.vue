<!-- Plugins — his exact layout: count + refresh header / card grid (icon·name·
     system badge·version·author·desc·uninstall) + install modal (URL + sha256).
     Wired to /plugins (install POST, list, delete by name). -->
<template>
  <div>
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px">
      <div style="font-size:12.5px;color:var(--text-3)">{{ pluginsCountLabel }}</div>
      <button @click="refreshPlugins" class="d2-refresh">{{ tr('common.refresh') || 'Refresh' }}</button>
    </div>

    <div v-if="loading && !plugins.length" style="color:var(--text-3);padding:24px;text-align:center">{{ tr('common.loading') || 'Loading…' }}</div>
    <div v-else-if="!plugins.length" style="background:var(--panel);border:1px solid var(--border);border-radius:14px;box-shadow:var(--shadow);padding:56px;text-align:center;color:var(--text-3)">{{ tr('plugins.empty') || 'No plugins installed yet.' }}</div>

    <div v-else style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px">
      <div v-for="p in plugins" :key="p.id || p.name" style="background:var(--panel);border:1px solid var(--border);border-radius:14px;box-shadow:var(--shadow);padding:18px 20px">
        <div style="display:flex;align-items:flex-start;gap:11px;margin-bottom:10px">
          <div style="width:38px;height:38px;border-radius:10px;background:var(--accent-soft);color:var(--accent);display:flex;align-items:center;justify-content:center;flex:none"><svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M21 8l-9-5-9 5v8l9 5 9-5z"></path><path d="M3 8l9 5 9-5M12 13v8"></path></svg></div>
          <div style="flex:1;min-width:0">
            <div style="display:flex;align-items:center;gap:7px"><span style="font-weight:620;font-size:14.5px">{{ p.name }}</span><span v-if="p.system" style="font-size:10px;font-weight:600;padding:2px 7px;border-radius:6px;color:var(--text-3);background:var(--gray-soft)">{{ tr('plugins.core') || 'System' }}</span></div>
            <div class="mono" style="font-size:11.5px;color:var(--text-3)">v{{ p.version }} · {{ p.author }}</div>
          </div>
        </div>
        <div style="font-size:12.5px;color:var(--text-2);line-height:1.5;margin-bottom:14px">{{ p.desc }}</div>
        <div v-if="p.toggleable" class="d2-plugin-control">
          <div style="min-width:0">
            <div :class="['d2-plugin-status', p.statusClass]">{{ p.statusLabel }}</div>
            <div v-if="p.configLabel" class="d2-plugin-config mono">{{ p.configLabel }}</div>
          </div>
          <button
            type="button"
            class="d2-switch"
            :class="{ 'is-on': p.enabled }"
            :disabled="p.toggling || (!p.licenseAvailable && !p.enabled)"
            role="switch"
            :aria-checked="p.enabled ? 'true' : 'false'"
            :aria-label="p.enabled ? (tr('plugins.disable') || 'Disable plugin') : (tr('plugins.enable') || 'Enable plugin')"
            @click="togglePlugin(p)"
          ><span></span></button>
        </div>
        <button v-if="p.removable" @click="p.onUninstall" class="d2-uninstall">{{ tr('plugins.uninstall') || 'Uninstall' }}</button>
      </div>
    </div>

    <!-- ===== PLUGIN INSTALL MODAL ===== -->
    <D2Modal :open="pluginInstallModal" :title="tr('plugins.installTitle') || 'Install plugin'" size="sm" @close="closePluginInstall">
      <div style="display:flex;flex-direction:column;gap:14px">
        <div>
          <label style="display:block;font-size:12.5px;font-weight:550;margin-bottom:7px">{{ tr('plugins.urlLabel') || 'Plugin URL' }}</label>
          <input :value="pluginUrl" @input="onPluginUrl" placeholder="https://…/plugin.tar.gz" class="d2-modal-in mono" style="font-size:12.5px" />
        </div>
        <div>
          <label style="display:block;font-size:12.5px;font-weight:550;margin-bottom:7px">{{ tr('plugins.shaLabel') || 'SHA-256' }}</label>
          <input :value="pluginSha" @input="onPluginSha" placeholder="e3b0c44298fc1c14…" class="d2-modal-in mono" style="font-size:12px" />
        </div>
        <div v-if="installError" style="color:var(--red);font-size:12.5px">{{ installError }}</div>
      </div>
      <template #footer>
        <button @click="closePluginInstall" style="height:40px;padding:0 16px;border:1px solid var(--border-strong);background:var(--panel);color:var(--text-2);border-radius:10px;font:inherit;font-size:13.5px;font-weight:550;cursor:pointer">{{ tr('common.cancel') || 'Cancel' }}</button>
        <button @click="submitPluginInstall" :disabled="!canSubmit || installing" :style="{ height:'40px', padding:'0 18px', border:'none', background:'var(--accent)', color:'#fff', borderRadius:'10px', font:'inherit', fontSize:'13.5px', fontWeight:600, cursor:(!canSubmit||installing)?'not-allowed':'pointer', opacity:(!canSubmit||installing)?.6:1 }">{{ installing ? (tr('plugins.installing') || 'Installing…') : (tr('plugins.installAction') || 'Install') }}</button>
      </template>
    </D2Modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { d2confirm } from '../ui/confirm'
import { useI18n } from 'vue-i18n'
import { translateGlobal } from '../../i18n/translate'
import api from '../../api'
import { useD2Ui } from '../../stores/d2ui'
import D2Modal from '../ui/D2Modal.vue'

const { t } = useI18n({ useScope: 'global' })
function tr(k) { try { return translateGlobal(k) } catch (_) { return '' } }
const ui = useD2Ui()

const items = ref([])
const loading = ref(false)
const toggling = ref(new Set())

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/plugins/installed')
    items.value = data.items || data.plugins || (Array.isArray(data) ? data : [])
  } catch (e) { console.error(e) } finally { loading.value = false }
}

// --- adapter: his card shape (name / version / author / desc / system / removable) ---
const plugins = computed(() => (items.value || []).map(p => ({
  id: p.id || p.name,
  rawName: p.name,
  name: p.display_name || p.name,
  version: p.version || '—',
  author: p.author || p.vendor || '—',
  desc: p.description || '',
  system: !!(p.is_core || p.system),
  removable: !(p.is_core || p.system),
  toggleable: !!p.operator_toggleable,
  enabled: !!p.enabled,
  effectiveEnabled: !!p.effective_enabled,
  configured: p.configured,
  licenseAvailable: !!p.license_available,
  toggling: toggling.value.has(p.name),
  statusLabel: !p.license_available
    ? (tr('plugins.licenseRequired') || 'Not included in licence')
    : !p.enabled
      ? (tr('plugins.disabled') || 'Disabled')
      : p.configured === false
        ? (tr('plugins.notConfigured') || 'Configuration required')
        : p.effective_enabled
          ? (tr('plugins.active') || 'Active')
          : (tr('plugins.unavailable') || 'Unavailable'),
  statusClass: !p.license_available || p.configured === false
    ? 'is-warning'
    : p.effective_enabled ? 'is-active' : 'is-muted',
  configLabel: p.runtime_status?.package_name && p.runtime_status?.product_id
    ? `${p.runtime_status.package_name} · ${p.runtime_status.product_id}`
    : '',
  onUninstall: () => uninstall(p),
})))
const pluginsCountLabel = computed(() => {
  const n = plugins.value.length
  return n + ' ' + (tr('plugins.installed') || 'installed')
})

async function refreshPlugins() { await load() }
async function togglePlugin(p) {
  if (p.toggling) return
  const next = !p.enabled
  toggling.value = new Set([...toggling.value, p.rawName])
  try {
    await api.patch(`/plugins/${encodeURIComponent(p.rawName)}/state`, { enabled: next })
    await load()
  } catch (e) {
    alert(e?.response?.data?.detail || e?.message || 'Plugin state change failed')
  } finally {
    const nextSet = new Set(toggling.value)
    nextSet.delete(p.rawName)
    toggling.value = nextSet
  }
}

// --- install modal ---
const pluginInstallModal = ref(false)
const pluginUrl = ref('')
const pluginSha = ref('')
const installing = ref(false)
const installError = ref('')
function openInstall() { pluginUrl.value = ''; pluginSha.value = ''; installError.value = ''; pluginInstallModal.value = true }
function closePluginInstall() { pluginInstallModal.value = false }
function onPluginUrl(e) { pluginUrl.value = e.target.value }
function onPluginSha(e) { pluginSha.value = e.target.value }
const canSubmit = computed(() =>
  pluginUrl.value.startsWith('https://') &&
  (pluginUrl.value.endsWith('.tar.gz') || pluginUrl.value.endsWith('.tgz')) &&
  /^[a-fA-F0-9]{64}$/.test(pluginSha.value)
)
async function submitPluginInstall() {
  if (!canSubmit.value) return
  installing.value = true; installError.value = ''
  try {
    await api.post('/plugins/install', { url: pluginUrl.value, sha256: pluginSha.value.toLowerCase() })
    closePluginInstall()
    await load()
  } catch (e) {
    installError.value = e?.response?.data?.detail || e?.message || 'Install failed'
  } finally { installing.value = false }
}
async function uninstall(p) {
  const name = p.display_name || p.name
  const msg = (tr('plugins.uninstallConfirm') || 'Uninstall {name}?').replace('{name}', name)
  if (!await d2confirm(msg)) return
  try { await api.delete(`/plugins/${encodeURIComponent(p.name)}`); await load() }
  catch (e) { alert(e?.response?.data?.detail || e?.message || 'Uninstall failed') }
}

onMounted(() => {
  ui.set({ title: tr('nav.plugins') || 'Plugins', primary: { label: tr('plugins.install') || 'Install plugin', onClick: openInstall } })
  load()
})
</script>

<style scoped>
.mono { font-family: 'JetBrains Mono', monospace; }
.d2-refresh { margin-left: auto; height: 34px; padding: 0 13px; border: 1px solid var(--border-strong); background: var(--panel); color: var(--text-2); border-radius: 9px; font: inherit; font-size: 12.5px; font-weight: 550; cursor: pointer; }
.d2-refresh:hover { background: var(--panel-2); }
.d2-uninstall { height: 34px; padding: 0 13px; border: 1px solid var(--border-strong); background: var(--panel); color: var(--text-2); border-radius: 9px; font: inherit; font-size: 12.5px; font-weight: 550; cursor: pointer; }
.d2-uninstall:hover { background: var(--red-soft); color: var(--red); border-color: var(--red-soft); }
.d2-plugin-control { min-height:42px;display:flex;align-items:center;justify-content:space-between;gap:14px;padding-top:12px;border-top:1px solid var(--border); }
.d2-plugin-status { font-size:12.5px;font-weight:620; }
.d2-plugin-status.is-active { color:var(--green); }
.d2-plugin-status.is-warning { color:var(--orange); }
.d2-plugin-status.is-muted { color:var(--text-3); }
.d2-plugin-config { margin-top:3px;font-size:10.5px;color:var(--text-3);overflow-wrap:anywhere; }
.d2-switch { position:relative;width:42px;height:24px;padding:0;border:0;border-radius:999px;background:var(--gray-soft);box-shadow:inset 0 0 0 1px var(--border-strong);cursor:pointer;transition:.18s ease;flex:none; }
.d2-switch span { position:absolute;left:3px;top:3px;width:18px;height:18px;border-radius:50%;background:var(--panel);box-shadow:0 1px 4px rgba(0,0,0,.18);transition:.18s ease; }
.d2-switch.is-on { background:var(--accent);box-shadow:none; }
.d2-switch.is-on span { transform:translateX(18px); }
.d2-switch:disabled { opacity:.5;cursor:not-allowed; }
.d2-modal-in { width: 100%; height: 42px; border: 1px solid var(--border-strong); background: var(--panel-2); color: var(--text); border-radius: 10px; padding: 0 13px; outline: none; }
.d2-modal-in:focus { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-ring); background: var(--panel); }
</style>
