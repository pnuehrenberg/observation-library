<template>
    <video
        :class="class_"
        :style="style_"
        :loop="loop"
        :autoplay="autoplay"
        controls
        :id="id"
    >
        <source :src="url" type="video/mp4" />
    </video>
</template>

<script>
export default {
    methods: {
        reload() {
            var video = document.getElementById(this.id);
            video.load();
        },
    },
    watch: {
        url() {
            this.reload();
        },
    },
};
</script>
