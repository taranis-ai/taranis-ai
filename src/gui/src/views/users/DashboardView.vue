<template>
  <ViewLayout>
    <template v-slot:content>
      <DashboardContent />
    </template>
  </ViewLayout>
</template>

<script>
import ViewLayout from '@/components/layouts/ViewLayout'
import DashboardContent from '@/components/dashboard/DashboardContent'

export default {
  name: 'DashboardView',
  components: {
    ViewLayout,
    DashboardContent
  }
}
</script>
