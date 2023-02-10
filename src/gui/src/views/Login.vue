<template>
  <v-container class="login-screen pa-0 ma-0" fluid fill-height align-center justify-center>
    <v-container style="background-color: #c7c7c7; text-align: center; position: relative;" fluid>
      <img src="@/assets/taranis-logo-login.svg" alt="">
      <v-form @submit.prevent="authenticate" id="form" ref="form">
        <table>
          <tr>
            <td>
              <v-flex>
                <v-text-field
                  :placeholder="$t('login.username')"
                  name="username"
                  prepend-icon="person"
                  type="text"
                  v-model="username"
                  v-validate="'required'"
                  data-vv-name="username"
                  :error-messages="errors.collect('username')"
                  required
                />
              </v-flex>
            </td>
            <td>
              <v-flex>
                <v-text-field
                  :placeholder="$t('login.password')"
                  name="password"
                  prepend-icon="lock"
                  type="password"
                  v-model="password"
                  v-validate="'required'"
                  :error-messages="errors.collect('password')"
                  data-vv-name="password"
                  required
                ></v-text-field>
              </v-flex>
            </td>
            <td>
              <v-btn text type="submit" form="form">
                <v-icon color="white" large>mdi-login-variant</v-icon>
              </v-btn>
            </td>
          </tr>
        </table>
      </v-form>
    </v-container>
    <v-alert v-if="login_error !== undefined" dense type="error" text>{{$t(login_error)}}</v-alert>
  </v-container>
</template>

<script>
import AuthMixin from '@/services/auth/auth_mixin'
import { mapActions } from 'vuex'

export default {
  name: 'Login',
  data: () => ({
    username: '',
    password: '',
    login_error: undefined
  }),
  mixins: [AuthMixin],
  methods: {
    ...mapActions(['login']),
    authenticate () {
      this.$validator.validateAll().then(() => {
        if (!this.$validator.errors.any()) {
          this.login({ username: this.username, password: this.password })
            .then((error) => {
              if (this.isAuthenticated()) {
                this.login_error = undefined
                this.$router.push('/')
                return
              }
              if (error) {
                this.$refs.form.reset()
                this.$validator.reset()
                if (error.status > 500) {
                  this.login_error = 'login.backend_error'
                } else {
                  this.login_error = 'login.error'
                }
              }
            })
        } else {
          this.login_error = undefined
        }
      })
    }
  }
}
</script>
