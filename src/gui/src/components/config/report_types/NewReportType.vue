<template>
    <v-row v-bind="UI.DIALOG.ROW.WINDOW">
        <v-btn v-bind="UI.BUTTON.ADD_NEW" v-if="canCreate" @click="addReportType">
            <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
            <span>{{$t('report_type.add_btn')}}</span>
        </v-btn>
        <v-dialog v-bind="UI.DIALOG.FULLSCREEN" v-model="visible" content-class="attribute-type">
            <v-card v-bind="UI.DIALOG.BASEMENT">
                <v-toolbar v-bind="UI.DIALOG.TOOLBAR" :style="UI.STYLE.z10000">
                    <v-btn v-bind="UI.BUTTON.CLOSE_ICON" @click="cancel">
                        <v-icon>{{ UI.ICON.CLOSE }}</v-icon>
                    </v-btn>

                    <v-toolbar-title>
                        <span v-if="!edit">{{ $t('report_type.add_new') }}</span>
                        <span v-else>{{ $t('report_type.edit') }}</span>
                    </v-toolbar-title>

                    <v-spacer></v-spacer>
                    <v-btn v-if="canUpdate" text dark type="submit" form="form">
                        <v-icon left>mdi-content-save</v-icon>
                        <span>{{$t('report_type.save')}}</span>
                    </v-btn>
                </v-toolbar>

                <v-form @submit.prevent="add" id="form" ref="form" class="px-4">
                    <v-row no-gutters>
                        <v-col cols="12" class="cation grey--text" v-if="edit">ID: {{report_type.id}}</v-col>
                        <v-col cols="12">
                            <v-text-field :disabled="!canUpdate"
                                          :label="$t('report_type.name')"
                                          name="name"
                                          type="text"
                                          v-model="report_type.title"
                                          v-validate="'required'"
                                          data-vv-name="name"
                                          :error-messages="errors.collect('name')"
                                          :spellcheck="$store.state.settings.spellcheck"
                            />
                        </v-col>
                        <v-col cols="12">
                            <v-textarea :disabled="!canUpdate"
                                        :label="$t('report_type.description')"
                                        name="description"
                                        v-model="report_type.description"
                                        :spellcheck="$store.state.settings.spellcheck"
                            />
                        </v-col>
                    </v-row>

                    <v-row no-gutters>
                        <v-col cols="12">
                            <v-btn v-if="canUpdate" color="primary" @click="addAttributeGroup">
                                <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
                                <span>{{$t('report_type.new_group')}}</span>
                            </v-btn>
                        </v-col>
                        <v-col cols="12">
                            <v-card style="margin-top: 8px" v-for="(group, index) in report_type.attribute_groups"
                                    :key="group.id">

                                <v-toolbar dark height="32px">
                                    <v-spacer></v-spacer>
                                    <v-toolbar-items v-if="canUpdate">

                                        <v-icon
                                            @click="moveAttributeGroupUp(index)"
                                        >
                                            mdi-arrow-up-bold
                                        </v-icon>
                                        <v-icon
                                            @click="moveAttributeGroupDown(index)"
                                        >
                                            mdi-arrow-down-bold
                                        </v-icon>

                                        <v-icon
                                            @click="deleteAttributeGroup(index)"
                                        >
                                            delete
                                        </v-icon>
                                    </v-toolbar-items>
                                </v-toolbar>

                                <v-card-text>
                                    <v-text-field :disabled="!canUpdate"
                                                  :label="$t('report_type.name')"
                                                  name="name"
                                                  type="text"
                                                  v-model="group.title"
                                                  :spellcheck="$store.state.settings.spellcheck"
                                    ></v-text-field>
                                    <v-textarea :disabled="!canUpdate"
                                                :label="$t('report_type.description')"
                                                name="description"
                                                v-model="group.description"
                                                :spellcheck="$store.state.settings.spellcheck"
                                    ></v-textarea>
                                    <v-text-field :disabled="!canUpdate"
                                                  :label="$t('report_type.section_title')"
                                                  name="section_title"
                                                  v-model="group.section_title"
                                                  :spellcheck="$store.state.settings.spellcheck"
                                    ></v-text-field>

                                    <AttributeTable :disabled="!canUpdate"
                                                    :attributes="report_type.attribute_groups[index].attribute_group_items"
                                                    :attribute_templates="attribute_templates"></AttributeTable>

                                </v-card-text>
                            </v-card>
                        </v-col>
                    </v-row>

                    <v-row no-gutters class="pt-2">
                        <v-col cols="12">
                            <v-alert v-if="show_validation_error" dense type="error" text>
                                {{$t('report_type.validation_error')}}
                            </v-alert>
                            <v-alert v-if="show_error" dense type="error" text>
                                {{$t('report_type.error')}}
                            </v-alert>
                        </v-col>
                    </v-row>
                </v-form>
            </v-card>
        </v-dialog>
    </v-row>
