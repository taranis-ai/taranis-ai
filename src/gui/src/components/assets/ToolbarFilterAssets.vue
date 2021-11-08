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
            <v-col class="py-0">
                <!-- FAVORITES -->
                <v-chip-group v-bind="UI.TOOLBAR.GROUP.FAVORITES">
                    <v-chip v-bind="UI.TOOLBAR.CHIP.GROUP" @click="filterVulnerable">
                        <v-icon v-bind="UI.TOOLBAR.ICON.FAVORITES_CHIP" :title="$t('assess.tooltip.filter_read')">{{ UI.ICON.VULNERABLE }}</v-icon>
                    </v-chip>
                </v-chip-group>

                <!-- SORT -->
                <v-chip-group v-bind="UI.TOOLBAR.GROUP.SORT">
                    <v-chip v-bind="UI.TOOLBAR.CHIP.GROUP" @click="filterSort('ALPHABETICAL')" :title="$t('assess.tooltip.sort.date.descending')">
                        <v-icon v-bind="UI.TOOLBAR.ICON.SORT_CHIP_A">{{ UI.ICON.ALPHABETICAL }}</v-icon>
                        <v-icon v-bind="UI.TOOLBAR.ICON.SORT_CHIP_B">{{ UI.ICON.DESC }}</v-icon>
                    </v-chip>
                    <v-chip v-bind="UI.TOOLBAR.CHIP.GROUP" @click="filterSort('VULNERABILITY')" :title="$t('assess.tooltip.sort.date.ascending')">
                        <v-icon v-bind="UI.TOOLBAR.ICON.SORT_CHIP_A">{{ UI.ICON.VULNERABLE }}</v-icon>
                        <v-icon v-bind="UI.TOOLBAR.ICON.SORT_CHIP_B">{{ UI.ICON.ASC }}</v-icon>
                    </v-chip>
                </v-chip-group>
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
        name: "ToolbarFilterAssets",
        props: {
            title: String,
            dialog: String,
            total_count_title: String,
        },
        components: {},
        computed: {
            totalCount() {
                return this.$store.getters.getAssets.total_count;
            }
        },
        data: () => ({
            filter: {
                search: "",
                vulnerable: false,
                sort: "ALPHABETICAL"
            }
        }),
        mixins: [AuthMixin],
        methods: {
            filterVulnerable() {
                this.filter.vulnerable = !this.filter.vulnerable;
                this.$root.$emit('update-assets-filter', this.filter);
            },
            filterSort(sort) {
                this.filter.sort = sort;
                this.$root.$emit('update-assets-filter', this.filter);
            },
            filterSearch() {
                clearTimeout(this.timeout);

                this.timeout = setTimeout(function () {
                    this.$root.$emit('update-assets-filter', this.filter);
                }, 300);
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
            callDialog: function (e) {
                this.$root.$emit('callDialog', e);
            },
        }
    }
</script>