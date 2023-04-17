import { authenticate, refresh } from '@/api/auth'
import ApiService from '@/services/api_service'
import { Base64 } from 'js-base64'

const state = {
  jwt: '',
  login_uri: '/login',
  logout_uri: '/logout',
  external_login_uri: false,
  external_logout_uri: false,
  user: {},
  sub: '',
  exp: ''
}

const actions = {
  login(context, userData) {
    return authenticate(userData)
      .then((response) => {
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
      .then((response) => {
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
  },

  setAuthURLs(context) {
    context.commit('setLoginURL')
    context.commit('setLogoutURL')
  }
}

const mutations = {
  setJwtToken(state, access_token) {
    localStorage.ACCESS_TOKEN = access_token
    ApiService.setHeader()
    state.jwt = access_token
    const data = JSON.parse(Base64.decode(access_token.split('.')[1]))
    state.user = data.user_claims
    state.sub = data.sub
    state.exp = data.exp
  },
  clearJwtToken(state) {
    localStorage.ACCESS_TOKEN = ''
    state.jwt = ''
  },
  setLoginURL(state) {
    if (
      '$VUE_APP_TARANIS_NG_LOGIN_URL' !== '' &&
      '$VUE_APP_TARANIS_NG_LOGIN_URL'[0] !== '$'
    ) {
      state.login_uri = '$VUE_APP_TARANIS_NG_LOGIN_URL'
      state.external_login_uri = true
    }
    if (process.env.VUE_APP_TARANIS_NG_LOGIN_URL) {
      state.login_uri = process.env.VUE_APP_TARANIS_NG_LOGIN_URL
      state.external_login_uri = true
    }
  },
  setLogoutURL(state) {
    if (
      '$VUE_APP_TARANIS_NG_LOGOUT_URL' !== '' &&
      '$VUE_APP_TARANIS_NG_LOGOUT_URL'[0] !== '$'
    ) {
      state.logout_uri = '$VUE_APP_TARANIS_NG_LOGOUT_URL'
      state.external_logout_uri = true
    } else if (
      typeof process !== 'undefined' &&
      typeof process.env !== 'undefined' &&
      process.env.VUE_APP_TARANIS_NG_LOGOUT_URL != null
    ) {
      state.logout_uri = process.env.VUE_APP_TARANIS_NG_LOGOUT_URL
      state.external_logout_uri = true
    }
  }
}

const getters = {
  getUserData(state) {
    return state.user
  },

  getSubjectName(state) {
    return state.sub
  },

  getLoginURL(state) {
    return state.login_uri
  },

  getLogoutURL(state) {
    return state.logout_uri
  },

  hasExternalLoginUrl(state) {
    return state.external_login_uri
  },

  hasExternalLogoutUrl(state) {
    return state.external_logout_uri
  },

  getJWT(state) {
    return state.jwt
  },

  getExpiration(state) {
    return new Date(state.exp * 1000)
  },

  isAuthenticated(state) {
    const exp = new Date(state.exp * 1000)
    const now = new Date()
    return now < exp
  },

  needTokenRefresh(state) {
    const exp = new Date((state - 300) * 1000)
    const now = new Date()
    return now > exp
  }
}

export const taranis_authenticator = {
  state,
  actions,
  mutations,
  getters
}
