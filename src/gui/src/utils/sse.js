export function connectSSE() {
  if (import.meta.env.VITE_TARANIS_NG_CORE_SSE === undefined) {
    return
  }
  // this.$sse(
  //   `${import.meta.env.VITE_TARANIS_NG_CORE_SSE}?jwt=${this.$store.getters.getJWT}`,
  //   { format: 'json' }
  // ).then((sse) => {
  //   sse.subscribe('news-items-updated', (data) => {
  //     this.$root.$emit('news-items-updated', data)
  //   })
  //   sse.subscribe('report-items-updated', (data) => {
  //     this.$root.$emit('report-items-updated', data)
  //   })
  //   sse.subscribe('report-item-updated', (data) => {
  //     this.$root.$emit('report-item-updated', data)
  //   })
  //   sse.subscribe('report-item-locked', (data) => {
  //     this.$root.$emit('report-item-locked', data)
  //   })
  //   sse.subscribe('report-item-unlocked', (data) => {
  //     this.$root.$emit('report-item-unlocked', data)
  //   })
  // })
}

export function reconnectSSE() {
  if (this.sseConnection !== null) {
    this.sseConnection.close()
    this.sseConnection = null
  }
  this.connectSSE()
}
