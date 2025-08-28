<template>
  <div class="docx-viewer">
    <div v-if="error" class="error">Failed to render document: {{ error }}</div>
    <div v-else-if="html" v-html="html" class="docx-content" />
    <div v-else class="loading">Rendering…</div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import mammoth from 'mammoth'

const props = defineProps({
  base64: {
    type: String,
    required: true
  }
})

const html = ref('')
const error = ref(null)

async function renderDocx() {
  try {
    const arrayBuffer = Uint8Array.from(atob(props.base64), (c) =>
      c.charCodeAt(0)
    ).buffer
    const { value } = await mammoth.convertToHtml({ arrayBuffer })
    html.value = value
  } catch (e) {
    error.value = e.message || 'Unknown error'
  }
}

watch(
  () => props.base64,
  () => {
    html.value = ''
    error.value = null
    renderDocx()
  }
)

onMounted(renderDocx)
</script>

<style scoped>
.docx-viewer {
  overflow: auto;
}
.docx-content {
  padding: 1rem;
}
.loading,
.error {
  text-align: center;
  padding: 2rem;
  color: gray;
}
.error {
  color: red;
}
</style>
