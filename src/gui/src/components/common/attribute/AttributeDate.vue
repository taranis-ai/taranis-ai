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
                        <!--<v-icon right>mdi-calendar</v-icon>-->
                        <!--<v-icon right>mdi-account-lock</v-icon>-->
                    </template>
                    <template v-slot:col_middle>
                        <date-picker
                                v-if="!read_only && !values[index].remote"
                                v-model="values[index].value"
                                type="date"
                                format="YYYY.MM.DD"
                                value-type="format"
                                @focus="onFocus(index)"
                                @change="onEdit(index)"
                                @clear="clear(index)"
                                :class="getLockedStyle(index)"
                                :disabled="values[index].locked || !canModify"
                        >
                            <template v-slot:icon-calendar>
                                <v-icon class="pb-5">mdi-calendar</v-icon>
                            </template>
                            <template v-slot:icon-clear>
                                <v-icon small class="pb-5 pr-1">mdi-close</v-icon>
                            </template>
                            <template v-slot:input>
                                <v-text-field
                                        v-if="!read_only && !values[index].remote"
                                        :placeholder="$t('attribute.select_date')"
                                        dense
                                        v-model="values[index].value"
                                        @focus="onFocus(index)"
                                        @blur="onBlur(index)"
                                        :class="getLockedStyle(index)"
                                        :disabled="values[index].locked || !canModify"
                                ></v-text-field>
                            </template>
                        </date-picker>
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

    import DatePicker from 'vue2-datepicker';
    import 'vue2-datepicker/index.css';

    export default {
        name: "AttributeDate",
        props: {
            attribute_group: Object
        },
        components: {
            AttributeItemLayout,
            AttributeValueLayout,
            DatePicker
        },
        methods: {
            clear(index) {
                this.values[index].value = '';
                this.onEdit(index);
            }
        },
        mixins: [AttributesMixin]
    }
</script>