<template>
    <div>
        <v-btn v-if="editAllowed()" depressed small color="white--text ma-2 mt-3 mr-5" @click="addAsset">
            <v-icon left>mdi-plus-circle-outline</v-icon>
            <span class="subtitle-2">{{$t('asset.add_new')}}</span>
        </v-btn>

        <v-row justify="center">
            <v-dialog v-model="visible" fullscreen hide-overlay transition="dialog-bottom-transition">
                <v-card>
                    <v-toolbar dark color="primary" style="z-index: 10000">

                        <v-btn icon dark @click="cancel">
                            <v-icon>mdi-close-circle</v-icon>
                        </v-btn>
                        <v-toolbar-title v-if="!edit">{{$t('asset.add_new')}}</v-toolbar-title>
                        <v-toolbar-title v-if="edit">{{$t('asset.edit')}}</v-toolbar-title>
                        <v-spacer></v-spacer>
                        <v-btn v-if="editAllowed()" text dark type="submit" form="form">
                            <v-icon left>mdi-content-save</v-icon>
                            <span>{{$t('asset.save')}}</span>
                        </v-btn>
                    </v-toolbar>

                    <v-form @submit.prevent="add" id="form" ref="form">
                        <v-card>
                            <v-card-text>
                                <v-text-field :disabled="!editAllowed()"
                                        :label="$t('asset.name')"
                                        name="name"
                                        type="text"
                                        v-model="asset.name"
                                        v-validate="'required'"
                                        data-vv-name="name"
                                        :error-messages="errors.collect('name')"
                                        :spellcheck="$store.state.settings.spellcheck"
                                ></v-text-field>
                                <v-text-field :disabled="!editAllowed()"
                                        :label="$t('asset.serial')"
                                        name="serial"
                                        type="text"
                                        v-model="asset.serial"
                                        :spellcheck="$store.state.settings.spellcheck"
                                ></v-text-field>
                                <v-textarea :disabled="!editAllowed()"
                                        :label="$t('asset.description')"
                                        name="description"
                                        v-model="asset.description"
                                        :spellcheck="$store.state.settings.spellcheck"
                                ></v-textarea>

                                <CPETable :cpes="asset.asset_cpes" @update-cpes="update"></CPETable>

                                <v-row v-if="edit">

                                    <v-card-title class="pl-0">{{$t('asset.vulnerabilities')}}</v-card-title>

                                    <component class="item-selector cs-cards" v-bind:is="cardLayout()"
                                               v-for="vulnerability in vulnerabilities"
                                               :card="vulnerability"
                                               :key="vulnerability.id"
                                               :asset="asset"
                                               :showToolbar="true">
                                    </component>

                                </v-row>

                            </v-card-text>
                        </v-card>
                    </v-form>
                    <v-alert v-if="show_validation_error" dense type="error" text>
                        {{$t('asset.validation_error')}}
                    </v-alert>
                    <v-alert v-if="show_error" dense type="error" text>{{$t('asset.error')}}
                    </v-alert>

                </v-card>

            </v-dialog>
        </v-row>
    </div>

</template>

