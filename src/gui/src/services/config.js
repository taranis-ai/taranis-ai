import axios from 'axios'

export async function getLocalConfig() {
  try {
    const configJson =
      typeof import.meta.env.VITE_TARANIS_CONFIG_JSON === 'undefined'
        ? '/config.json'
        : import.meta.env.VITE_TARANIS_CONFIG_JSON
    const response = await axios.get(configJson, { baseURL: '' })
    return response.data
  } catch (error) {
    if (error.response && error.response.status === 404) {
      console.error('Config file not found')
    } else {
      console.error('Error parsing config file:', error.message)
    }
    return null
  }
}
