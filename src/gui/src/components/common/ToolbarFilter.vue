<template>
    <v-container v-bind="UI.TOOLBAR.CONTAINER" :style="UI.STYLE.shadow">
        <v-row v-bind="UI.TOOLBAR.ROW">
            <v-col v-bind="UI.TOOLBAR.COL.LEFT">
                <div :class="UI.CLASS.toolbar_filter_title">{{$t( title )}}</div>
            </v-col>
            <v-col v-bind="UI.TOOLBAR.COL.MIDDLE">
                <v-text-field v-bind="UI.ELEMENT.SEARCH" v-model="filter.search"
                              :placeholder="$t('toolbar_filter.search')"
                              v-on:keyup="filterSearch" />
            </v-col>
            <v-col v-bind="UI.TOOLBAR.COL.RIGHT">
                <slot name="addbutton"></slot>
            </v-col>
        </v-row>
        <v-divider></v-divider>
        <v-row v-bind="UI.TOOLBAR.ROW">
            <v-col v-bind="UI.TOOLBAR.COL.INFO">
                <span>{{$t(total_count_title)}}<strong>{{totalCount}}</strong></span>
            </v-col>
            <v-col v-bind="UI.TOOLBAR.COL.RIGHT"></v-col>
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
            }
        }
    }
</script>