</template>

<script>
    import {createNewReportItemType} from "@/api/config";
    import {updateReportItemType} from "@/api/config";
    import AttributeTable from "@/components/config/report_types/AttributeTable";
    import AuthMixin from "@/services/auth/auth_mixin";
    import Permissions from "@/services/auth/permissions";

    export default {
        name: "NewReportType",
        components: {
            AttributeTable
        },
        data: () => ({
            visible: false,
            edit: false,
            show_validation_error: false,
            show_error: false,
            attribute_templates: [],
            report_type: {
                id: -1,
                title: "",
                description: "",
                attribute_groups: []
            }
        }),
        mixins: [AuthMixin],
        computed: {
            canCreate() {
                return this.checkPermission(Permissions.CONFIG_REPORT_TYPE_CREATE)
            },
            canUpdate() {
                return this.checkPermission(Permissions.CONFIG_REPORT_TYPE_UPDATE) || !this.edit
            },
        },
        methods: {
            addReportType() {
                this.visible = true;
                this.edit = false
                this.show_error = false;
                this.report_type.id = -1;
                this.report_type.title = "";
                this.report_type.description = "";
                this.report_type.categories = []
                this.report_type.attribute_groups = []
                this.$validator.reset();
            },

            addAttributeGroup() {
                this.report_type.attribute_groups.push({
                    index: this.report_type.attribute_groups.length,
                    id: -1,
                    title: "",
                    description: "",
                    section: -1,
                    section_title: "",
                    attribute_group_items: []
                });

                setTimeout( () => {
                    document.scrollingElement.querySelector(".attribute-type").scrollTo(0, 5000);
                },200);

            },

            moveAttributeGroupUp(index) {
                if (index > 0) {
                    this.report_type.attribute_groups.splice(index - 1, 0, this.report_type.attribute_groups.splice(index, 1)[0]);
                }
            },

            moveAttributeGroupDown(index) {
                if (index < this.report_type.attribute_groups.length - 1) {
                    this.report_type.attribute_groups.splice(index + 1, 0, this.report_type.attribute_groups.splice(index, 1)[0]);
                }
            },

            deleteAttributeGroup(index) {
                this.report_type.attribute_groups.splice(index, 1)
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

                        for (let x = 0; x < this.report_type.attribute_groups.length; x++) {

                            this.report_type.attribute_groups[x].index = x;

                            for (let y = 0; y < this.report_type.attribute_groups[x].attribute_group_items.length; y++) {
                                this.report_type.attribute_groups[x].attribute_group_items[y].index = y;
                            }
                        }

                        if (this.edit) {
                            updateReportItemType(this.report_type).then(() => {

                                this.$validator.reset();
                                this.visible = false;
                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'report_type.successful_edit'
                                    }
                                )
                            }).catch(() => {

                                this.show_error = true;
                            })
                        } else {
                            createNewReportItemType(this.report_type).then(() => {

                                this.$validator.reset();
                                this.visible = false;
                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'report_type.successful'
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
            this.$store.dispatch('getAllAttributes', {search: ''})
                .then(() => {
                    this.attribute_templates = this.$store.getters.getAttributes.items
                });

            this.$root.$on('show-edit', (data) => {

                this.visible = true;
                this.edit = true
                this.show_error = false;

                this.report_type.id = data.id;
                this.report_type.title = data.title;
                this.report_type.description = data.description;

                this.report_type.attribute_groups = []
                for (let i = 0; i < data.attribute_groups.length; i++) {
                    let group = {
                        index: data.attribute_groups[i].index,
                        id: data.attribute_groups[i].id,
                        title: data.attribute_groups[i].title,
                        description: data.attribute_groups[i].description,
                        section: data.attribute_groups[i].section,
                        section_title: data.attribute_groups[i].section_title,
                        attribute_group_items: []
                    }

                    for (let j = 0; j < data.attribute_groups[i].attribute_group_items.length; j++) {
                        group.attribute_group_items.push({
                            index: data.attribute_groups[i].attribute_group_items[j].description,
                            id: data.attribute_groups[i].attribute_group_items[j].id,
                            attribute_id: data.attribute_groups[i].attribute_group_items[j].attribute.id,
                            attribute_name: data.attribute_groups[i].attribute_group_items[j].attribute.name,
                            title: data.attribute_groups[i].attribute_group_items[j].title,
                            description: data.attribute_groups[i].attribute_group_items[j].description,
                            min_occurrence: data.attribute_groups[i].attribute_group_items[j].min_occurrence,
                            max_occurrence: data.attribute_groups[i].attribute_group_items[j].max_occurrence
                        })
                    }

                    this.report_type.attribute_groups.push(group)
                }
            });
        },
        beforeDestroy() {
            this.$root.$off('show-edit')
        }
    }
</script>