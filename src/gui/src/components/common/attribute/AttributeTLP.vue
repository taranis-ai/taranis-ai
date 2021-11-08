<template>
    <!--<div>
        <v-row v-for="(value, index) in values" :key="value.index">

            <v-col>
                <span v-if="read_only || values[index].remote">{{values[index].value}}</span>
                <v-radio-group :disabled="!canModify" v-if="!read_only && !values[index].remote" row v-model="values[index].value" @change="onEdit(index)">
                    <v-radio
                            :label="$t('attribute.tlp_white')"
                            color="gray"
                            value="WHITE"
                    ></v-radio>
                    <v-radio
                            :label="$t('attribute.tlp_green')"
                            color="green"
                            value="GREEN"
                    ></v-radio>
                    <v-radio
                            :label="$t('attribute.tlp_amber')"
                            color="orange"
                            value="AMBER"
                    ></v-radio>
                    <v-radio
                            :label="$t('attribute.tlp_red')"
                            color="red"
                            value="RED"
                    ></v-radio>
                </v-radio-group>
            </v-col>

        </v-row>
    </div>-->
    <AttributeItemLayout
            :add_button="addButtonVisible"
            @add-value="add()"
            :values="values"
    >
        <template v-slot:content>
            <v-row v-for="(value, index) in values" :key="value.index"
                   class="valueHolder"
            >
                <span v-if="read_only || values[index].remote">{{values[index].value}}</span>
                <AttributeValueLayout
                        v-if="!read_only && canModify && !values[index].remote"
                        :del_button="delButtonVisible"
                        @del-value="del(index)"
                        :occurrence="attribute_group.min_occurrence"
                        :values="values"
                        :val_index="index"
                >
                    <template v-slot:col_middle>
                        <v-radio-group
                                :disabled="!canModify"
                                v-if="!read_only && !values[index].remote"
                                row
                                v-model="values[index].value"
                                @change="onEdit(index)"
                        >
                            <v-radio
                                    :label="$t('attribute.tlp_white')"
                                    color="gray"
                                    value="WHITE"
                            ></v-radio>
                            <v-radio
                                    :label="$t('attribute.tlp_green')"
                                    color="green"
                                    value="GREEN"
                            ></v-radio>
                            <v-radio
                                    :label="$t('attribute.tlp_amber')"
                                    color="orange"
                                    value="AMBER"
                            ></v-radio>
                            <v-radio
                                    :label="$t('attribute.tlp_red')"
                                    color="red"
                                    value="RED"
                            ></v-radio>
                        </v-radio-group>
                    </template>
                </AttributeValueLayout>
            </v-row>
        </template>

    </AttributeItemLayout>

</template>

<script>
    import AttributesMixin from "@/components/common/attribute/attributes_mixin";
    import AttributeItemLayout from "../../layouts/AttributeItemLayout";
    import AttributeValueLayout from "../../layouts/AttributeValueLayout";

    export default {
        name: "AttributeTLP",
        props: {
            attribute_group: Object
        },
        components: {
            AttributeItemLayout,
            AttributeValueLayout
        },
        mixins: [AttributesMixin]
    }
</script>