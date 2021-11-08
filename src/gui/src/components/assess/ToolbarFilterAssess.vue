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
                <!-- DAY-S -->
                <v-chip-group v-bind="UI.TOOLBAR.GROUP.DAYS">
                    <v-chip v-bind="UI.TOOLBAR.CHIP.GROUP"
                        v-for="day in days" :key="day.filter" @click="filterRange(day.filter)">
                        <div class="px-2" :title="$t('assess.tooltip.range.' + day.filter)">{{$t(day.title)}}</div>
                    </v-chip>
                </v-chip-group>

                <v-icon v-bind="UI.TOOLBAR.ICON.CHIPS_SEPARATOR">{{ UI.ICON.SEPARATOR }}</v-icon>

                <!-- FAVORITES -->
                <v-chip-group v-bind="UI.TOOLBAR.GROUP.FAVORITES">
                    <v-chip v-bind="UI.TOOLBAR.CHIP.GROUP" @click="filterRead">
                        <v-icon v-bind="UI.TOOLBAR.ICON.FAVORITES_CHIP" :title="$t('assess.tooltip.filter_read')">{{ UI.ICON.UNREAD }}</v-icon>
                    </v-chip>
                    <v-chip  v-bind="UI.TOOLBAR.CHIP.GROUP" @click="filterImportant">
                        <v-icon v-bind="UI.TOOLBAR.ICON.FAVORITES_CHIP" :title="$t('assess.tooltip.filter_important')">{{ UI.ICON.IMPORTANT }}</v-icon>
                    </v-chip>
                    <v-chip v-bind="UI.TOOLBAR.CHIP.GROUP" @click="filterRelevant">
                        <v-icon v-bind="UI.TOOLBAR.ICON.FAVORITES_CHIP" :title="$t('assess.tooltip.filter_relevant')">{{ UI.ICON.RELEVANT }}</v-icon>
                    </v-chip>
                    <v-chip v-bind="UI.TOOLBAR.CHIP.GROUP" @click="filterInAnalyze">
                        <v-icon v-bind="UI.TOOLBAR.ICON.FAVORITES_CHIP" :title="$t('assess.tooltip.filter_in_analyze')">{{ UI.ICON.IN_ANALYZE }}</v-icon>
                    </v-chip>
                </v-chip-group>

                <!-- SORT -->
                <v-chip-group v-bind="UI.TOOLBAR.GROUP.SORT">
                    <v-chip v-bind="UI.TOOLBAR.CHIP.GROUP" @click="filterSort('DATE_DESC')" :title="$t('assess.tooltip.sort.date.descending')">
                        <v-icon v-bind="UI.TOOLBAR.ICON.SORT_CHIP_A">{{ UI.ICON.CLOCK }}</v-icon>
                        <v-icon v-bind="UI.TOOLBAR.ICON.SORT_CHIP_B">{{ UI.ICON.DESC }}</v-icon>
                    </v-chip>
                    <v-chip v-bind="UI.TOOLBAR.CHIP.GROUP" @click="filterSort('DATE_ASC')" :title="$t('assess.tooltip.sort.date.ascending')">
                        <v-icon v-bind="UI.TOOLBAR.ICON.SORT_CHIP_A">{{ UI.ICON.CLOCK }}</v-icon>
                        <v-icon v-bind="UI.TOOLBAR.ICON.SORT_CHIP_B">{{ UI.ICON.ASC }}</v-icon>
                    </v-chip>

                    <v-chip v-bind="UI.TOOLBAR.CHIP.GROUP" @click="filterSort('RELEVANCE_DESC')" :title="$t('assess.tooltip.sort.relevance.descending')">
                        <v-icon v-bind="UI.TOOLBAR.ICON.SORT_CHIP_A">{{ UI.ICON.LIKE }}</v-icon>
                        <v-icon v-bind="UI.TOOLBAR.ICON.SORT_CHIP_B">{{ UI.ICON.DESC }}</v-icon>
                    </v-chip>
                    <v-chip v-bind="UI.TOOLBAR.CHIP.GROUP" @click="filterSort('RELEVANCE_ASC')" :title="$t('assess.tooltip.sort.relevance.descending')">
                        <v-icon v-bind="UI.TOOLBAR.ICON.SORT_CHIP_A">{{ UI.ICON.UNLIKE }}</v-icon>
                        <v-icon v-bind="UI.TOOLBAR.ICON.SORT_CHIP_B">{{ UI.ICON.ASC }}</v-icon>
                    </v-chip>
                </v-chip-group>
            </v-col>
        </v-row>
        <v-divider v-if="!analyze_selector"></v-divider>
        <v-row v-bind="UI.TOOLBAR.ROW" v-if="!analyze_selector">
            <v-col v-bind="UI.TOOLBAR.COL.SELECTOR">
                <ToolbarGroupAssess ref="toolbarGroupAssess"/>
            </v-col>
        </v-row>
        <v-divider></v-divider>
        <v-row v-bind="UI.TOOLBAR.ROW">
            <v-col v-bind="UI.TOOLBAR.COL.INFO">
                <span>{{$t(total_count_title)}}<strong>{{totalCount}}</strong></span>
            </v-col>
            <v-col v-bind="UI.TOOLBAR.COL.RIGHT">
                <!-- Wordlist -->
                <v-btn x-small text @click="hideWordlist" class="ma-0 pa-0 d-block" :title="$t('assess.tooltip.highlight_wordlist')">
                    <v-icon v-if="word_list_toggle" center color="black">mdi-alphabetical-variant-off</v-icon>
                    <v-icon v-else center color="orange">mdi-alphabetical-variant</v-icon>
                </v-btn>
            </v-col>
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