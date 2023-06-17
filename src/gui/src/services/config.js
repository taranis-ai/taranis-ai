import axios from 'axios'

export async function getLocalConfig() {
  try {
    const response = await axios.get('/config.json')
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
