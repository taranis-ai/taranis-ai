<template>
  <v-container fluid class="ma-5 mt-5 pa-5 pt-0">
    <v-form id="form" ref="form" validate-on="submit" @submit.prevent="add">
      <v-row no-gutters>
        <v-col cols="12">
          <v-text-field v-model="report_type.id" label="ID" :disabled="true" />
        </v-col>
        <v-col cols="12">
          <v-text-field
            v-model="report_type.title"
            :label="$t('report_type.name')"
            name="name"
          />
        </v-col>
        <v-col cols="12">
          <v-textarea
            v-model="report_type.description"
            :label="$t('report_type.description')"
            name="description"
          />
        </v-col>
      </v-row>

      <v-row no-gutters>
        <v-col cols="12">
          <v-btn
            color="primary"
            prepend-icon="mdi-plus"
            @click="addAttributeGroup"
          >
            <span>{{ $t('report_type.new_group') }}</span>
          </v-btn>
        </v-col>
        <v-col cols="12">
          <v-card
            v-for="(group, index) in report_type.attribute_groups"
            :key="group.id"
            style="margin-top: 8px"
          >
            <v-toolbar dark height="32px">
              <v-spacer></v-spacer>
              <v-toolbar-items>
                <v-icon @click="moveAttributeGroupUp(index)">
                  mdi-arrow-up-bold
                </v-icon>
                <v-icon @click="moveAttributeGroupDown(index)">
                  mdi-arrow-down-bold
                </v-icon>

                <v-icon @click="deleteAttributeGroup(index)"> delete </v-icon>
              </v-toolbar-items>
            </v-toolbar>

            <v-card-text>
              <v-text-field
                v-model="group.title"
                :label="$t('report_type.name')"
                type="text"
              ></v-text-field>
              <v-textarea
                v-model="group.description"
                :label="$t('report_type.description')"
              ></v-textarea>
              <AttributeTable
                :attributes="
                  report_type.attribute_groups[index].attribute_group_items
                "
                :attribute-templates="attributes"
                @update="(items) => updateAttributeGroupItems(index, items)"
              />
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
      <v-btn block type="submit" color="success" class="mt-3"> Submit </v-btn>
    </v-form>
  </v-container>
</template>

<script>
import { ref } from 'vue'
import { createReportItemType, updateReportItemType } from '@/api/config'
import AttributeTable from './AttributeTable.vue'
import { notifySuccess, notifyFailure } from '@/utils/helpers'

export default {
  name: 'ReportTypeForm',
  components: {
    AttributeTable
  },
  props: {
    reportTypeData: {
      type: Object || null,
      required: false,
      default: null
    },
    edit: {
      type: Boolean,
      required: false,
      default: false
    },
    attributes: {
      type: Array,
      required: false,
      default: () => []
    }
  },
  emits: ['updated'],
  setup(props, { emit }) {
    const report_type = ref(props.reportTypeData)

    const updateAttributeGroupItems = (index, items) => {
      report_type.value.attribute_groups[index].attribute_group_items = items
    }

    const addAttributeGroup = () => {
      report_type.value.attribute_groups.unshift({
        index: 0,
        title: '',
        description: '',
        attribute_group_items: []
      })
    }

    const moveAttributeGroupUp = (index) => {
      if (index > 0) {
        report_type.value.attribute_groups.splice(
          index - 1,
          0,
          report_type.value.attribute_groups.splice(index, 1)[0]
        )
      }
    }

    const moveAttributeGroupDown = (index) => {
      if (index < report_type.value.attribute_groups.length - 1) {
        report_type.value.attribute_groups.splice(
          index + 1,
          0,
          report_type.value.attribute_groups.splice(index, 1)[0]
        )
      }
    }

    const deleteAttributeGroup = (index) => {
      report_type.value.attribute_groups.splice(index, 1)
    }

    const add = () => {
      // make a deep copy of the report_type object
      const update_report_type = JSON.parse(JSON.stringify(report_type.value))
      for (let x = 0; x < update_report_type.attribute_groups.length; x++) {
        update_report_type.attribute_groups[x].index = x

        for (
          let y = 0;
          y <
          update_report_type.attribute_groups[x].attribute_group_items.length;
          y++
        ) {
          update_report_type.attribute_groups[x].attribute_group_items[
            y
          ].index = y
          delete update_report_type.attribute_groups[x].attribute_group_items[y]
            .attribute
        }
      }

      if (props.edit) {
        updateReportItemType(update_report_type)
          .then(() => {
            notifySuccess('report_type.successful_edit')
            emit('updated')
          })
          .catch(() => {
            notifyFailure('report_type.error')
          })
      } else {
        createReportItemType(update_report_type)
          .then(() => {
            notifySuccess('report_type.successful')
            emit('updated')
          })
          .catch(() => {
            notifyFailure('report_type.error')
          })
      }
    }

    return {
      report_type,
      updateAttributeGroupItems,
      addAttributeGroup,
      moveAttributeGroupUp,
      moveAttributeGroupDown,
      deleteAttributeGroup,
      add
    }
  },
  watch: {
    reportTypeData(r) {
      this.report_type = r
    }
  }
}
</script>
