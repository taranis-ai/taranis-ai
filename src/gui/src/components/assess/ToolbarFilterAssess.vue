<template>
    <v-container fluid class="toolbar-filter ma-0 pa-0 pb-2 cx-toolbar-filter primary">

        <!-- Heading -->
        <v-row class="row1">
            <span class="display-1 primary--text ma-1 pl-4 view-heading" style="height: 40px;">{{$t( title )}}</span>
            <v-spacer></v-spacer>

            <v-text-field class="search"
                          :placeholder="$t('toolbar_filter.search')"
                          prepend-inner-icon='mdi-card-search'
                          dense
                          v-on:keyup="filterSearch"
                          v-model="filter.search"
            ></v-text-field>

            <v-spacer></v-spacer>
            <!-- ADD NEW BUTTON -->
            <slot name="addbutton"></slot>
        </v-row>
        <v-divider></v-divider>

        <!-- Chips • USER -->
        <v-row class="user ml-5 mt-0">
            <!-- DAY-S -->
            <v-chip-group
                    active-class="info"
                    color="primary"
                    mandatory
            >
                <v-chip v-for="day in days" :key="day.filter" small class="px-0 mr-1" @click="filterRange(day.filter)">
                    <span class="px-3" :title="$t('assess.tooltip.range.' + day.filter)">{{$t(day.title)}}</span>
                </v-chip>
            </v-chip-group>

            <v-icon center color="grey lighten-2" class="mr-1">mdi-drag-vertical</v-icon>

            <!-- FAVORITES -->
            <v-chip-group
                    active-class="info"
                    color=""
                    multiple
                    class="pr-4"
            >
                <v-chip small class="px-0 mr-1" @click="filterRead">
                    <v-tooltip bottom>
                        <template v-slot:activator="{on}">
                            <v-icon small center class="px-2" :title="$t('assess.tooltip.filter_read')">mdi-eye-off</v-icon>
                        </template>
                        <span>{{ $t('assess.tooltip.filter_read') }}</span>
                    </v-tooltip>
                </v-chip>
                <v-chip small class="px-0 mr-1" @click="filterImportant">
                    <v-icon small center class="px-2" :title="$t('assess.tooltip.filter_important')">mdi-star-circle</v-icon>
                </v-chip>
                <v-chip small class="px-0 mr-1" @click="filterRelevant">
                    <v-icon small center class="px-2" :title="$t('assess.tooltip.filter_relevant')">mdi-thumb-up</v-icon>
                </v-chip>
                <v-chip small class="px-0 mr-1" @click="filterInAnalyze">
                    <v-icon small center class="px-2" :title="$t('assess.tooltip.filter_in_analyze')">mdi-file-cog-outline</v-icon>
                </v-chip>
            </v-chip-group>

            <v-spacer></v-spacer>

            <!-- SORT -->
            <v-chip-group
                    active-class="success"
                    color=""
                    class="pr-4"
                    mandatory

            >
                <v-chip small class="px-0 mr-1" @click="filterSort('DATE_DESC')" :title="$t('assess.tooltip.sort.date.descending')">
                    <v-icon class="pl-2" small center>mdi-clock-outline</v-icon>
                    <v-icon class="pr-2" small center>mdi-sort-descending</v-icon>
                </v-chip>
                <v-chip small class="px-0 mr-1" @click="filterSort('DATE_ASC')" :title="$t('assess.tooltip.sort.date.ascending')">
                    <v-icon class="pl-2" small center>mdi-clock-outline</v-icon>
                    <v-icon class="pr-2" small center>mdi-sort-ascending</v-icon>
                </v-chip>

                <v-chip small class="px-0 mr-1" @click="filterSort('RELEVANCE_DESC')" :title="$t('assess.tooltip.sort.relevance.descending')">
                    <v-icon class="pl-2" small center>mdi-thumb-up</v-icon>
                    <v-icon class="pr-2" small center>mdi-sort-descending</v-icon>
                </v-chip>
                <v-chip small class="px-0 mr-1" @click="filterSort('RELEVANCE_ASC')" :title="$t('assess.tooltip.sort.relevance.descending')">
                    <v-icon class="pl-2" small center>mdi-thumb-down</v-icon>
                    <v-icon class="pr-2" small center>mdi-sort-ascending</v-icon>
                </v-chip>
            </v-chip-group>
        </v-row>

        <v-divider v-if="!analyze_selector"></v-divider>
        <v-row v-if="!analyze_selector">
            <ToolbarGroupAssess ref="toolbarGroupAssess"/>
        </v-row>
        <v-divider class="pt-2"></v-divider>
        <v-row>
            <span class="total-count-text mx-5">{{$t(total_count_title)}}<strong>{{totalCount}}</strong></span>

            <v-spacer></v-spacer>
            <!-- Wordlist -->
            <v-btn x-small text @click="hideWordlist" class="wl pa-0 ma-0 mr-3" :title="$t('assess.tooltip.highlight_wordlist')">
                <v-icon v-if="word_list_toggle" center color="black" class="">mdi-alphabetical-variant-off</v-icon>
                <v-icon v-else center color="orange" class="">mdi-alphabetical-variant</v-icon>
            </v-btn>
        </v-row>

    </v-container>
