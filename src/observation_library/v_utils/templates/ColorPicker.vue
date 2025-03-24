<template>
    <v-menu offset-y :open-on-hover="true" :close-on-content-click="false">
        <template v-slot:activator="{ on, attrs }">
            <div
                class="px-2 d-inline-flex flex-column align-self-end"
                style="min-width: 60px"
            >
                <div v-if="label" class="mb-1 caption text--secondary">
                    {{ label }}
                </div>
                <v-btn
                    icon
                    v-bind="attrs"
                    v-on="on"
                    :style="{
                        border: '2px solid black',
                        'border-radius': '50%',
                        'background-color': color,
                    }"
                >
                    <v-icon x-large>mdi-circle</v-icon>
                </v-btn>
            </div>
        </template>
        <v-color-picker v-model="color"></v-color-picker>
    </v-menu>
</template>

<script>
export default {};
</script>
