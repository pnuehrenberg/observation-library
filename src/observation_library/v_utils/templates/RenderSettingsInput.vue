<template>
    <v-sheet class="ma-2" style="width: 600px">
        <v-tabs vertical>
            <v-tab
                v-for="item in ['video', 'trajectories', 'categories']"
                class="mr-2"
                :key="item"
            >
                {{ item }}
            </v-tab>

            <v-tab-item class="pa-2 pb-3">
                <v-column>
                    <v-row class="mx-2">
                        <v-select
                            v-model="size_preset"
                            :items="size_preset_options"
                            label="Preset"
                            class="px-2"
                            style="max-width: 200px"
                        ></v-select>
                        <jupyter-widget
                            :widget="max_render_width_input"
                            class="px-2"
                            style="max-width: 100px"
                        />
                        <jupyter-widget
                            :widget="max_render_height_input"
                            class="px-2"
                            style="max-width: 100px"
                        />
                    </v-row>
                    <v-row class="mx-2">
                        <v-switch
                            v-model="crop_roi"
                            label="Crop trajectory ROI"
                            hide-details
                            class="px-2 pb-7"
                            style="width: 200px"
                        ></v-switch>
                        <v-fade-transition>
                            <jupyter-widget
                                v-show="crop_roi"
                                :widget="roi_padding_input"
                                class="px-2"
                                style="max-width: 200px"
                            />
                        </v-fade-transition>
                    </v-row>
                    <v-row class="mx-2">
                        <jupyter-widget
                            :widget="interval_padding_input"
                            class="px-2"
                            style="max-width: 200px"
                        />
                    </v-row>
                </v-column>
            </v-tab-item>
            <v-tab-item class="pa-2 pb-3">
                <v-column>
                    <v-row class="mx-2">
                        <v-switch
                            v-model="draw_trajectories"
                            label="Draw trajectories"
                            hide-details
                            class="px-2 pt-3 pb-7"
                            style="width: 200px"
                        ></v-switch>
                        <v-fade-transition>
                            <v-column
                                v-show="draw_trajectories"
                                class="px-2"
                                style="max-width: 200px"
                            >
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
                    </v-row>
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
                                        class="px-2 pb-2"
                                        style="max-width: 400px"
                                    >
                                    </v-select>
                                </v-row>
                                <v-row class="mx-2">
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
                                        class="px-2 pb-2"
                                        style="max-width: 400px"
                                    >
                                    </v-select>
                                </v-row>
                                <v-row class="mx-2">
                                    <jupyter-widget
                                        :widget="overlay_size_input"
                                        class="px-2 mt-3 mb-n6"
                                        style="max-width: 200px"
                                    />
                                    <jupyter-widget
                                        :widget="actor_color_input"
                                    />
                                    <jupyter-widget
                                        :widget="recipient_color_input"
                                    />
                                    <jupyter-widget
                                        :widget="other_color_input"
                                    />
                                </v-row>
                            </v-column>
                        </div>
                    </v-expand-transition>
                </v-column>
            </v-tab-item>
            <v-tab-item class="pa-2 pb-3">
                <v-column>
                    <v-row class="mx-2">
                        <v-switch
                            v-model="draw_label"
                            label="Draw label"
                            hide-details
                            class="px-2 mt-6 pb-4"
                            style="width: 200px"
                        ></v-switch>
                        <v-fade-transition>
                            <div v-show="draw_label">
                                <jupyter-widget
                                    v-show="draw_label"
                                    :widget="text_color_input"
                                />
                                <jupyter-widget
                                    v-show="draw_label"
                                    :widget="box_color_input"
                                />
                            </div>
                        </v-fade-transition>
                    </v-row>
                    <v-row class="mx-2">
                        <v-switch
                            v-model="highlight"
                            label="Enable highlighting"
                            hide-details
                            class="px-2 mt-6 pb-4"
                            style="width: 200px"
                        ></v-switch>
                        <v-fade-transition>
                            <div v-show="highlight">
                                <jupyter-widget
                                    :widget="highlight_color_input"
                                />
                            </div>
                        </v-fade-transition>
                    </v-row>
                    <v-expand-transition>
                        <div v-show="highlight">
                            <v-row class="mx-2 mt-2">
                                <v-select
                                    :items="categories"
                                    v-model="selected_category"
                                    label="Override highlight color"
                                    placeholder="Select category"
                                    clearable
                                    hide-details
                                    class="px-2"
                                    style="max-width: 200px"
                                ></v-select>
                                <v-fade-transition>
                                    <v-row
                                        v-show="selected_category"
                                        class="mt-3 mx-0"
                                    >
                                        <jupyter-widget
                                            :widget="
                                                override_highlight_color_input
                                            "
                                        />
                                        <v-fade-transition>
                                            <div
                                                v-show="
                                                    selected_category &&
                                                    overridden_highlight
                                                "
                                            >
                                                <v-btn
                                                    class="ml-n4"
                                                    icon
                                                    x-small
                                                    @click="
                                                        reset_override_highlight_color
                                                    "
                                                >
                                                    <v-icon>mdi-replay</v-icon>
                                                </v-btn>
                                            </div>
                                        </v-fade-transition>
                                    </v-row>
                                </v-fade-transition>
                            </v-row>
                        </div>
                    </v-expand-transition>
                </v-column>
            </v-tab-item>
        </v-tabs>
    </v-sheet>
</template>

<script>
export default {};
</script>
