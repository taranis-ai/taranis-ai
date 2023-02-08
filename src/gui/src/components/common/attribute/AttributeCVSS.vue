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
                        <CalculatorCVSS
                                :value="calcValue"
                                @update-value="updateValue"
                                @success="report"
                        />
                    </template>
                    <template v-slot:col_middle>
                        <v-text-field v-model="calcValue"
                                      :label="$t('attribute.value')"
                                      @focus="onFocus(index)" @blur="onBlur(index)" @keyup="directValueChange"
                                      :class="getLockedStyle(index)"
                                      :disabled="values[index].locked || !canModify"
                                      :rules="[rules.vector]"
                        ></v-text-field>

                        <v-card class="text-center pb-3" color="white" outlined>
                            <v-row justify="center">
                                <v-col v-for="metric in score.all" :key="metric.name" class="pa-0 mr-1 severity" :class="metric.severity" style="width: calc(100% / 3); border-radius: 4px;">
                                    <span class="body-2 white--text">{{ $t('cvss_calculator.'+metric.name+'_score') + " " }}</span>
                                    <span class="body-2 white--text font-weight-bold text-uppercase">{{ $t('cvss_calculator.' + metric.severity) }}</span>
                                    <br>
                                    <span class="px-4 cs_metric_score headline font-weight-medium">{{ metric.score }}</span>
                                </v-col>
                            </v-row>
                        </v-card>
                    </template>
                </AttributeValueLayout>
            </v-row>
        </template>
    </AttributeItemLayout>

</template>

<script>
import AttributesMixin from '@/components/common/attribute/attributes_mixin'
import CalculatorCVSS from '@/components/common/CalculatorCVSS'
import Cvss31Mixin from '@/assets/cvss31_mixin'

import AttributeItemLayout from '../../layouts/AttributeItemLayout'
import AttributeValueLayout from '../../layouts/AttributeValueLayout'

export default {
  name: 'AttributeCVSS',
  props: {
    attribute_group: Object
  },
  data: () => ({
    score: 'score status',
    calcValue: '',
    status: '',
    rules: {
      vector: value => {
        const pattern = /^CVSS:3\.1\/((AV:[NALP]|AC:[LH]|PR:[UNLH]|UI:[NR]|S:[UC]|[CIA]:[NLH]|E:[XUPFH]|RL:[XOTWU]|RC:[XURC]|[CIA]R:[XLMH]|MAV:[XNALP]|MAC:[XLH]|MPR:[XUNLH]|MUI:[XNR]|MS:[XUC]|M[CIA]:[XNLH])\/)*(AV:[NALP]|AC:[LH]|PR:[UNLH]|UI:[NR]|S:[UC]|[CIA]:[NLH]|E:[XUPFH]|RL:[XOTWU]|RC:[XURC]|[CIA]R:[XLMH]|MAV:[XNALP]|MAC:[XLH]|MPR:[XUNLH]|MUI:[XNR]|MS:[XUC]|M[CIA]:[XNLH])$/
        return value === '' || pattern.test(value) || 'Invalid or Incomplete Vector String'
      }
    }
  }),
  mixins: [AttributesMixin, Cvss31Mixin],
  components: {
    CalculatorCVSS,
    AttributeItemLayout,
    AttributeValueLayout
  },
  methods: {
    updateValue (e) {
      this.calcValue = e
      this.score = this.clc.calculateCVSSFromVector(this.calcValue)
      setTimeout(() => {
        this.values[0].value = e
        this.onEdit(0)
      }, 200)
    },
    report (e) {
      this.status = e
    },
    directValueChange () {
      const vsReport = this.clc.calculateCVSSFromVector(this.calcValue)

      if (vsReport.success) {
        this.score = vsReport

        this.values[0].value = this.calcValue
        this.onKeyUp(0)
      }
    }

  },
  mounted () {
    if (this.values[0].value !== '') {
      this.calcValue = this.values[0].value
      this.score = this.clc.calculateCVSSFromVector(this.calcValue)
    } else {
      this.calcValue = 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N'
    }
  }
}
</script>
