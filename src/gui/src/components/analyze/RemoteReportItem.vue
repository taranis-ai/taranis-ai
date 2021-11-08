<template>
    <v-row v-bind="UI.DIALOG.ROW.WINDOW">
        <v-dialog v-bind="UI.DIALOG.FULLSCREEN" v-model="visible" @keydown.esc="cancel" report-item>
            <v-card>

                <v-toolbar v-bind="UI.DIALOG.TOOLBAR" :style="UI.STYLE.z10000" data-dialog="report-item">
                    <v-btn icon dark @click="cancel" data-btn="cancel">
                        <v-icon>mdi-close-circle</v-icon>
                    </v-btn>
                    <v-toolbar-title>{{report_item.title}}</v-toolbar-title>
                    <v-spacer></v-spacer>
                </v-toolbar>

                <v-form @submit.prevent="add" id="form" ref="form">
                    <v-card>
                        <v-card-text>
                            <span>ID: {{report_item.uuid}}</span>
                        </v-card-text>
                    </v-card>

                    <div style="padding:16px" class="div-wrapper">
                        <v-card style="margin-bottom: 8px">

                            <v-card-title class="v-card-title-dialog">
                                {{$t('report_item.attributes')}}
                            </v-card-title>

                            <v-card-text style="padding-top:8px">
                                <RemoteAttributeContainer v-for="attribute_item in report_item.attributes"
                                                          :key="attribute_item.id"
                                                          :attribute_item="attribute_item"></RemoteAttributeContainer>
                            </v-card-text>
                        </v-card>
                    </div>

                </v-form>

            </v-card>
        </v-dialog>
    </v-row>
</template>

<script>
    import {getReportItem} from "@/api/analyze";
    import RemoteAttributeContainer from "../common/attribute/RemoteAttributeContainer";

    export default {
        name: "RemoteReportItem",
        components: {RemoteAttributeContainer},
        data: () => ({
            visible: false,
            report_item: {
                uuid: null,
                title: "",
                title_prefix: "",
                completed: false,
                attributes: []
            }
        }),
        methods: {
            cancel() {
                this.visible = false;
            },
            showDetail(report_item) {
                getReportItem(report_item.id).then((response) => {

                    let data = response.data

                    this.visible = true;

                    this.report_item.uuid = data.uuid;
                    this.report_item.title = data.title;
                    this.report_item.title_prefix = data.title_prefix;
                    this.report_item.completed = data.completed;

                    this.report_item.attributes = []
                    for (let i = 0; i < data.attributes.length; i++) {
                        let exists = false
                        for (let k = 0; k < this.report_item.attributes.length; k++) {
                            if (this.report_item.attributes[k].title === data.attributes[i].attribute_group_item_title) {
                                exists = true
                                this.report_item.attributes[k].values.push({
                                    value: data.attributes[i].value,
                                    index: this.report_item.attributes[k].values.length
                                })
                                break
                            }
                        }

                        if (exists === false) {
                            let attribute = {title: data.attributes[i].attribute_group_item_title, values: []}
                            attribute.values.push({
                                value: data.attributes[i].value,
                                index: 0
                            })
                            this.report_item.attributes.push(attribute)
                        }
                    }
                });
            }
        }
    }
</script>