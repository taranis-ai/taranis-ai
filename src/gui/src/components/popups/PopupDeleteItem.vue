<template>
  <v-card>

    <button-outlined
      icon="mdi-close"
      color="awake-red-color"
      extraClass="corner-close"
      @click="$emit('close')"
    />

    <v-container>
      <v-row>
        <v-col cols="12">
          <strong class="pt-3">Item:</strong>
          <h2 class="font-weight-regular dark-grey--text text-capitalize pt-0">
            "{{ newsItem.title }}"
          </h2>
        </v-col>
      </v-row>

      <v-row class="pb-4">
        <v-row class="mt-4 mb-0">
          <v-col
            cols="12"
            sm="12"
            class="pl-5 d-flex flex-column align-start"
          >
            <!----------------->
            <!-- Delete item -->
            <!----------------->
            <h2 class="popup-title mb-3">Delete item</h2>

            <p>
              This action deletes the item permanently.
            </p>

            <p class="awake-red-color--text">
              <v-icon color="awake-red-color" class="mb-1">
                mdi-alert-octagon-outline
              </v-icon>
              This action cannot be undone.
            </p>

            <button-outlined
              label="delete item"
              icon="mdi-delete"
              color="awake-red-color"
              @click="emitDeleteAction()"
            />
          </v-col>
        </v-row>
      </v-row>
    </v-container>

  </v-card>
</template>

<script>
import buttonOutlined from '@/components/_subcomponents/buttonOutlined'

export default {
  name: 'PopupDeleteItem',
  components: {
    buttonOutlined
  },
  props: {
    newsItem: {}
  },
  methods: {
    emitDeleteAction () {
      this.$emit('deleteItem')
      this.$emit('close')
    }
  }
}
</script>
