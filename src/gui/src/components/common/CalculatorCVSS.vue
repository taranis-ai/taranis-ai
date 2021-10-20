<template>
    <div>
        <v-btn text small @click.prevent="show" :title="$t('report_item.tooltip.cvss_detail')">
            <v-icon>mdi-calculator</v-icon>
        </v-btn>
        <v-row justify="center">
            <v-dialog v-model="visible" fullscreen hide-overlay transition="dialog-bottom-transition">
                <v-card class="ma-0 pa-0 pb-8" >
                    <v-toolbar dark color="primary">
                        <v-btn icon dark @click="cancel">
                            <v-icon>mdi-close-circle</v-icon>
                        </v-btn>
                        <v-toolbar-title>{{$t('cvss_calculator.title')}}</v-toolbar-title>
                        <v-spacer></v-spacer>
                        <v-switch v-model="tooltip" label="Tooltip" class="mt-5"></v-switch>
                    </v-toolbar>

                    <!-- Score -->
                    <v-sheet class="text-center vector-string" color="primary darken-2 white--text">
                        <span class="caption font-weight-bold" >{{ calc.vectorString }}</span>
                        <v-sheet class="text-center score-sheet" color="white">
                            <v-row justify="center" class="score-sheet">
                                <v-col v-for="metric in calc.all" :key="metric.name" class="cs_cvss_score pa-0 my-1 severity" :class="metric.severity">
                                    <span class="body-2 white--text">{{ $t('cvss_calculator.'+metric.name+'_score') + " " }}</span>
                                    <span class="body-2 white--text font-weight-bold text-uppercase">{{ $t('cvss_calculator.' + metric.severity) }}</span>
                                    <br>
                                    <span class="px-4 cs_metric_score headline font-weight-medium">{{ metric.score }}</span>
                                </v-col>
                            </v-row>
                        </v-sheet>
                    </v-sheet>

                    <!-- Base -->
                    <v-card class="bsm px-4 pb-2 pt-0 base-metric" :class="calc.baseSeverity">
                        <v-row class="pa-0 ma-0">
                            <v-card-title class="ma-0 pa-0 text-uppercase">
                                {{$t('cvss_calculator.base_score')}}
                                <v-tooltip v-if="tooltip" right max-width="500">
                                    <template v-slot:activator="{on}">
                                        <v-icon v-on="on" x-small right>mdi-information-outline</v-icon>
                                    </template>
                                    <span>{{ $t('cvss_calculator_tooltip.baseMetricGroup_Legend') }}</span>
                                </v-tooltip>
                            </v-card-title>
                        </v-row>
                        <v-card class="my-2">
                            <v-row v-for="group in cvss.base" :key="group.model">
                                <v-card flat @click="update" :ripple="false">
                                    <v-card-text class="py-2">
                                        <v-row>
                                            <span class="blue--text">{{ $t('cvss_calculator.' + group.title) }} </span>
                                            <v-tooltip v-if="tooltip" right max-width="500">
                                                <template v-slot:activator="{on}">
                                                    <v-icon v-on="on" x-small right>mdi-information-outline</v-icon>
                                                </template>
                                                <span>{{ $t('cvss_calculator_tooltip.' + group.model + '_Heading') }}</span>
                                            </v-tooltip>
                                        </v-row>
                                        <v-row >
                                            <v-btn-toggle v-model="group.state" mandatory>
                                                <v-tooltip right max-width="300" v-for="prop in group.props" :key="prop.value" :content-class="hideTooltip">
                                                    <template v-slot:activator="{on}" >
                                                        <v-btn small v-on="on">
                                                            <span>{{ $t('cvss_calculator.' + prop.label) }}</span>
                                                            <v-icon small color="primary">{{ 'mdi-alpha-' + prop.value.toLowerCase() + '-box' }}</v-icon>
                                                        </v-btn>
                                                    </template>
                                                    <span v-if="tooltip">{{ $t('cvss_calculator_tooltip.' + group.model + '_' + prop.value + '_Label') }}</span>
                                                </v-tooltip>
                                            </v-btn-toggle>
                                        </v-row>
                                    </v-card-text>
                                </v-card>
                            </v-row>
                        </v-card>
                    </v-card>

                    <!-- Temporal -->
                    <v-card class="bsm ma-4 px-4 pb-2 pt-0" :class="calc.temporalSeverity">
                        <v-row class="pa-0 ma-0">
                            <v-card-title class="ma-0 pa-0 text-uppercase">
                                {{$t('cvss_calculator.temporal_score')}}
                                <v-tooltip v-if="tooltip" right max-width="500">
                                    <template v-slot:activator="{on}">
                                        <v-icon v-on="on" x-small right>mdi-information-outline</v-icon>
                                    </template>
                                    <span>{{ $t('cvss_calculator_tooltip.temporalMetricGroup_Legend') }}</span>
                                </v-tooltip>
                            </v-card-title>
                        </v-row>
                        <v-card class="my-2">
                            <v-row v-for="group in cvss.temporal" :key="group.model">
                                <v-card flat @click="update" :ripple="false">
                                    <v-card-text class="py-2">
                                        <v-row>
                                            <span class="blue--text">{{ $t('cvss_calculator.' + group.title) }}</span>
                                            <v-tooltip v-if="tooltip" right max-width="500">
                                                <template v-slot:activator="{on}">
                                                    <v-icon v-on="on" x-small right>mdi-information-outline</v-icon>
                                                </template>
                                                <span>{{ $t('cvss_calculator_tooltip.' + group.model + '_Heading') }}</span>
                                            </v-tooltip>
                                        </v-row>
                                        <v-row >
                                            <v-btn-toggle v-model="group.state" mandatory>
                                                <v-tooltip right max-width="300" v-for="prop in group.props" :key="prop.value" :content-class="hideTooltip">
                                                    <template v-slot:activator="{on}">
                                                        <v-btn small  v-on="on">
                                                            <span>{{ $t('cvss_calculator.' + prop.label) }}</span>
                                                            <v-icon small color="primary">{{ 'mdi-alpha-' + prop.value.toLowerCase() + '-box' }}</v-icon>
                                                        </v-btn>
                                                    </template>
                                                    <span>{{ $t('cvss_calculator_tooltip.' + group.model + '_' + prop.value + '_Label') }}</span>
                                                </v-tooltip>
                                            </v-btn-toggle>
                                        </v-row>
                                    </v-card-text>
                                </v-card>
                            </v-row>
                        </v-card>
                    </v-card>

                    <!-- Environmental -->
                    <v-card class="bsm ma-4 px-4 pb-2 pt-0" :class="calc.environmentalSeverity">
                        <v-row class="pa-0 ma-0">
                            <v-card-title class="ma-0 pa-0 text-uppercase">
                                {{$t('cvss_calculator.environmental_score')}}
                                <v-tooltip v-if="tooltip" right max-width="500">
                                    <template v-slot:activator="{on}">
                                        <v-icon v-on="on" x-small right>mdi-information-outline</v-icon>
                                    </template>
                                    <span>{{ $t('cvss_calculator_tooltip.environmentalMetricGroup_Legend') }}</span>
                                </v-tooltip>
                            </v-card-title>
                        </v-row>
                        <v-card class="my-2">
                            <v-row v-for="group in cvss.environmental" :key="group.model">
                                <v-card flat @click="update" :ripple="false">
                                    <v-card-text class="py-2">
                                        <v-row>
                                            <span class="blue--text">{{ $t('cvss_calculator.' + group.title) }}</span>
                                            <v-tooltip v-if="tooltip" right max-width="500">
                                                <template v-slot:activator="{on}">
                                                    <v-icon v-on="on" x-small right>mdi-information-outline</v-icon>
                                                </template>
                                                <span>{{ $t('cvss_calculator_tooltip.' + group.model + '_Heading') }}</span>
                                            </v-tooltip>
                                        </v-row>
                                        <v-row >
                                            <v-btn-toggle v-model="group.state" mandatory>
                                                <v-tooltip right max-width="300" v-for="prop in group.props" :key="prop.value" :content-class="hideTooltip">
                                                    <template v-slot:activator="{on}">
                                                        <v-btn small  v-on="on">
                                                            <span>{{ $t('cvss_calculator.' + prop.label) }}</span>
                                                            <v-icon small color="primary">{{ 'mdi-alpha-' + prop.value.toLowerCase() + '-box' }}</v-icon>
                                                        </v-btn>
                                                    </template>
                                                    <span>{{ $t('cvss_calculator_tooltip.' + group.model + '_' + prop.value + '_Label') }}</span>
                                                </v-tooltip>
                                            </v-btn-toggle>
                                        </v-row>
                                    </v-card-text>
                                </v-card>
                            </v-row>
                        </v-card>
                    </v-card>

                </v-card>
            </v-dialog>
        </v-row>
    </div>