<script>
    import {createNewAsset} from "@/api/assets";
    import {updateAsset} from "@/api/assets";
    import CPETable from "@/components/assets/CPETable";
    import CardVulnerability from "@/components/assets/CardVulnerability";
    import AuthMixin from "@/services/auth/auth_mixin";
    import Permissions from "@/services/auth/permissions";

    export default {
        name: "NewAsset",
        mixins: [AuthMixin],
        components: {
            CPETable,
            CardVulnerability
        },
        data: () => ({
            visible: false,
            edit: false,
            show_validation_error: false,
            show_error: false,
            vulnerabilities: [],
            asset: {
                id: -1,
                name: "",
                serial: "",
                description: "",
                asset_cpes: [],
                asset_group_id: ""
            }
        }),
        methods: {
            editAllowed() {
                return this.checkPermission(Permissions.MY_ASSETS_CREATE)
            },
            cardLayout() {
                return "CardVulnerability"
            },
            addAsset() {
                this.visible = true;
                this.edit = false
                this.show_error = false;
                this.asset.id = -1;
                this.asset.name = "";
                this.asset.serial = "";
                this.asset.description = "";
                this.asset.asset_cpes = [];
                this.asset.asset_group_id = "";
                this.$validator.reset();
            },

            cancel() {
                this.$validator.reset();
                this.visible = false
                this.$root.$emit('update-data')
            },

            add() {
                this.$validator.validateAll().then(() => {

                    if (!this.$validator.errors.any()) {

                        this.show_validation_error = false;
                        this.show_error = false;

                        if (window.location.pathname.includes("/group/")) {

                            let i = window.location.pathname.indexOf("/group/");
                            let len = window.location.pathname.length;
                            this.asset.asset_group_id = window.location.pathname.substring(i + 7, len);
                        }

                        for (let i = 0; i < this.asset.asset_cpes.length; i++) {
                            this.asset.asset_cpes[i].value = this.asset.asset_cpes[i].value.replace("*", "%")
                        }

                        if (this.edit === true) {
                            updateAsset(this.asset).then(() => {

                                this.$validator.reset();
                                this.visible = false;
                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'asset.successful_edit'
                                    }
                                )
                            }).catch(() => {

                                this.show_error = true;
                            })
                        } else {
                            createNewAsset(this.asset).then(() => {

                                this.$validator.reset();
                                this.visible = false;
                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'asset.successful'
                                    }
                                )
                            }).catch(() => {

                                this.show_error = true;
                            })
                        }

                    } else {

                        this.show_validation_error = true;
                    }
                })
            },

            update(cpes) {
                this.asset.asset_cpes = cpes;
            }
        },
        mounted() {
            this.$root.$on('show-edit', (data) => {

                this.visible = true;
                this.edit = true
                this.show_error = false;

                this.asset.id = data.id;
                this.asset.name = data.name;
                this.asset.serial = data.serial;
                this.asset.description = data.description;
                this.asset.asset_group_id = data.group_id

                this.asset.asset_cpes = []
                for (let i = 0; i < data.asset_cpes.length; i++) {
                    this.asset.asset_cpes.push({
                        value: data.asset_cpes[i].value.replace("%", "*"),
                    })
                }

                this.vulnerabilities = data.vulnerabilities
            });
        },
        beforeDestroy() {
            this.$root.$off('show-edit')
        }
    }
</script>

<style>
    .row {
        margin-left: 0;
    }
    .container.item-selector,
    .item-selector .row {
        margin-right: 0;
        margin-left: 0;
        /*position: fixed;*/
    }

    .cs-inside {
        position: fixed;
        height: 100%;
        width: calc(100% + 0px);
        overflow: auto;
    }

    .cs-inside .cs-panel,
    .cs-inside .cs-content {
        position: relative;
        padding: 0;
    }

    .cs-inside .cs-panel {
        max-width: 96px;
        background-color: #484848;
        z-index: 200;
        position: fixed;
        height: 100%;
        padding-left: 0px;
        text-align: center;
    }

    .cs-inside .cs-panel a {
        margin: 0;
        padding: 0;
    }

    .cs-inside .cs-content {
        max-width: calc(100% - 96px);
        margin-left: 96px;
    }

    .cx-toolbar-filter {
        position: sticky;
        top: 0;
        z-index: 100;
    }

    .cs-cards {
        position: relative;
        float: left;
        width: calc(100% - 28px);
        margin-left: 0px;

    }

    #selector .card.focus {
        background-color: #caecff;
    }

    .card .obj.center {
        text-align: center;
    }

    .card.elevation-12 {
        z-index: 1;
        background-color: rgba(100, 137, 214, 0.1);
    }

    .v-speed-dial {
        position: absolute;
        right: 0;
        padding-top: 40px;
    }

    .card-assess .col {
        margin: 0;
        padding: 0;
    }

    .cs-panel.col .v-list-item.active {
        background-color: rgba(255, 255, 255, 0.1);
    }

    .cs-inside .cs-panel .v-list-item__title {
        white-space: normal;
        font-size: 10px;
    }

    .newdial .v-speed-dial__list {
        width: 400px;
    }

    .newdialshort .v-speed-dial__list {
        width: 80px;
    }
</style>
