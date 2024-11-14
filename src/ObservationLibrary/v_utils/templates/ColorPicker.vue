<template>
    <v-menu offset-y :open-on-hover="true" :close-on-content-click="false">
        <template v-slot:activator="{ on, attrs }">
            <div>
                <div class="mb-1 caption text--secondary">{{ label }}</div>
                <v-btn
                    outlined
                    icon
                    v-bind="attrs"
                    v-on="on"
                    :color="color"
                    style="border: 2px solid black"
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
