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

                    <template v-slot:col_left>
                        <EnumSelector :attribute_id="attribute_group.attribute.id" :value_index="value.index" @enum-selected="enumSelected"/>
                    </template>
                    <template v-slot:col_middle>
                        <v-text-field v-model="values[index].value" dense
                                      :label="$t('attribute.value')"
                                      @focus="onFocus(index)" @blur="onBlur(index)" @keyup="onKeyUp(index)"
                                      :class="getLockedStyle(index)"
                                      :disabled="values[index].locked || !canModify"
                                      @fo="firstOne(index)"
                        >
                        </v-text-field>
                    </template>
                </AttributeValueLayout>

            </v-row>
        </template>

    </AttributeItemLayout>
</template>

<script>
    import AttributesMixin from "@/components/common/attribute/attributes_mixin";
    import EnumSelector from "@/components/common/EnumSelector";

    import AttributeItemLayout from "../../layouts/AttributeItemLayout";
    import AttributeValueLayout from "../../layouts/AttributeValueLayout";

    export default {
        name: "AttributeCVE",
        props: {
            attribute_group: Object
        },
        data: () => ({
            tooltip: ''
        }),
        mixins: [AttributesMixin],
        components: {
            EnumSelector,
            AttributeItemLayout,
            AttributeValueLayout
        },
        computed: {
            hideTooltip() {
                return !this.values === '' ? "hide-tooltip" : "";
            }
        },
        methods: {
            firstOne(index) {
                if(this.values[index].value === '') {
                    this.tooltip = "hide-tooltip"
                } else {
                    this.tooltip = '';
                }
            }
        }
    }
</script>