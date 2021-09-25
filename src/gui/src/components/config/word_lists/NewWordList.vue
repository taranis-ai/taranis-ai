<template>
    <div>
        <v-btn v-if="canCreate" depressed small color="white--text ma-2 mt-3 mr-5" @click="addWordList">
            <v-icon left>mdi-plus-circle-outline</v-icon>
            <span class="subtitle-2">{{$t('word_list.add_btn')}}</span>
        </v-btn>

        <v-row justify="center">
            <v-dialog v-model="visible" fullscreen hide-overlay transition="dialog-bottom-transition">
                <v-card>
                    <v-toolbar dark color="primary" style="z-index: 10000">

                        <v-btn icon dark @click="cancel">
                            <v-icon>mdi-close-circle</v-icon>
                        </v-btn>
                        <v-toolbar-title v-if="!edit">{{$t('word_list.add_new')}}</v-toolbar-title>
                        <v-toolbar-title v-if="edit">{{$t('word_list.edit')}}</v-toolbar-title>
                        <v-spacer></v-spacer>
                        <v-btn v-if="canUpdate" text dark type="submit" form="form">
                            <v-icon left>mdi-content-save</v-icon>
                            <span>{{$t('word_list.save')}}</span>
                        </v-btn>
                    </v-toolbar>

                    <v-form @submit.prevent="add" id="form" ref="form">
                        <v-card>
                            <v-card-text>

                                <span v-if="edit">ID: {{word_list.id}}</span>

                                <v-text-field :disabled="!canUpdate"
                                        :label="$t('word_list.name')"
                                        name="name"
                                        type="text"
                                        v-model="word_list.name"
                                        v-validate="'required'"
                                        data-vv-name="name"
                                        :error-messages="errors.collect('name')"
                                        :spellcheck="$store.state.settings.spellcheck"
                                ></v-text-field>
                                <v-textarea :disabled="!canUpdate"
                                        :label="$t('word_list.description')"
                                        name="description"
                                        v-model="word_list.description"
                                        :spellcheck="$store.state.settings.spellcheck"
                                ></v-textarea>

                                <v-checkbox :disabled="!canUpdate"
                                            :label="$t('word_list.use_for_stop_words')"
                                            name="use_for_stop_words"
                                            v-model="word_list.use_for_stop_words"
                                ></v-checkbox>

                                <v-btn v-if="canUpdate" color="primary" @click="addCategory">
                                    <v-icon left>mdi-plus</v-icon>
                                    <span>{{$t('word_list.new_category')}}</span>
                                </v-btn>

                                <v-card style="margin-top: 8px" v-for="(category, index) in word_list.categories"
                                        :key="category.index">

                                    <v-toolbar dark height="32px">
                                        <v-spacer></v-spacer>
                                        <v-toolbar-items v-if="canUpdate">
                                            <v-icon
                                                    @click="deleteCategory(index)"
                                            >
                                                delete
                                            </v-icon>
                                        </v-toolbar-items>
                                    </v-toolbar>

                                    <v-card-text>
                                        <v-text-field :disabled="!canUpdate"
                                                :label="$t('word_list.name')"
                                                name="category_name"
                                                type="text"
                                                v-model="category.name"
                                                :spellcheck="$store.state.settings.spellcheck"
                                        ></v-text-field>
                                        <v-textarea :disabled="!canUpdate"
                                                :label="$t('word_list.description')"
                                                name="category_description"
                                                v-model="category.description"
                                                :spellcheck="$store.state.settings.spellcheck"
                                        ></v-textarea>

                                        <WordTable :disabled="!canUpdate"
                                                :words="word_list.categories[index].entries"
                                                   :id="index"
                                                @update-categories="update"
                                        ></WordTable>

                                    </v-card-text>
                                </v-card>

                            </v-card-text>
                        </v-card>
                    </v-form>
                    <v-alert v-if="show_validation_error" dense type="error" text>
                        {{$t('word_list.validation_error')}}
                    </v-alert>
                    <v-alert v-if="show_error" dense type="error" text>{{$t('word_list.error')}}
                    </v-alert>
                </v-card>
            </v-dialog>
        </v-row>
    </div>

</template>

<script>
    import {createNewWordList} from "@/api/config";
    import {updateWordList} from "@/api/config";
    import WordTable from "@/components/config/word_lists/WordTable";
    import AuthMixin from "@/services/auth/auth_mixin";
    import Permissions from "@/services/auth/permissions";

    export default {
        name: "NewWordList",
        components: {
            WordTable
        },
        data: () => ({
            visible: false,
            edit: false,
            show_validation_error: false,
            show_error: false,
            word_list: {
                id: -1,
                name: "",
                description: "",
                use_for_stop_words: false,
                categories: []
            }
        }),
        mixins: [AuthMixin],
        computed: {
            canCreate() {
                return this.checkPermission(Permissions.CONFIG_BOT_PRESET_CREATE)
            },
            canUpdate() {
                return this.checkPermission(Permissions.CONFIG_BOT_PRESET_UPDATE) || !this.edit
            },
        },
        methods: {
            addWordList() {
                this.visible = true;
                this.edit = false
                this.show_error = false;
                this.word_list.id = -1;
                this.word_list.name = "";
                this.word_list.description = "";
                this.word_list.use_for_stop_words = false
                this.word_list.categories = []
                this.$validator.reset();
            },

            addCategory() {
                this.word_list.categories.push({
                    name: "",
                    description: "",
                    entries: []
                })
            },

            deleteCategory(index) {
                this.word_list.categories.splice(index, 1)
            },

            cancel() {
                this.$validator.reset();
                this.visible = false
            },

            add() {
                this.$validator.validateAll().then(() => {

                    if (!this.$validator.errors.any()) {

                        this.show_validation_error = false;
                        this.show_error = false;

                        if (this.edit === true) {
                            updateWordList(this.word_list).then(() => {

                                this.$validator.reset();
                                this.visible = false;
                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'word_list.successful_edit'
                                    }
                                )
                            }).catch(() => {

                                this.show_error = true;
                            })
                        } else {
                            createNewWordList(this.word_list).then(() => {

                                this.$validator.reset();
                                this.visible = false;
                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'word_list.successful'
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

            update(list) {
                this.word_list.categories[list.index].entries = list.entries;
            }
        },
        mounted() {
            this.$root.$on('show-edit', (data) => {

                this.visible = true;
                this.edit = true
                this.show_error = false;

                this.word_list.id = data.id;
                this.word_list.name = data.name;
                this.word_list.use_for_stop_words = data.use_for_stop_words
                this.word_list.description = data.description;

                this.word_list.categories = []
                for (let i = 0; i < data.categories.length; i++) {
                    let category = {
                        name: data.categories[i].name,
                        description: data.categories[i].description,
                        entries: []
                    }

                    for (let j = 0; j < data.categories[i].entries.length; j++) {
                        category.entries.push({
                            value: data.categories[i].entries[j].value,
                            description: data.categories[i].entries[j].description,
                        })
                    }

                    this.word_list.categories.push(category)
                }
            });
        },
        beforeDestroy() {
            this.$root.$off('show-edit')
        }
    }
</script>
