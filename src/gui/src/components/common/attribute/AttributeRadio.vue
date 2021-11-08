<template>
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
                                v-if="!read_only && !values[index].remote"
                                :disabled="!canModify"
                                row
                                v-model="values[index].value"
                                @change="onEdit(index)"
                        >
                            <v-radio v-for="attr_enum in attribute_group.attribute.attribute_enums" :key="attr_enum.id"
                                     :label="attr_enum.value"
                                     :value="attr_enum.value"
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
        name: "AttributeRadio",
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