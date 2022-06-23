<template>
  <v-card>

    <button-outlined
      icon="$awakeClose"
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
            v-if="topicView"
            cols="12"
            sm="6"
            class="pr-5 d-flex flex-column align-start"
          >
            <!----------------------->
            <!-- Remove from Topic -->
            <!----------------------->
            <h2 class="popup-title mb-3">Remove from topic</h2>
            <p>
              This action will only remove the item from the topic. The item
              still exists and remains in the other topics.
            </p>

            <v-spacer></v-spacer>

            <button-solid
              label="remove from topic"
              icon="$awakeClose"
              @click="emitRemoveFromTopicAction()"
            />
          </v-col>

          <v-divider
            v-if="topicView"
            class="d-none d-sm-flex"
            vertical
          ></v-divider>

          <v-divider
            class="mr-3 ml-3 d-flex d-sm-none"
            style="border: 0.5px solid rgba(0, 0, 0, 0.12); border-bottom: none"
          ></v-divider>

          <v-col
            cols="12"
            :sm="topicView ? 6 : 12"
            class="pl-5 d-flex flex-column align-start"
          >
            <!----------------->
            <!-- Delete item -->
            <!----------------->
            <h2 class="popup-title mb-3">Delete item</h2>

            <p>
              This action deletes the item permanently. This also removes the
              item from other topics.
            </p>

            <p class="awake-red-color--text">
              <v-icon color="awake-red-color" class="mb-1">
                mdi-alert-octagon-outline
              </v-icon>
              This action cannot be undone.
            </p>

            <button-solid
              label="delete item"
              icon="$awakeDelete"
              color="awake-red-color"
              @click="emitDeleteAction()"
            />
          </v-col>
        </v-row>
      </v-row>
    </v-container>

    <!-- <v-divider></v-divider>

    <v-card-actions class="mt-3">
      <v-spacer></v-spacer>

      <button-outlined
        label="cancel"
        icon="$awakeClose"
        color="awake-red-color"
        @click="$emit('close')"
      />
    </v-card-actions> -->
  </v-card>
</template>

<script>
import buttonSolid from '@/components/_subcomponents/buttonSolid'
import buttonOutlined from '@/components/_subcomponents/buttonOutlined'

export default {
  name: 'PopupDeleteItem',
  components: {
    buttonSolid,
    buttonOutlined
  },
  props: {
    newsItem: {},
    topicView: Boolean
  },
  methods: {
    emitDeleteAction () {
      this.$emit('deleteItem')
      this.$emit('close')
    },
    emitRemoveFromTopicAction () {
      this.$emit('removeFromTopic')
      this.$emit('close')
    }
  }
}
</script>
