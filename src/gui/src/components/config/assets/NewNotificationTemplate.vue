<template>
    <v-row v-bind="UI.DIALOG.ROW.WINDOW">
        <v-btn v-bind="UI.BUTTON.ADD_NEW" @click="addTemplate">
            <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
            <span>{{$t('notification_template.add')}}</span>
        </v-btn>
        <v-dialog v-bind="UI.DIALOG.FULLSCREEN" v-model="visible">
            <v-card v-bind="UI.DIALOG.BASEMENT">
                <v-toolbar v-bind="UI.DIALOG.TOOLBAR" :style="UI.STYLE.z10000">
                    <v-btn v-bind="UI.BUTTON.CLOSE_ICON" @click="cancel">
                        <v-icon>{{ UI.ICON.CLOSE }}</v-icon>
                    </v-btn>

                    <v-toolbar-title>
                        <span v-if="!edit">{{ $t('notification_template.add_new') }}</span>
                        <span v-else>{{ $t('notification_template.edit') }}</span>
                    </v-toolbar-title>

                    <v-spacer></v-spacer>
                    <v-btn text dark type="submit" form="form">
                        <v-icon left>mdi-content-save</v-icon>
                        <span>{{$t('notification_template.save')}}</span>
                    </v-btn>
                </v-toolbar>

                <v-form @submit.prevent="add" id="form" ref="form" class="px-4">
                    <v-row no-gutters>
                        <v-col cols="12" class="pa-1">
                            <v-text-field
                                :label="$t('notification_template.name')"
                                name="name"
                                type="text"
                                v-model="template.name"
                                v-validate="'required'"
                                data-vv-name="name"
                                :error-messages="errors.collect('name')"
                                :spellcheck="$store.state.settings.spellcheck"
                            />
                        </v-col>
                        <v-col cols="12" class="pa-1">
                            <v-textarea
                                :label="$t('notification_template.description')"
                                name="description"
                                v-model="template.description"
                                :spellcheck="$store.state.settings.spellcheck"
                            />
                        </v-col>
                    </v-row>
                    <v-row no-gutters>
                        <v-col cols="12" class="pa-1">
                            <v-text-field
                                :label="$t('notification_template.message_title')"
                                name="message_title"
                                type="text"
                                v-model="template.message_title"
                                :spellcheck="$store.state.settings.spellcheck"
                            />
                        </v-col>
                        <v-col cols="12" class="pa-1">
                            <span style="font-size:16px">{{$t('notification_template.message_body')}}</span>
                            <ckeditor :editor="editor" v-model="editorData" :config="editorConfig"></ckeditor>
                        </v-col>
                    </v-row>
                    <v-row no-gutters class="pt-2">
                        <v-col cols="12" class="pa-1">
                            <RecipientTable :recipients="template.recipients" />
                        </v-col>
                    </v-row>
                    <v-row no-gutters>
                        <v-col cols="12">
                            <v-alert v-if="show_validation_error" dense type="error" text>
                                {{$t('notification_template.validation_error')}}
                            </v-alert>
                            <v-alert v-if="show_error" dense type="error" text>
                                {{$t('notification_template.error')}}
                            </v-alert>
                        </v-col>
                    </v-row>
                </v-form>
            </v-card>
        </v-dialog>
    </v-row>
</template>

<script>
    import {createNewNotificationTemplate} from "@/api/assets";
    import {updateNotificationTemplate} from "@/api/assets";
    import RecipientTable from "@/components/config/assets/RecipientTable";
    import ClassicEditor from '@ckeditor/ckeditor5-build-classic';

    export default {
        name: "NewNotificationTemplate",
        components: {
            RecipientTable
        },
        data: () => ({
            visible: false,
            edit: false,
            editor: ClassicEditor,
            editorData: '<p></p>',
            editorConfig: {
                // The configuration of the editor.
            },
            show_validation_error: false,
            show_error: false,
            template: {
                id: -1,
                name: "",
                description: "",
                message_title: "",
                message_body: "",
                recipients: []
            }
        }),
        methods: {
            addTemplate() {
                this.visible = true;
                this.edit = false
                this.show_error = false;
                this.editorData = '<p></p>'
                this.template.id = -1;
                this.template.name = "";
                this.template.description = "";
                this.template.message_title = "";
                this.template.message_body = "";
                this.template.recipients = []
                this.$validator.reset();
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
                        this.template.message_body = this.editorData;

                        if (this.edit === true) {
                            updateNotificationTemplate(this.template).then(() => {

                                this.$validator.reset();
                                this.visible = false;
                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'notification_template.successful_edit'
                                    }
                                )
                            }).catch(() => {

                                this.show_error = true;
                            })
                        } else {
                            createNewNotificationTemplate(this.template).then(() => {

                                this.$validator.reset();
                                this.visible = false;
                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'notification_template.successful'
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
            }
        },
        mounted() {
            this.$root.$on('show-edit', (data) => {

                this.visible = true;
                this.edit = true
                this.show_error = false;

                this.template.id = data.id;
                this.template.name = data.name;
                this.template.description = data.description;
                this.template.message_title = data.message_title;
                this.template.message_body = data.message_body;
                this.editorData = data.message_body;

                this.template.recipients = []
                for (let i = 0; i < data.recipients.length; i++) {
                    let recipient = {
                        email: data.recipients[i].email,
                        name: data.recipients[i].name,
                    }

                    this.template.recipients.push(recipient)
                }
            });
        },
        beforeDestroy() {
            this.$root.$off('show-edit')
        }
    }
</script>