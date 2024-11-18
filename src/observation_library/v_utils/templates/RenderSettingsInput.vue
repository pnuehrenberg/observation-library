<template>
    <v-sheet class="ma-2" style="width: 700px">
        <v-tabs vertical>
            <v-tab
                v-for="item in ['video', 'trajectories', 'categories']"
                :key="item"
            >
                {{ item }}
            </v-tab>

            <v-tab-item>
                <div
                    class="ma-2 ml-4 d-inline-flex flex-column align-self-start"
                >
                    <div class="d-inline-flex flex-row align-self-start">
                        <v-select
                            v-model="size_preset"
                            :items="size_preset_options"
                            label="Preset"
                            class="mx-2"
                            style="width: 200px"
                        ></v-select>
                        <jupyter-widget
                            :widget="max_render_width_input"
                            class="mx-2"
                            style="width: 70px"
                        />
                        <jupyter-widget
                            :widget="max_render_height_input"
                            class="mx-2"
                            style="width: 70px"
                        />
                    </div>
                    <div class="d-inline-flex flex-row align-self-start">
                        <v-switch
                            v-model="crop_roi"
                            label="Crop trajectory ROI"
                            hide-details
                            class="mx-2 pb-7"
                            style="width: 200px"
                        ></v-switch>
                        <v-fade-transition>
                            <jupyter-widget
                                v-show="crop_roi"
                                :widget="roi_padding_input"
                                class="mx-2"
                                style="width: 100px"
                            />
                        </v-fade-transition>
                    </div>
                    <jupyter-widget
                        :widget="interval_padding_input"
                        class="mx-2"
                        style="width: 200px"
                    />
                </div>
            </v-tab-item>
            <v-tab-item>
                <div
                    class="ma-2 ml-4 d-inline-flex flex-column align-self-start"
                >
                    <div class="d-inline-flex flex-row align-self-start">
                        <v-switch
                            v-model="draw_trajectories"
                            label="Draw trajectories"
                            hide-details
                            class="mx-2 pb-7"
                            style="min-width: 200px"
                        ></v-switch>
                        <v-fade-transition>
                            <v-column v-show="draw_trajectories" class="mx-2">
                                <div class="mb-n1 caption text--secondary">
                                    Apply highlight color to
                                </div>
                                <v-chip-group
                                    v-model="apply_highlight_color_to"
                                    multiple
                                    label="Apply highlight color to"
                                    active-class="primary--text"
                                >
                                    <v-chip key="actor">Actor</v-chip>
                                    <v-chip key="recipient">Recipient</v-chip>
                                </v-chip-group>
                            </v-column>
                        </v-fade-transition>
                    </div>
                    <v-expand-transition>
                        <div v-show="draw_trajectories">
                            <v-column>
                                <v-row class="mx-2">
                                    <v-select
                                        label="Keypoints"
                                        placeholder="Select keypoints"
                                        v-model="keypoints"
                                        :items="available_keypoints"
                                        multiple
                                        chips
                                        deletable-chips
                                        clearable
                                        hide-details
                                        class="mx-2 pb-4"
                                        style="width: 100%"
                                    >
                                    </v-select>
                                    <v-select
                                        label="Segments"
                                        placeholder="Select segments"
                                        v-model="segments"
                                        :items="available_segments"
                                        multiple
                                        chips
                                        deletable-chips
                                        clearable
                                        hide-details
                                        class="mx-2 pb-4"
                                        style="width: 100%"
                                    >
                                    </v-select>
                                </v-row>
                                <v-row class="mx-2 pb-7">
                                    <jupyter-widget
                                        :widget="actor_color_input"
                                        class="mx-2"
                                        style="width: 60px"
                                    />
                                    <jupyter-widget
                                        :widget="recipient_color_input"
                                        class="mx-2"
                                        style="width: 60px"
                                    />
                                    <jupyter-widget
                                        :widget="other_color_input"
                                        class="mx-2"
                                        style="width: 60px"
                                    />
                                </v-row>
                            </v-column>
                        </div>
                    </v-expand-transition>
                </div>
            </v-tab-item>
            <v-tab-item>
                <div
                    class="ma-2 ml-4 d-inline-flex flex-column align-self-start"
                >
                    <div class="my-2 d-inline-flex flex-row align-self-start">
                        <v-switch
                            v-model="draw_label"
                            label="Draw label"
                            hide-details
                            class="mx-2 pb-3"
                            style="min-width: 200px"
                        ></v-switch>
                        <v-fade-transition>
                            <jupyter-widget
                                v-show="draw_label"
                                :widget="text_color_input"
                                class="mx-2 mt-n2"
                                style="width: 60px"
                            />
                        </v-fade-transition>
                        <v-fade-transition>
                            <jupyter-widget
                                v-show="draw_label"
                                :widget="box_color_input"
                                class="mx-2 mt-n2"
                                style="width: 60px"
                            />
                        </v-fade-transition>
                    </div>
                    <div class="my-2 d-inline-flex flex-row align-self-start">
                        <v-switch
                            v-model="highlight"
                            label="Enable highlighting"
                            hide-details
                            class="mx-2 pb-3"
                            style="min-width: 200px"
                        ></v-switch>
                        <v-fade-transition>
                            <jupyter-widget
                                v-show="highlight"
                                :widget="highlight_color_input"
                                class="mx-2 mt-n2"
                                style="width: 60px"
                            />
                        </v-fade-transition>
                    </div>
                    <v-expand-transition>
                        <div v-show="highlight">
                            <div
                                class="my-2 d-inline-flex flex-row align-self-start"
                            >
                                <v-select
                                    :items="categories"
                                    v-model="selected_category"
                                    label="Override highlight color"
                                    placeholder="Select category"
                                    clearable
                                    hide-details
                                    class="mx-2"
                                    style="max-width: 200px"
                                ></v-select>
                                <v-fade-transition>
                                    <div
                                        v-show="selected_category"
                                        class="mt-2"
                                    >
                                        <jupyter-widget
                                            :widget="
                                                override_highlight_color_input
                                            "
                                            style="width: 60px"
                                        />
                                    </div>
                                </v-fade-transition>
                                <v-fade-transition>
                                    <v-btn
                                        v-show="
                                            selected_category &&
                                            overridden_highlight
                                        "
                                        icon
                                        x-small
                                        class="mt-1 ml-n5"
                                        @click="reset_override_highlight_color"
                                    >
                                        <v-icon>mdi-replay</v-icon>
                                    </v-btn>
                                </v-fade-transition>
                            </div>
                        </div>
                    </v-expand-transition>
                </div>
            </v-tab-item>
        </v-tabs>
    </v-sheet>
</template>

<script>
export default {};
</script>
