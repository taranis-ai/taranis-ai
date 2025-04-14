import axios from 'axios'

export async function getLocalConfig() {
  try {
    const configJson =
      typeof import.meta.env.VITE_TARANIS_CONFIG_JSON === 'undefined'
        ? '/config.json'
        : import.meta.env.VITE_TARANIS_CONFIG_JSON

    console.debug(`Loading config from ${configJson}`)

    const response = await axios.get(configJson, {
      baseURL: import.meta.env.BASE_URL
    })
    return JSON.parse(JSON.stringify(response.data))
  } catch (error) {
    if (error.response && error.response.status === 404) {
      console.error('Config file not found')
    } else {
      console.error('Error parsing config file:', error.message)
    }
    return {
      TARANIS_CORE_API: '/api'
    }
  }
}