</template>

<script>
    import Cvss31Mixin from '@/assets/cvss31_mixin';

    export default {
        name: "CalculatorCVSS",
        props: {
            value: String
        },
        data: () => ({
            visible: false,
            tooltip: false,
            decode_string: "",
            switches: "...",
            cvss: {
                base: {
                    av:{'state':0, 'model':'AV','title':'attack_vector',
                        'props':[
                            {'value':'N','label':'network'},
                            {'value':'A','label':'adjacent'},
                            {'value':'L','label':'local'},
                            {'value':'P','label':'physical'}
                        ]
                    },
                    ac:{'state':0, 'model':'AC','title':'attack_complexity',
                        'props':[
                            {'value':'L','label':'low'},
                            {'value':'H','label':'high'}
                        ]
                    },
                    pr:{'state':0, 'model':'PR', 'title':'privileges_required',
                        'props':[
                            {'value':'N','label':'none'},
                            {'value':'L','label':'low'},
                            {'value':'H','label':'high'},
                        ]
                    },
                    ui:{'state':0, 'model':'UI', 'title':'user_interaction',
                        'props':[
                            {'value':'N','label':'none'},
                            {'value':'R','label':'required'}
                        ]
                    },
                    s:{'state':0, 'model':'S', 'title':'scope',
                        'props':[
                            {'value':'U','label':'unchanged'},
                            {'value':'C','label':'changed'}
                        ]
                    },
                    c:{'state':0, 'model':'C', 'title':'confidentiality',
                        'props':[
                            {'value':'N', 'label':'none'},
                            {'value':'L', 'label':'low'},
                            {'value':'H', 'label':'high'}
                        ]
                    },
                    i:{'state':0, 'model':'I', 'title':'integrity',
                        'props':[
                            {'value':'N', 'label':'none'},
                            {'value':'L', 'label':'low'},
                            {'value':'H', 'label':'high'}
                        ]
                    },
                    a:{'state':0, 'model':'A', 'title':'availability',
                        'props':[
                            {'value':'N', 'label':'none'},
                            {'value':'L', 'label':'low'},
                            {'value':'H', 'label':'high'}
                        ]
                    }
                },
                temporal: {
                    e:{'state':0, 'model':'E', 'title':'exploitability_code_maturity',
                        'props':[
                            {'value':'X', 'label':'not_defined'},
                            {'value':'U', 'label':'unproven'},
                            {'value':'P', 'label':'proof_of_concept'},
                            {'value':'F', 'label':'functional'},
                            {'value':'H', 'label':'high'}
                        ]
                    },
                    rl:{'state':0, 'model':'RL', 'title':'remediation_level',
                        'props':[
                            {'value':'X', 'label':'not_defined'},
                            {'value':'O', 'label':'official_fix'},
                            {'value':'T', 'label':'temporary_fix'},
                            {'value':'W', 'label':'workaround'},
                            {'value':'U', 'label':'unavailable'}
                        ]
                    },
                    rc:{'state':0, 'model':'RC', 'title':'report_confidence',
                        'props':[
                            {'value':'X', 'label':'not_defined','tooltip':''},
                            {'value':'U', 'label':'unknown','tooltip':''},
                            {'value':'R', 'label':'reasonable','tooltip':''},
                            {'value':'C', 'label':'confirmed','tooltip':''}
                        ]
                    }
                },
                environmental: {
                    cr:{'state':0, 'model':'CR', 'title':'confidentiality_requirement',
                        'props':[
                            {'value':'X', 'label':'not_defined'},
                            {'value':'L', 'label':'low'},
                            {'value':'M', 'label':'medium'},
                            {'value':'H', 'label':'high'}
                        ]
                    },
                    ir:{'state':0, 'model':'IR', 'title':'integrity_requirement',
                        'props':[
                            {'value':'X', 'label':'not_defined'},
                            {'value':'L', 'label':'low'},
                            {'value':'M', 'label':'medium'},
                            {'value':'H', 'label':'high'}
                        ]
                    },
                    ar:{'state':0, 'model':'AR', 'title':'availability_requirement',
                        'props':[
                            {'value':'X', 'label':'not_defined'},
                            {'value':'L', 'label':'low'},
                            {'value':'M', 'label':'medium'},
                            {'value':'H', 'label':'high'}
                        ]
                    },
                    mav:{'state':0, 'model':'MAV', 'title':'modified_attack_vector',
                        'props':[
                            {'value':'X', 'label':'not_defined'},
                            {'value':'N', 'label':'network'},
                            {'value':'A', 'label':'adjacent_network'},
                            {'value':'L', 'label':'local'},
                            {'value':'P', 'label':'physical'}
                        ]
                    },
                    mac:{'state':0, 'model':'MAC', 'title':'modified_attack_complexity',
                        'props':[
                            {'value':'X', 'label':'not_defined'},
                            {'value':'L', 'label':'low'},
                            {'value':'H', 'label':'high'}
                        ]
                    },
                    mpr:{'state':0, 'model':'MPR', 'title':'modified_privileges_required',
                        'props':[
                            {'value':'X', 'label':'not_defined'},
                            {'value':'N', 'label':'none'},
                            {'value':'L', 'label':'low'},
                            {'value':'H', 'label':'high'}
                        ]
                    },
                    mui:{'state':0, 'model':'MUI', 'title':'modified_user_interaction',
                        'props':[
                            {'value':'X', 'label':'not_defined'},
                            {'value':'N', 'label':'none'},
                            {'value':'R', 'label':'required'}
                        ]
                    },
                    ms:{'state':0, 'model':'MS', 'title':'modified_scope',
                        'props':[
                            {'value':'X', 'label':'not_defined'},
                            {'value':'U', 'label':'unchanged'},
                            {'value':'C', 'label':'changed'}
                        ]
                    },
                    mc:{'state':0, 'model':'MC', 'title':'modified_confidentiality',
                        'props':[
                            {'value':'X', 'label':'not_defined'},
                            {'value':'N', 'label':'none'},
                            {'value':'L', 'label':'low'},
                            {'value':'H', 'label':'high'}
                        ]
                    },
                    mi:{'state':0, 'model':'MI', 'title':'modified_integrity',
                        'props':[
                            {'value':'X', 'label':'not_defined'},
                            {'value':'N', 'label':'none'},
                            {'value':'L', 'label':'low'},
                            {'value':'H', 'label':'high'}
                        ]
                    },
                    ma:{'state':0, 'model':'MA', 'title':'modified_availability',
                        'props':[
                            {'value':'X', 'label':'not_defined'},
                            {'value':'N', 'label':'none'},
                            {'value':'L', 'label':'low'},
                            {'value':'H', 'label':'high'}
                        ]
                    }
                }
            },
            vector_string: "",
            calc: {}
        }),
        mixins: [Cvss31Mixin],
        computed: {
            baseString2: function() {
                let group = Object.values(this.cvss);
                let vector = [];
                let states = [];

                vector.push('CVSS:3.1');

                for( let i=0; i<group.length; i++ ) {
                    let keys = Object.values(group[i]);

                    for( let j=0; j<keys.length; j++ ) {
                        let state = keys[j].state;

                        if( keys[j].props[state].value !== 'X') {
                            vector.push('/' + keys[j].model + ':' + keys[j].props[state].value);
                        }
                        states.push(keys[j].props[state].value);
                    }
                }

                return this.clc.calculateCVSSFromVector(vector.join(''));
            },

            hideTooltip() {
                return !this.tooltip ? "hide-tooltip" : "";
            }
        },
        mounted() {

        },
        methods: {
            show() {
                let status = this.clc.calculateCVSSFromVector(this.value).success;

                if( status || this.value === '') {

                    if(this.value !== '') {
                        this.remapButton();
                    }

                    this.update();
                    this.visible = true;
                    this.$emit('success', status );
                } else {
                    this.$emit('success', status );
                }

            },
            cancel() {
                this.$emit('update-value', this.calc.vectorString);
                this.visible = false;
            },
            update() {
                let group = Object.values(this.cvss);
                let vector = [];
                let states = [];

                vector.push('CVSS:3.1');
                for( let i=0; i<group.length; i++ ) {
                    let keys = Object.values(group[i]);

                    for( let j=0; j<keys.length; j++ ) {
                        let state = keys[j].state;

                        if( keys[j].props[state].value !== 'X') {
                            vector.push('/' + keys[j].model + ':' + keys[j].props[state].value);
                        }
                        //states.push(keys[j].props[state].value);
                        states.push(keys[j].state);
                    }
                }
                this.calc = this.clc.calculateCVSSFromVector(vector.join(''));
            },

            remapButton(){
                let values = this.clc.calculateCVSSFromVector(this.value).vectorValues;
                let group = Object.values(this.cvss);
                let count = 0;

                for( let i=0; i<group.length; i++ ) {
                    let keys = Object.values(group[i]);

                    for( let j=0; j<keys.length; j++) {
                        keys[j].state = this.readInputVector(Object.values(keys[j].props), values[count++]);
                    }
                }
            },

            readInputVector(props, value) {
                for( let i=0; i<props.length; i++) {
                    if( props[i].value === value ) {
                        return i;
                    }
                }
            },

        }
    }
