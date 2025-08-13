<template>
  <div class="odf-viewer">
    <div v-if="error" class="error">Failed to render document: {{ error }}</div>
    <div v-else class="odf-container" ref="viewerContainer">
      <div v-if="loading" class="loading">Rendering…</div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'

const props = defineProps({
  base64: {
    type: String,
    required: true
  }
})

const viewerContainer = ref(null)
const loading = ref(true)
const error = ref(null)
let odfCanvas = null

async function renderOdt() {
  loading.value = true
  error.value = null

  try {
    const binaryString = atob(props.base64)
    const byteArray = new Uint8Array(binaryString.length)
    for (let i = 0; i < binaryString.length; i++) {
      byteArray[i] = binaryString.charCodeAt(i)
    }
    const blob = new Blob([byteArray], {
      type: 'application/vnd.oasis.opendocument.text'
    })
    const odfUrl = URL.createObjectURL(blob)

    if (!window.odf) throw new Error('WebODF not loaded')

    odfCanvas = new window.odf.OdfCanvas(viewerContainer.value)
    odfCanvas.load(odfUrl)
  } catch (e) {
    error.value = e.message || 'Unknown error'
  } finally {
    loading.value = false
  }
}

watch(() => props.base64, renderOdt)
onMounted(renderOdt)
</script>

<style scoped>
.odf-viewer {
  overflow: auto;
  position: relative;
}
.odf-container {
  min-height: 300px;
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
