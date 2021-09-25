<template>
    <v-container fluid class="toolbar-filter ma-0 pa-0 pb-2 cx-toolbar-filter primary">

        <!-- Heading -->
        <v-row class="row1">
            <span class="display-1 primary--text ma-1 pl-4 view-heading">{{$t( title )}}</span>
            <v-spacer></v-spacer>

            <v-text-field class="search"
                          :placeholder="$t('toolbar_filter.search')"
                          prepend-inner-icon='mdi-card-search'
                          dense
                          v-on:keyup="filterSearch"
                          v-model="filter.search"
            ></v-text-field>

            <v-spacer></v-spacer>
            <slot name="addbutton"></slot>
        </v-row>
        <v-divider class="pt-2"></v-divider>
        <v-row>
            <span class="total-count-text pl-5">{{$t(total_count_title)}}<strong>{{totalCount}}</strong></span>
        </v-row>

    </v-container>
</template>

<script>
    import AuthMixin from "../../services/auth/auth_mixin";

    export default {
        name: "ToolbarFilter",
        props: {
            title: String,
            dialog: String,
            total_count_title: String,
            total_count_getter: String
        },
        computed: {
            totalCount() {
                return this.$store.getters[this.total_count_getter].total_count
            }
        },
        data: () => ({
            filter: {
                search: "",
            },
            timeout: null
        }),
        mixins: [AuthMixin],
        methods: {
            filterSearch: function() {
                clearTimeout(this.timeout);

                let self = this;
                this.timeout = setTimeout(function(){
                    self.$root.$emit('update-items-filter', self.filter)
                },800);
            },
            changeTheme() {
                this.$vuetify.theme.themes.light.primary = "#f0f";
                this.$vuetify.theme.themes.light.secondary = '#f00';
                this.$vuetify.theme.themes.light.bg = '#0f0';
                this.$vuetify.theme.themes.light.base = '#00f';
            },
            remove(item) {
                this.chips.splice(this.chips.indexOf(item), 1);
                this.chips = [...this.chips]
            },
            /*callDialog: function (e) {
                this.$root.$emit('callDialog', e);
            },*/
            cancel() {
            },
            add() {
            }
        }
    }
</script>

<style>
    .toolbar-filter {
        box-shadow: 0px 1px 5px rgba(0, 0, 0, 0.4);
    }

    #app:not(.theme--dark) .toolbar-filter {
        box-shadow: 0px 1px 5px rgba(0, 0, 0, 0.15);
    }

    /*.toolbar-filter .row1 {
        border-bottom: 1px solid #ddd;
    }*/

    .toolbar-filter .row1 .view-heading {
        text-transform: uppercase;
        font-weight: 300;
    }

    .toolbar-filter .custom-filter {
        height: 32px;
    }

    .toolbar-filter .custom-filter .v-input__control {
        min-height: 32px;
    }

    .toolbar-filter .custom-filter .v-input__control .v-input__slot {
        padding: 0;
        padding-left: 0.1em;
    }

    .toolbar-filter .custom-filter .v-select__selections {
        min-height: 32px;
    }

    .toolbar-filter .custom-filter .filter-tag {
        height: 22px;
    }

    .toolbar-filter .custom-filter [placeholder]::placeholder {
        font-size: 0.8em;
        padding-left: 1em;
    }

    .toolbar-filter .admin .v-chip.v-chip--active,
    .toolbar-filter .user .v-chip.v-chip--active {
        opacity: 1;
    }

    .toolbar-filter .admin .v-chip:not(.v-chip--active),
    .toolbar-filter .user .v-chip:not(.v-chip--active) {
        opacity: 0.5;
    }

    .toolbar-filter .v-chip:not(.v-chip--active):hover {
        opacity: 1;
    }

    .search {
        padding-top: 0;
        padding-left: 8px;
        padding-right: 8px;
        margin-top: 8px;
        height: 32px;
        background-color: #f8f8f8;
        border-radius: 4px;
    }

    .v-chip-group .v-slide-group__content {
        padding-top: 0 !important;
    }

    .v-chip-group .v-chip.filter {
        height: 20px;
        margin-top: 5px;
    }

</style>