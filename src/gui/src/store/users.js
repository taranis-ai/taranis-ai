const state = {
  users: []
}

const actions = {
  updateUsers(context, users) {
    context.commit('UPDATE_USERS', users)
  }
}

const mutations = {
  UPDATE_USERS(state, users) {
    state.users = users
  }
}

const getters = {
  getUsers(state) {
    return state.users
  },

  getUsernames(state) {
    return state.users.map((user) => user.username)
  },

  getUserById: (state) => (id) => {
    return state.users.find((user) => user.id === id)
  },

  getUsernameById: (state) => (id) => {
    return state.users.find((user) => user.id === id).username
  },

  getUsersSelectionList(state) {
    return state.users.map(function (user) {
      return { id: user.id, username: user.username }
    })
  }
}

export const users = {
  namespaced: true,
  state,
  actions,
  mutations,
  getters
}
