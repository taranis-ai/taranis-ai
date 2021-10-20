<template>
    <v-container class="login-screen pa-0 ma-0" fluid fill-height align-center justify-center>
        <v-container style="background-color: #c7c7c7; text-align: center; position: relative;" fluid>
            <img src="@/assets/taranis-logo-login.svg" alt="">
            <v-form @submit.prevent="authenticate" id="form" ref="form">
                <table width="420">
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
        },
    }
</script>

<style>
    /* Login Screen */
    .login-screen {
        background-color: #eee;
    }

    .login-screen .v-form .flex {
        border: 1px solid #eee;
        border-radius: 4px;
        height: 38px;
        width: 200px;
        background-color: white;
    }

    .login-screen .v-form .v-input {
        margin: 0;
        padding: 0;
    }

    .login-screen .offset-login {
        position: relative;
        height: 20%;
    }

    .login-screen div {
        text-align: center;
    }

    .login-screen .v-input {
        transform: scale(0.8);
        transform-origin: left;
    }

    .login-screen table {
        width: 550px;
        margin: 0 auto;
        padding-left: 64px;
    }

    .login-screen table td {
        padding: 0;
        margin: 0;
    }

    .login-screen table td.table-button {
        vertical-align: top;
    }

    .login-screen img {
        position: absolute;
        width: 400px;
        bottom: 0;
        left: 50%;
        transform: translate(-50%, -20%);
    }

    .login-screen .v-alert {
        position: absolute;
        transform: translate(10px, 74px);
    }

    .login-screen .v-input__slot {
        width: 200px;
    }
</style>