</script>

<style>
    .v-tooltip__content.hide-tooltip {
        display: none !important;
    }
    .v-card.bsm {
        border-left: 4px solid #ddd;
        transition: border-left-color 250ms;
    }
    .score-sheet {
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        border-radius: 0;
    }
    .base-metric {
        margin: 16px;
        margin-top: 112px !important;
    }

    .vector-string {
        position: fixed;
        top: 55px;
        z-index: 1;
        width: calc(100%);
        border-radius: 0;
        padding-top: 8px;
    }

    .severity { transition: background-color 250ms, color 250ms; font-weight: bold;}

    .severity.none { background-color: #53aa33 !important; }
    .severity.low { background-color: #ffcb0d !important; }
    .severity.medium { background-color: #f9a009 !important; }
    .severity.high { background-color: #df3d03 !important; }
    .severity.critical { background-color: red !important; }

    .bsm.none { border-left-color: #53aa33 !important; }
    .bsm.low { border-left-color: #ffcb0d !important; }
    .bsm.medium { border-left-color: #f9a009 !important; }
    .bsm.high { border-left-color: #df3d03 !important; }
    .bsm.critical { border-left-color: red !important; }

    span.cs_metric_score {
        background-color: rgba(255,255,255,1) !important;
        border-radius: 4px;
    }

    .cs_cvss_score {
        width: calc(100% / 3.2);
    }
    .cs_cvss_score:first-child {
        margin-left: 0px;
        margin-right: 4px;
    }
    .cs_cvss_score:last-child {
        margin-left: 4px;
        margin-right: 0px;
    }
</style>