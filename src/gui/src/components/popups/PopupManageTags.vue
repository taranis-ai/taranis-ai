<template>
  <v-card>
    <v-container>
      <v-row>
        <v-col cols="12">
          <h2 class="font-weight-regular dark-grey--text text-capitalize pt-0">
            Manage Tags
          </h2>
        </v-col>
      </v-row>
    </v-container>
  </v-card>
</template>

<script>
import buttonSolid from '@/components/_subcomponents/buttonSolid'
import buttonOutlined from '@/components/_subcomponents/buttonOutlined'

export default {
  name: 'PopupManageTags',
  components: {
    buttonSolid,
    buttonOutlined
  },
  props: {
    newsItem: {}
  },
  methods: {}
}
</script>
