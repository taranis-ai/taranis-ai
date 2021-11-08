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
        <v-alert v-if="show_login_error" dense type="error" text>{{$t('login.error')}}</v-alert>
    </v-container>
</template>

<script>

    import AuthMixin from "@/services/auth/auth_mixin";

    export default {
        name: 'Login',
        data: () => ({
            username: '',
            password: '',
            show_login_error: false
        }),
        mixins: [AuthMixin],
        methods: {
            authenticate() {
                this.$validator.validateAll().then(() => {

                    if (!this.$validator.errors.any()) {
                        this.$store.dispatch('login', {username: this.username, password: this.password})
                            .then(() => {
                                if (this.isAuthenticated()) {
                                    this.show_login_error = false;
                                    this.$router.push('/')
                                    this.$store.dispatch('getUserProfile').then(() => {
                                        this.$vuetify.theme.dark = this.$store.getters.getProfileDarkTheme
                                    });
                                    this.$root.$emit('logged-in')
                                } else {
                                    this.show_login_error = true;
                                    this.$refs.form.reset();
                                    this.$validator.reset()
                                }
                            })
                    } else {

                        this.show_login_error = false;
                    }
                })
            }
        }
    }
</script>