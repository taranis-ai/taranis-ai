export function connectSSE() {
  const coreAPIURL = import.meta.env.VITE_TARANIS_CORE_SSE
  if (!coreAPIURL) {
    console.error('SSE URL is not defined.')
    return
  }

  const sseEndpoint = `${coreAPIURL}/sse`
  const evtSource = new EventSource(sseEndpoint)

  evtSource.onopen = () => console.debug('SSE connection opened.')
  evtSource.onerror = (event) => console.error('SSE connection error:', event)
  /*evtSource.onerror = (event) => {
    console.error('SSE connection error:', event)
    // Attempt to reconnect
    evtSource.close(); // Close current connection
    setTimeout(connectSSE, 5000) // Attempt reconnecting after some delay
  }*/

  const events = [
    'news-items-updated',
    'report-item-updated',
    'product-rendered',
    'report-item-locked',
    'report-item-unlocked'
  ]

  events.forEach((event) => {
    evtSource.addEventListener(event, (e) => {
      console.debug(`Event received - ${event}:`, e.data)
    })
  })

  this.sseConnection = evtSource
}

export function reconnectSSE() {
  if (this.sseConnection) {
    this.sseConnection.close()
    console.debug('SSE connection closed.')
  }

  this.connectSSE()
}
