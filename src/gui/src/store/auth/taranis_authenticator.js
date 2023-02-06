import { authenticate, refresh } from '@/api/auth'
import ApiService from '@/services/api_service'

const state = {
  jwt: ''
}

const actions = {

  login(context, userData) {
    return authenticate(userData)
      .then(response => {
        context.commit('setJwtToken', response.data.access_token)
        context.dispatch('setUser', context.getters.getUserData)
      })
      .catch((error) => {
        context.commit('clearJwtToken')
        return error.toJSON()
      })
  },

  refresh(context) {
    return refresh()
      .then(response => {
        context.commit('setJwtToken', response.data.access_token)
        context.dispatch('setUser', context.getters.getUserData)
      })
      .catch(() => {
        context.commit('clearJwtToken')
      })
  },

  setToken(context, access_token) {
    context.commit('setJwtToken', access_token)
    context.dispatch('setUser', context.getters.getUserData)
  }
}

const mutations = {

  setJwtToken(state, access_token) {
    localStorage.ACCESS_TOKEN = access_token
    ApiService.setHeader()
    state.jwt = access_token
  },
  clearJwtToken(state) {
    localStorage.ACCESS_TOKEN = ''
    state.jwt = ''
  }
}

const getters = {

  getUserData(state) {
    const data = JSON.parse(atob(state.jwt.split('.')[1]))
    return data.user_claims
  },

  getSubjectName(state) {
    const data = JSON.parse(atob(state.jwt.split('.')[1]))
    return data.sub
  },

  hasExternalLoginUrl() {
    if (('$VUE_APP_TARANIS_NG_LOGIN_URL' !== '') && ('$VUE_APP_TARANIS_NG_LOGIN_URL'[0] !== '$')) { return true }
    if (typeof (process) !== 'undefined' && typeof (process.env) !== 'undefined') { return process.env.VUE_APP_TARANIS_NG_LOGIN_URL != null }
    return false
  },

  getLoginURL() {
    const own_base_uri = document.URL.replace(/^([^:]*:\/*[^\/]*)\/.*/, '$1'); //eslint-disable-line
    let login_uri = '/login'

    if (('$VUE_APP_TARANIS_NG_LOGIN_URL' !== '') && ('$VUE_APP_TARANIS_NG_LOGIN_URL'[0] !== '$')) {
      login_uri = '$VUE_APP_TARANIS_NG_LOGIN_URL'
    } else if (typeof (process) !== 'undefined' && typeof (process.env) !== 'undefined' && process.env.VUE_APP_TARANIS_NG_LOGIN_URL) {
      login_uri = process.env.VUE_APP_TARANIS_NG_LOGIN_URL
    }

    login_uri = login_uri.replace('TARANIS_GUI_URI', encodeURIComponent(own_base_uri + '/login'))
    return login_uri
  },

  hasExternalLogoutUrl() {
    if (('$VUE_APP_TARANIS_NG_LOGOUT_URL' !== '') && ('$VUE_APP_TARANIS_NG_LOGOUT_URL'[0] !== '$')) { return true }
    if (typeof (process) !== 'undefined' && typeof (process.env) !== 'undefined') { return process.env.VUE_APP_TARANIS_NG_LOGOUT_URL != null }
    return false
  },

  getLogoutURL() {
        const own_base_uri = document.URL.replace(/^([^:]*:\/*[^\/]*)\/.*/, '$1'); //eslint-disable-line
    let logout_uri = '/logout'

    if (('$VUE_APP_TARANIS_NG_LOGOUT_URL' !== '') && ('$VUE_APP_TARANIS_NG_LOGOUT_URL'[0] !== '$')) {
      logout_uri = '$VUE_APP_TARANIS_NG_LOGOUT_URL'
    } else if (typeof (process) !== 'undefined' && typeof (process.env) !== 'undefined' && process.env.VUE_APP_TARANIS_NG_LOGOUT_URL != null) {
      logout_uri = process.env.VUE_APP_TARANIS_NG_LOGOUT_URL
    }

    logout_uri = logout_uri.replace('TARANIS_GUI_URI', encodeURIComponent(own_base_uri + '/login'))
    return logout_uri
  },

  getJWT() {
    return state.jwt
  }
}

export const taranis_authenticator = {
  state,
  actions,
  mutations,
  getters
}
