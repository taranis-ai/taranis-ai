<!--
<template>
    <div>
        <v-btn v-if="canCreate" depressed small color="white&#45;&#45;text ma-2 mt-3 mr-5" @click="addReportType">
            <v-icon left>mdi-plus-circle-outline</v-icon>
            <span class="subtitle-2">{{$t('report_type.add_btn')}}</span>
        </v-btn>

        <v-row justify="center">
            <v-dialog v-model="visible" fullscreen hide-overlay transition="dialog-bottom-transition">
                <v-card>
                    <v-toolbar dark color="primary" style="z-index: 10000">

                        <v-btn icon dark @click="cancel">
                            <v-icon>mdi-close-circle</v-icon>
                        </v-btn>
                        <v-toolbar-title v-if="!edit">{{$t('report_type.add_new')}}</v-toolbar-title>
                        <v-toolbar-title v-if="edit">{{$t('report_type.edit')}}</v-toolbar-title>
                        <v-spacer></v-spacer>
                        <v-btn v-if="canUpdate" text dark type="submit" form="form">
                            <v-icon left>mdi-content-save</v-icon>
                            <span>{{$t('report_type.save')}}</span>
                        </v-btn>
                    </v-toolbar>

                    <v-form @submit.prevent="add" id="form" ref="form">
                        <v-card>
                            <v-card-text>

                                <span v-if="edit">ID: {{report_type.id}}</span>

                                <v-text-field :disabled="!canUpdate"
                                              :label="$t('report_type.name')"
                                              name="name"
                                              type="text"
                                              v-model="report_type.title"
                                              v-validate="'required'"
                                              data-vv-name="name"
                                              :error-messages="errors.collect('name')"
                                              :spellcheck="$store.state.settings.spellcheck"
                                ></v-text-field>
                                <v-textarea :disabled="!canUpdate"
                                            :label="$t('report_type.description')"
                                            name="description"
                                            v-model="report_type.description"
                                            :spellcheck="$store.state.settings.spellcheck"
                                ></v-textarea>

                                <v-btn v-if="canUpdate" color="primary" @click="addAttributeGroup">
                                    <v-icon left>mdi-plus</v-icon>
                                    <span>{{$t('report_type.new_group')}}</span>
                                </v-btn>

                                <v-btn @click="expand_groups">expand</v-btn>

                                <v-expansion-panels class="mt-3" v-model="expandPanelGroups" multiple>
                                    <v-expansion-panel v-for="(group, index) in report_type.attribute_groups"
                                                       :key="group.id" >
                                        <v-expansion-panel-header>
                                            <v-row>
                                                <v-icon small color="blue">mdi-group</v-icon>
                                                <span class="group-title font-weight-bold pl-2">{{group.title}}</span>
                                                <v-spacer></v-spacer>
                                                <div class="pr-6">
                                                    <v-icon class="pr-2" dense @click.native.stop="moveAttributeGroupUp(index)">
                                                        mdi-arrow-up-bold
                                                    </v-icon>
                                                    <v-icon class="pr-2" dense @click.native.stop="moveAttributeGroupDown(index)">
                                                        mdi-arrow-down-bold
                                                    </v-icon>
                                                    <v-icon class="pr-2" dense @click.native.stop="deleteAttributeGroup(index)">
                                                        delete
                                                    </v-icon>
                                                </div>

                                            </v-row>
                                        </v-expansion-panel-header>
                                        <v-expansion-panel-content>
                                            <v-card style="margin-top: 8px" >
                                                &lt;!&ndash;<v-toolbar dark height="32px">
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
                                                </v-toolbar>&ndash;&gt;

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
                                        </v-expansion-panel-content>
                                    </v-expansion-panel>
                                </v-expansion-panels>

                            </v-card-text>
                        </v-card>
                    </v-form>
                    <v-alert v-if="show_validation_error" dense type="error" text>
                        {{$t('report_type.validation_error')}}
                    </v-alert>
                    <v-alert v-if="show_error" dense type="error" text>{{$t('report_type.error')}}
                    </v-alert>
                </v-card>
            </v-dialog>
        </v-row>
    </div>

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
            expand_panel_groups: [],
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
            expandPanelGroups() {
                //this.expand_group_reset();
                return this.expand_panel_groups;
            }
        },
        methods: {
            expand_groups() {
                this.expand_panel_groups = [];
                //return this.expand_panel_groups = Array.from(Array(this.report_type.attribute_groups.length).keys());
                this.expand_panel_groups = [...Array(this.report_type.attribute_groups).keys()].map((k, i) => i)
            },
            expand_group_reset() {
                this.expand_panel_groups = [];
            },
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
                })
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

                    this.report_type.attribute_groups.push(group);
                }
            });

            setTimeout( () => {
                this.expand_panel_groups = [...Array(this.report_type.attribute_groups).keys()].map((k, i) => i);
            }, 200);

        },
        beforeDestroy() {
            this.$root.$off('show-edit')
        }
    }
</script>

<style>
    .group-title { padding-top: 3px;}
</style>-->

<template>
    <div>
        <v-btn v-if="canCreate" depressed small color="white--text ma-2 mt-3 mr-5" @click="addReportType">
            <v-icon left>mdi-plus-circle-outline</v-icon>
            <span class="subtitle-2">{{$t('report_type.add_btn')}}</span>
        </v-btn>

        <v-row justify="center">
            <v-dialog v-model="visible" fullscreen hide-overlay transition="dialog-bottom-transition" content-class="attribute-type">
                <v-card>
                    <v-toolbar dark color="primary" style="z-index: 10000">

                        <v-btn icon dark @click="cancel">
                            <v-icon>mdi-close-circle</v-icon>
                        </v-btn>
                        <v-toolbar-title v-if="!edit">{{$t('report_type.add_new')}}</v-toolbar-title>
                        <v-toolbar-title v-if="edit">{{$t('report_type.edit')}}</v-toolbar-title>
                        <v-spacer></v-spacer>
                        <v-btn v-if="canUpdate" text dark type="submit" form="form">
                            <v-icon left>mdi-content-save</v-icon>
                            <span>{{$t('report_type.save')}}</span>
                        </v-btn>
                    </v-toolbar>

                    <v-form @submit.prevent="add" id="form" ref="form">
                        <v-card>
                            <v-card-text>

                                <span v-if="edit">ID: {{report_type.id}}</span>

                                <v-text-field :disabled="!canUpdate"
                                              :label="$t('report_type.name')"
                                              name="name"
                                              type="text"
                                              v-model="report_type.title"
                                              v-validate="'required'"
                                              data-vv-name="name"
                                              :error-messages="errors.collect('name')"
                                              :spellcheck="$store.state.settings.spellcheck"
                                ></v-text-field>
                                <v-textarea :disabled="!canUpdate"
                                            :label="$t('report_type.description')"
                                            name="description"
                                            v-model="report_type.description"
                                            :spellcheck="$store.state.settings.spellcheck"
                                ></v-textarea>

                                <v-btn v-if="canUpdate" color="primary" @click="addAttributeGroup">
                                    <v-icon left>mdi-plus</v-icon>
                                    <span>{{$t('report_type.new_group')}}</span>
                                </v-btn>

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

                            </v-card-text>
                        </v-card>
                    </v-form>
                    <v-alert v-if="show_validation_error" dense type="error" text>
                        {{$t('report_type.validation_error')}}
                    </v-alert>
                    <v-alert v-if="show_error" dense type="error" text>{{$t('report_type.error')}}
                    </v-alert>
                </v-card>
            </v-dialog>
        </v-row>
    </div>

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
