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
                <AttributeValueLayout
                        v-if="!read_only && canModify && !values[index].remote"
                        :del_button="delButtonVisible"
                        @del-value="del(index)"
                        :occurrence="attribute_group.min_occurrence"
                        :values="values"
                        :val_index="index"
                >

                    <span v-if="read_only || values[index].remote">{{values[index].value}}</span>
                    <template v-slot:col_middle>
                        <v-combobox v-if="!read_only && !values[index].remote"
                                    v-model="values[index].value" dense
                                    :items="stringEnums"
                                    :label="$t('attribute.value')"
                                    @focus="onFocus(index)" @blur="onBlur(index)"
                                    :class="getLockedStyle(index)"
                                    :disabled="values[index].locked || !canModify"
                        />
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
        name: "AttributeEnum",
        props: {
            attribute_group: Object
        },
        components: {
            AttributeItemLayout,
            AttributeValueLayout
        },
        data: () => ({
            stringEnums: []
        }),
        mixins: [AttributesMixin],
        mounted() {
            for (let i = 0; i < this.attribute_group.attribute.attribute_enums.length; i++) {
                this.stringEnums.push(this.attribute_group.attribute.attribute_enums[i].value)
            }
        }
    }
</script>