<template>
    <v-progress-linear :value="value" :class="class_" :style="style_" rounded>
        <template v-slot:default="{ value }">
            <div class="pa-2 text-h6">{{ label }}</div>
            {{ value.toFixed(0) }} % <v-spacer></v-spacer>
        </template>
    </v-progress-linear>
</template>

<script>
export default {};
</script>