</template>

<script>
    import AuthMixin from "../../services/auth/auth_mixin";
    import ToolbarGroupAssess from "@/components/assess/ToolbarGroupAssess";

    export default {
        name: "ToolbarFilterAssess",
        components: {
            ToolbarGroupAssess
        },
        props: {
            title: String,
            dialog: String,
            analyze_selector: Boolean,
            total_count_title: String,
        },
        computed: {
            totalCount() {
                return this.data_count
            }
        },
        data: () => ({
            status: [],
            days: [
                {title: 'toolbar_filter.all', icon: 'mdi-information-outline', type: 'info', filter: 'ALL'},
                {title: 'toolbar_filter.today', icon: 'mdi-calendar-today', type: 'info', filter: 'TODAY'},
                {title: 'toolbar_filter.this_week', icon: 'mdi-calendar-range', type: 'info', filter: 'WEEK'},
                {title: 'toolbar_filter.this_month', icon: 'mdi-calendar-month', type: 'info', filter: 'MONTH'}
            ],
            data_count: 0,
            filter: {
                search: "",
                range: "ALL",
                read: false,
                important: false,
                relevant: false,
                in_analyze: false,
                sort: "DATE_DESC"
            },
            timeout: null,
            word_list_toggle: false
        }),
        mixins: [AuthMixin],
        methods: {
            updateDataCount(count) {
                this.data_count = count
            },

            filterRead() {
                this.filter.read = !this.filter.read;
                this.$emit('update-news-items-filter', this.filter);
                if (this.analyze_selector === false) {
                    this.$refs.toolbarGroupAssess.disableMultiSelect()
                }
            },

            filterImportant() {
                this.filter.important = !this.filter.important;
                this.$emit('update-news-items-filter', this.filter);
                if (this.analyze_selector === false) {
                    this.$refs.toolbarGroupAssess.disableMultiSelect()
                }
            },

            filterRelevant() {
                this.filter.relevant = !this.filter.relevant;
                this.$emit('update-news-items-filter', this.filter);
                if (this.analyze_selector === false) {
                    this.$refs.toolbarGroupAssess.disableMultiSelect()
                }
            },

            filterInAnalyze() {
                this.filter.in_analyze = !this.filter.in_analyze;
                this.$emit('update-news-items-filter', this.filter);
                this.$refs.toolbarGroupAssess.disableMultiSelect()
            },

            filterSort(sort) {
                this.filter.sort = sort;
                this.$emit('update-news-items-filter', this.filter);
                if (this.analyze_selector === false) {
                    this.$refs.toolbarGroupAssess.disableMultiSelect()
                }
            },

            filterRange(range) {
                this.filter.range = range;
                this.$emit('update-news-items-filter', this.filter);
                if (this.analyze_selector === false) {
                    this.$refs.toolbarGroupAssess.disableMultiSelect()
                }
            },

            filterSearch: function () {
                clearTimeout(this.timeout);

                let self = this;
                this.timeout = setTimeout(function () {
                    self.$emit('update-news-items-filter', self.filter)
                    if (self.analyze_selector === false) {
                        self.$refs.toolbarGroupAssess.disableMultiSelect()
                    }
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
            /*callDialog: function (e) {
                this.$root.$emit('callDialog', e);
            },*/
            cancel() {
            },
            add() {
            },

            hideWordlist() {
                this.word_list_toggle = !this.word_list_toggle;

                if(this.word_list_toggle) {
                    document.getElementById("app").classList.add("hide-wordlist");
                } else {
                    document.getElementById("app").classList.remove("hide-wordlist");
                }
                localStorage.setItem('word-list-hide', this.word_list_toggle);

            }

        },
        mounted(){
            if( !localStorage.getItem('word-list-hide')) {
                localStorage.setItem('word-list-hide', false);
            } else {
                if( localStorage.getItem('word-list-hide') === "true") {
                    this.word_list_toggle = true;
                    document.getElementById("app").classList.add("hide-wordlist");
                } else {
                    this.word_list_toggle = false;
                    document.getElementById("app").classList.remove("hide-wordlist");
                }
            }
        }
    }
</script>

<style>
    #app button.wl {
        background-color: transparent !important;
    }
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