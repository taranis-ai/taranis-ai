<template>
    <div>
        <ViewLayout>
            <template v-slot:panel>

                <v-container fluid class="toolbar-filter ma-0 pa-0 pb-2 cx-toolbar-filter primary">

                    <v-row class="row1">
                        <span class="display-1 primary--text ma-1 pl-4 view-heading">{{$t('nav_menu.enter')}}</span>
                    </v-row>
                </v-container>

            </template>
            <template v-slot:content>

                <v-form @submit.prevent="add" id="form" ref="form" style="width: 100%; padding: 8px">
                    <v-card>
                        <v-card-text>
                            <v-text-field
                                    :label="$t('enter.title')"
                                    name="title"
                                    type="text"
                                    v-model="news_item.title"
                                    v-validate="'required'"
                                    data-vv-name="title"
                                    :error-messages="errors.collect('title')"
                            ></v-text-field>

                            <v-textarea
                                    :label="$t('enter.review')"
                                    name="review"
                                    v-model="news_item.review"
                            ></v-textarea>

                            <v-text-field
                                    :label="$t('enter.source')"
                                    name="source"
                                    type="text"
                                    v-model="news_item.source"
                            ></v-text-field>

                            <v-text-field
                                    :label="$t('enter.link')"
                                    name="link"
                                    type="text"
                                    v-model="news_item.link"
                            ></v-text-field>

                            <ckeditor :editor="editor" v-model="editorData" :config="editorConfig"></ckeditor>

                        </v-card-text>
                    </v-card>
                    <v-spacer class="pt-2"></v-spacer>
                    <v-btn color="primary" @click="add()">{{$t('enter.create')}}</v-btn>
                </v-form>

                <v-alert v-if="show_validation_error" dense type="error" text>
                    {{$t('enter.validation_error')}}
                </v-alert>
                <v-alert v-if="show_error" dense type="error" text>{{$t('enter.error')}}
                </v-alert>

            </template>

        </ViewLayout>
    </div>

</template>

<style>
    .nri {
        display: none;
    }

    .toolbar-filter {
        box-shadow: 0px 1px 5px rgba(0, 0, 0, 0.4);
    }

    #app:not(.theme--dark) .toolbar-filter {
        box-shadow: 0px 1px 5px rgba(0, 0, 0, 0.15);
    }

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

<script>
    import ViewLayout from "../../components/layouts/ViewLayout";
    import ClassicEditor from '@ckeditor/ckeditor5-build-classic';
    import {addNewsItem} from "@/api/assess";

    export default {
        name: "Enter",
        components: {
            ViewLayout,

        },
        data: () => ({

            show_error: false,
            show_validation_error: false,

            editor: ClassicEditor,
            editorData: '<p></p>',
            editorConfig: {
                // The configuration of the editor.
            },

            news_item: {
                id: "",
                title: "",
                review: "",
                content: "",
                link: "",
                source: "",
                author: "",
                language: "",
                hash: "",
                osint_source_id: "",
                published: "",
                collected: "",
                attributes: []
            }
        }),
        methods: {

            add() {
                this.$validator.validateAll().then(() => {

                    if (!this.$validator.errors.any()) {

                        this.news_item.content = this.editorData;

                        let i = window.location.pathname.indexOf("/source/");
                        let len = window.location.pathname.length;
                        this.news_item.osint_source_id = window.location.pathname.substring(i + 8, len);

                        this.news_item.author = this.$store.getters.getUserName;
                        this.news_item.language = ((typeof(process.env.VUE_APP_TARANIS_NG_LOCALE) == "undefined") ? "$VUE_APP_TARANIS_NG_LOCALE" : process.env.VUE_APP_TARANIS_NG_LOCALE);

                        let d = new Date();
                        this.news_item.collected = this.appendLeadingZeroes(d.getDate()) + "." + this.appendLeadingZeroes(d.getMonth() + 1) + "." + d.getFullYear() +
                            " - " + this.appendLeadingZeroes(d.getHours()) + ":" + this.appendLeadingZeroes(d.getMinutes());
                        this.news_item.published = this.news_item.collected;

                        addNewsItem(this.news_item).then(() => {

                            this.news_item.id = ""
                            this.news_item.title = ""
                            this.news_item.review = ""
                            this.news_item.content = ""
                            this.news_item.link = ""
                            this.news_item.source = ""
                            this.news_item.author = ""
                            this.news_item.language = ""
                            this.news_item.hash = ""
                            this.news_item.osint_source_id = ""
                            this.news_item.published = ""
                            this.news_item.collected = ""
                            this.news_item.attributes = []

                            this.$validator.reset();

                            this.editorData = '<p></p>';

                            this.$root.$emit('notification',
                                {
                                    type: 'success',
                                    loc: 'enter.successful'
                                }
                            )

                        }).catch(() => {

                            this.show_error = true;
                        })

                    } else {

                        this.show_validation_error = true;
                    }
                })
            },

            appendLeadingZeroes(n) {
                if (n <= 9) {
                    return "0" + n;
                }
                return n
            }
        },

        created() {
        }
    };
</script>
