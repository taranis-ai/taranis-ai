const Cvss31Mixin = {
  data: () => ({
    clc: {}
  }),
  /* data() {
        return {
            clc: {}
        }
    }, */
  mounted() {
    const CVSS31 = {}
    this.clc = CVSS31

    CVSS31.CVSSVersionIdentifier = 'CVSS:3.1'
    CVSS31.exploitabilityCoefficient = 8.22
    CVSS31.scopeCoefficient = 1.08
    CVSS31.vectorStringRegex_31 =
      /^CVSS:3\.1\/((AV:[NALP]|AC:[LH]|PR:[UNLH]|UI:[NR]|S:[UC]|[CIA]:[NLH]|E:[XUPFH]|RL:[XOTWU]|RC:[XURC]|[CIA]R:[XLMH]|MAV:[XNALP]|MAC:[XLH]|MPR:[XUNLH]|MUI:[XNR]|MS:[XUC]|M[CIA]:[XNLH])\/)*(AV:[NALP]|AC:[LH]|PR:[UNLH]|UI:[NR]|S:[UC]|[CIA]:[NLH]|E:[XUPFH]|RL:[XOTWU]|RC:[XURC]|[CIA]R:[XLMH]|MAV:[XNALP]|MAC:[XLH]|MPR:[XUNLH]|MUI:[XNR]|MS:[XUC]|M[CIA]:[XNLH])$/
    CVSS31.Weight = {
      AV: {
        N: 0.85,
        A: 0.62,
        L: 0.55,
        P: 0.2
      },
      AC: {
        H: 0.44,
        L: 0.77
      },
      PR: {
        U: {
          N: 0.85,
          L: 0.62,
          H: 0.27
        },
        C: {
          N: 0.85,
          L: 0.68,
          H: 0.5
        }
      },
      UI: {
        N: 0.85,
        R: 0.62
      },
      S: {
        U: 6.42,
        C: 7.52
      },
      CIA: {
        N: 0,
        L: 0.22,
        H: 0.56
      },
      E: {
        X: 1,
        U: 0.91,
        P: 0.94,
        F: 0.97,
        H: 1
      },
      RL: {
        X: 1,
        O: 0.95,
        T: 0.96,
        W: 0.97,
        U: 1
      },
      RC: {
        X: 1,
        U: 0.92,
        R: 0.96,
        C: 1
      },
      CIAR: {
        X: 1,
        L: 0.5,
        M: 1,
        H: 1.5
      }
    }
    CVSS31.severityRatings = [
      { name: 'none', bottom: 0, top: 0 },
      { name: 'low', bottom: 0.1, top: 3.9 },
      { name: 'medium', bottom: 4, top: 6.9 },
      { name: 'high', bottom: 7, top: 8.9 },
      { name: 'critical', bottom: 9, top: 10 }
    ]
    CVSS31.calculateCVSSFromMetrics = function (
      AttackVector,
      AttackComplexity,
      PrivilegesRequired,
      UserInteraction,
      Scope,
      Confidentiality,
      Integrity,
      Availability,
      ExploitCodeMaturity,
      RemediationLevel,
      ReportConfidence,
      ConfidentialityRequirement,
      IntegrityRequirement,
      AvailabilityRequirement,
      ModifiedAttackVector,
      ModifiedAttackComplexity,
      ModifiedPrivilegesRequired,
      ModifiedUserInteraction,
      ModifiedScope,
      ModifiedConfidentiality,
      ModifiedIntegrity,
      ModifiedAvailability
    ) {
      const badMetrics = []
      if (typeof AttackVector === 'undefined' || AttackVector === '') {
        badMetrics.push('AV')
      }
      if (typeof AttackComplexity === 'undefined' || AttackComplexity === '') {
        badMetrics.push('AC')
      }
      if (
        typeof PrivilegesRequired === 'undefined' ||
        PrivilegesRequired === ''
      ) {
        badMetrics.push('PR')
      }
      if (typeof UserInteraction === 'undefined' || UserInteraction === '') {
        badMetrics.push('UI')
      }
      if (typeof Scope === 'undefined' || Scope === '') {
        badMetrics.push('S')
      }
      if (typeof Confidentiality === 'undefined' || Confidentiality === '') {
        badMetrics.push('C')
      }
      if (typeof Integrity === 'undefined' || Integrity === '') {
        badMetrics.push('I')
      }
      if (typeof Availability === 'undefined' || Availability === '') {
        badMetrics.push('A')
      }
      if (badMetrics.length > 0) {
        return {
          success: false,
          errorType: 'MissingBaseMetric',
          errorMetrics: badMetrics
        }
      }

      const AV = AttackVector
      const AC = AttackComplexity
      const PR = PrivilegesRequired
      const UI = UserInteraction
      const S = Scope
      const C = Confidentiality
      const I = Integrity
      const A = Availability
      const E = ExploitCodeMaturity || 'X'
      const RL = RemediationLevel || 'X'
      const RC = ReportConfidence || 'X'
      const CR = ConfidentialityRequirement || 'X'
      const IR = IntegrityRequirement || 'X'
      const AR = AvailabilityRequirement || 'X'
      const MAV = ModifiedAttackVector || 'X'
      const MAC = ModifiedAttackComplexity || 'X'
      const MPR = ModifiedPrivilegesRequired || 'X'
      const MUI = ModifiedUserInteraction || 'X'
      const MS = ModifiedScope || 'X'
      const MC = ModifiedConfidentiality || 'X'
      const MI = ModifiedIntegrity || 'X'
      const MA = ModifiedAvailability || 'X'

      const remapMetrics = []
      !CVSS31.Weight.AV.hasOwnProperty(AV)
        ? badMetrics.push('AV')
        : remapMetrics.push(AV)
      !CVSS31.Weight.AC.hasOwnProperty(AC)
        ? badMetrics.push('AC')
        : remapMetrics.push(AC)
      !CVSS31.Weight.PR.U.hasOwnProperty(PR)
        ? badMetrics.push('PR')
        : remapMetrics.push(PR)
      !CVSS31.Weight.UI.hasOwnProperty(UI)
        ? badMetrics.push('UI')
        : remapMetrics.push(UI)
      !CVSS31.Weight.S.hasOwnProperty(S)
        ? badMetrics.push('S')
        : remapMetrics.push(S)
      !CVSS31.Weight.CIA.hasOwnProperty(C)
        ? badMetrics.push('C')
        : remapMetrics.push(C)
      !CVSS31.Weight.CIA.hasOwnProperty(I)
        ? badMetrics.push('I')
        : remapMetrics.push(I)
      !CVSS31.Weight.CIA.hasOwnProperty(A)
        ? badMetrics.push('A')
        : remapMetrics.push(A)

      !(E === 'X' || CVSS31.Weight.E.hasOwnProperty(E))
        ? badMetrics.push('E')
        : remapMetrics.push(E)
      !(RL === 'X' || CVSS31.Weight.RL.hasOwnProperty(RL))
        ? badMetrics.push('RL')
        : remapMetrics.push(RL)
      !(RC === 'X' || CVSS31.Weight.RC.hasOwnProperty(RC))
        ? badMetrics.push('RC')
        : remapMetrics.push(RC)

      !(CR === 'X' || CVSS31.Weight.CIAR.hasOwnProperty(CR))
        ? badMetrics.push('CR')
        : remapMetrics.push(CR)
      !(IR === 'X' || CVSS31.Weight.CIAR.hasOwnProperty(IR))
        ? badMetrics.push('IR')
        : remapMetrics.push(IR)
      !(AR === 'X' || CVSS31.Weight.CIAR.hasOwnProperty(AR))
        ? badMetrics.push('AR')
        : remapMetrics.push(AR)
      !(MAV === 'X' || CVSS31.Weight.AV.hasOwnProperty(MAV))
        ? badMetrics.push('MAV')
        : remapMetrics.push(MAV)
      !(MAC === 'X' || CVSS31.Weight.AC.hasOwnProperty(MAC))
        ? badMetrics.push('MAC')
        : remapMetrics.push(MAC)
      !(MPR === 'X' || CVSS31.Weight.PR.U.hasOwnProperty(MPR))
        ? badMetrics.push('MPR')
        : remapMetrics.push(MPR)
      !(MUI === 'X' || CVSS31.Weight.UI.hasOwnProperty(MUI))
        ? badMetrics.push('MUI')
        : remapMetrics.push(MUI)
      !(MS === 'X' || CVSS31.Weight.S.hasOwnProperty(MS))
        ? badMetrics.push('MS')
        : remapMetrics.push(MS)
      !(MC === 'X' || CVSS31.Weight.CIA.hasOwnProperty(MC))
        ? badMetrics.push('MC')
        : remapMetrics.push(MC)
      !(MI === 'X' || CVSS31.Weight.CIA.hasOwnProperty(MI))
        ? badMetrics.push('MI')
        : remapMetrics.push(MI)
      !(MA === 'X' || CVSS31.Weight.CIA.hasOwnProperty(MA))
        ? badMetrics.push('MA')
        : remapMetrics.push(MA)

      if (!CVSS31.Weight.AV.hasOwnProperty(AV)) {
        badMetrics.push('AV')
      }
      if (!CVSS31.Weight.AC.hasOwnProperty(AC)) {
        badMetrics.push('AC')
      }
      if (!CVSS31.Weight.PR.U.hasOwnProperty(PR)) {
        badMetrics.push('PR')
      }
      if (!CVSS31.Weight.UI.hasOwnProperty(UI)) {
        badMetrics.push('UI')
      }
      if (!CVSS31.Weight.S.hasOwnProperty(S)) {
        badMetrics.push('S')
      }
      if (!CVSS31.Weight.CIA.hasOwnProperty(C)) {
        badMetrics.push('C')
      }
      if (!CVSS31.Weight.CIA.hasOwnProperty(I)) {
        badMetrics.push('I')
      }
      if (!CVSS31.Weight.CIA.hasOwnProperty(A)) {
        badMetrics.push('A')
      }

      if (!CVSS31.Weight.E.hasOwnProperty(E)) {
        badMetrics.push('E')
      }
      if (!CVSS31.Weight.RL.hasOwnProperty(RL)) {
        badMetrics.push('RL')
      }
      if (!CVSS31.Weight.RC.hasOwnProperty(RC)) {
        badMetrics.push('RC')
      }

      if (!(CR === 'X' || CVSS31.Weight.CIAR.hasOwnProperty(CR))) {
        badMetrics.push('CR')
      }
      if (!(IR === 'X' || CVSS31.Weight.CIAR.hasOwnProperty(IR))) {
        badMetrics.push('IR')
      }
      if (!(AR === 'X' || CVSS31.Weight.CIAR.hasOwnProperty(AR))) {
        badMetrics.push('AR')
      }
      if (!(MAV === 'X' || CVSS31.Weight.AV.hasOwnProperty(MAV))) {
        badMetrics.push('MAV')
      }
      if (!(MAC === 'X' || CVSS31.Weight.AC.hasOwnProperty(MAC))) {
        badMetrics.push('MAC')
      }
      if (!(MPR === 'X' || CVSS31.Weight.PR.U.hasOwnProperty(MPR))) {
        badMetrics.push('MPR')
      }
      if (!(MUI === 'X' || CVSS31.Weight.UI.hasOwnProperty(MUI))) {
        badMetrics.push('MUI')
      }
      if (!(MS === 'X' || CVSS31.Weight.S.hasOwnProperty(MS))) {
        badMetrics.push('MS')
      }
      if (!(MC === 'X' || CVSS31.Weight.CIA.hasOwnProperty(MC))) {
        badMetrics.push('MC')
      }
      if (!(MI === 'X' || CVSS31.Weight.CIA.hasOwnProperty(MI))) {
        badMetrics.push('MI')
      }
      if (!(MA === 'X' || CVSS31.Weight.CIA.hasOwnProperty(MA))) {
        badMetrics.push('MA')
      }
      if (badMetrics.length > 0) {
        return {
          success: false,
          errorType: 'UnknownMetricValue',
          errorMetrics: badMetrics
        }
      }

      const metricWeightAV = CVSS31.Weight.AV[AV]
      const metricWeightAC = CVSS31.Weight.AC[AC]
      const metricWeightPR = CVSS31.Weight.PR[S][PR]
      const metricWeightUI = CVSS31.Weight.UI[UI]
      const metricWeightS = CVSS31.Weight.S[S]
      const metricWeightC = CVSS31.Weight.CIA[C]
      const metricWeightI = CVSS31.Weight.CIA[I]
      const metricWeightA = CVSS31.Weight.CIA[A]
      const metricWeightE = CVSS31.Weight.E[E]
      const metricWeightRL = CVSS31.Weight.RL[RL]
      const metricWeightRC = CVSS31.Weight.RC[RC]
      const metricWeightCR = CVSS31.Weight.CIAR[CR]
      const metricWeightIR = CVSS31.Weight.CIAR[IR]
      const metricWeightAR = CVSS31.Weight.CIAR[AR]
      const metricWeightMAV = CVSS31.Weight.AV[MAV !== 'X' ? MAV : AV]
      const metricWeightMAC = CVSS31.Weight.AC[MAC !== 'X' ? MAC : AC]
      const metricWeightMPR =
        CVSS31.Weight.PR[MS !== 'X' ? MS : S][MPR !== 'X' ? MPR : PR]
      const metricWeightMUI = CVSS31.Weight.UI[MUI !== 'X' ? MUI : UI]
      const metricWeightMS = CVSS31.Weight.S[MS !== 'X' ? MS : S]
      const metricWeightMC = CVSS31.Weight.CIA[MC !== 'X' ? MC : C]
      const metricWeightMI = CVSS31.Weight.CIA[MI !== 'X' ? MI : I]
      const metricWeightMA = CVSS31.Weight.CIA[MA !== 'X' ? MA : A]
      let baseScore
      const iss =
        1 - (1 - metricWeightC) * (1 - metricWeightI) * (1 - metricWeightA)
      const impact =
        S === 'U'
          ? metricWeightS * iss
          : metricWeightS * (iss - 0.029) - 3.25 * Math.pow(iss - 0.02, 15)

      const exploitability =
        CVSS31.exploitabilityCoefficient *
        metricWeightAV *
        metricWeightAC *
        metricWeightPR *
        metricWeightUI
      if (impact <= 0) {
        baseScore = 0
      } else if (S === 'U') {
        baseScore = CVSS31.roundUp1(Math.min(exploitability + impact, 10))
      } else {
        baseScore = CVSS31.roundUp1(
          Math.min(CVSS31.scopeCoefficient * (exploitability + impact), 10)
        )
      }

      const temporalScore = CVSS31.roundUp1(
        baseScore * metricWeightE * metricWeightRL * metricWeightRC
      )
      const miss = Math.min(
        1 -
          (1 - metricWeightMC * metricWeightCR) *
            (1 - metricWeightMI * metricWeightIR) *
            (1 - metricWeightMA * metricWeightAR),
        0.915
      )
      const modifiedImpact =
        MS === 'U' || (MS === 'X' && S === 'U')
          ? metricWeightMS * miss
          : metricWeightMS * (miss - 0.029) -
            3.25 * Math.pow(miss * 0.9731 - 0.02, 13)
      const modifiedExploitability =
        CVSS31.exploitabilityCoefficient *
        metricWeightMAV *
        metricWeightMAC *
        metricWeightMPR *
        metricWeightMUI
      let envScore

      if (modifiedImpact <= 0) {
        envScore = 0
      } else if (MS === 'U' || (MS === 'X' && S === 'U')) {
        envScore = CVSS31.roundUp1(
          CVSS31.roundUp1(
            Math.min(modifiedImpact + modifiedExploitability, 10)
          ) *
            metricWeightE *
            metricWeightRL *
            metricWeightRC
        )
      } else {
        envScore = CVSS31.roundUp1(
          CVSS31.roundUp1(
            Math.min(
              CVSS31.scopeCoefficient *
                (modifiedImpact + modifiedExploitability),
              10
            )
          ) *
            metricWeightE *
            metricWeightRL *
            metricWeightRC
        )
      }

      let vectorString = `${CVSS31.CVSSVersionIdentifier}/AV:${AV}/AC:${AC}/PR:${PR}/UI:${UI}/S:${S}/C:${C}/I:${I}/A:${A}`
      if (E !== 'X') {
        vectorString += `/E:${E}`
      }
      if (RL !== 'X') {
        vectorString += `/RL:${RL}`
      }
      if (RC !== 'X') {
        vectorString += `/RC:${RC}`
      }
      if (CR !== 'X') {
        vectorString += `/CR:${CR}`
      }
      if (IR !== 'X') {
        vectorString += `/IR:${IR}`
      }
      if (AR !== 'X') {
        vectorString += `/AR:${AR}`
      }
      if (MAV !== 'X') {
        vectorString += `/MAV:${MAV}`
      }
      if (MAC !== 'X') {
        vectorString += `/MAC:${MAC}`
      }
      if (MPR !== 'X') {
        vectorString += `/MPR:${MPR}`
      }
      if (MUI !== 'X') {
        vectorString += `/MUI:${MUI}`
      }
      if (MS !== 'X') {
        vectorString += `/MS:${MS}`
      }
      if (MC !== 'X') {
        vectorString += `/MC:${MC}`
      }
      if (MI !== 'X') {
        vectorString += `/MI:${MI}`
      }
      if (MA !== 'X') {
        vectorString += `/MA:${MA}`
      }

      return {
        success: true,
        baseMetricScore: baseScore.toFixed(1),
        baseSeverity: CVSS31.severityRating(baseScore.toFixed(1)),
        baseISS: iss,
        baseImpact: impact,
        baseExploitability: exploitability,
        temporalMetricScore: temporalScore.toFixed(1),
        temporalSeverity: CVSS31.severityRating(temporalScore.toFixed(1)),
        environmentalMetricScore: envScore.toFixed(1),
        environmentalSeverity: CVSS31.severityRating(envScore.toFixed(1)),
        environmentalMISS: miss,
        environmentalModifiedImpact: modifiedImpact,
        environmentalModifiedExploitability: modifiedExploitability,
        vectorString: vectorString,
        vectorValues: remapMetrics,
        all: {
          base: {
            name: 'base',
            score: baseScore.toFixed(1),
            severity: CVSS31.severityRating(baseScore.toFixed(1)),
            iss: iss,
            impact: impact,
            exploitability: exploitability
          },
          temporal: {
            name: 'temporal',
            score: temporalScore.toFixed(1),
            severity: CVSS31.severityRating(temporalScore.toFixed(1))
          },
          environmental: {
            name: 'environmental',
            score: envScore.toFixed(1),
            severity: CVSS31.severityRating(envScore.toFixed(1)),
            miss: miss,
            impact: modifiedImpact,
            exploitability: modifiedExploitability
          }
        }
      }
    }
    CVSS31.calculateCVSSFromVector = function (vectorString) {
      const metricValues = {
        AV: undefined,
        AC: undefined,
        PR: undefined,
        UI: undefined,
        S: undefined,
        C: undefined,
        I: undefined,
        A: undefined,
        E: undefined,
        RL: undefined,
        RC: undefined,
        CR: undefined,
        IR: undefined,
        AR: undefined,
        MAV: undefined,
        MAC: undefined,
        MPR: undefined,
        MUI: undefined,
        MS: undefined,
        MC: undefined,
        MI: undefined,
        MA: undefined
      }
      const badMetrics = []
      if (!CVSS31.vectorStringRegex_31.test(vectorString)) {
        return {
          success: false,
          errorType: 'MalformedVectorString'
        }
      }
      const metricNameValue = vectorString
        .substring(CVSS31.CVSSVersionIdentifier.length)
        .split('/')
      for (const i in metricNameValue) {
        if (metricNameValue.hasOwnProperty(i)) {
          const singleMetric = metricNameValue[i].split(':')
          if (typeof metricValues[singleMetric[0]] === 'undefined') {
            metricValues[singleMetric[0]] = singleMetric[1]
          } else {
            badMetrics.push(singleMetric[0])
          }
        }
      }

      if (badMetrics.length > 0) {
        return {
          success: false,
          errorType: 'MultipleDefinitionsOfMetric',
          errorMetrics: badMetrics
        }
      }
      return CVSS31.calculateCVSSFromMetrics(
        metricValues.AV,
        metricValues.AC,
        metricValues.PR,
        metricValues.UI,
        metricValues.S,
        metricValues.C,
        metricValues.I,
        metricValues.A,
        metricValues.E,
        metricValues.RL,
        metricValues.RC,
        metricValues.CR,
        metricValues.IR,
        metricValues.AR,
        metricValues.MAV,
        metricValues.MAC,
        metricValues.MPR,
        metricValues.MUI,
        metricValues.MS,
        metricValues.MC,
        metricValues.MI,
        metricValues.MA
      )
    }
    CVSS31.roundUp1 = function Roundup(input) {
      const int_input = Math.round(input * 100000)
      return int_input % 10000 === 0
        ? int_input / 100000
        : (Math.floor(int_input / 10000) + 1) / 10
    }
    CVSS31.severityRating = function (score) {
      const severityRatingLength = CVSS31.severityRatings.length
      const validatedScore = Number(score)
      if (isNaN(validatedScore)) {
        return validatedScore
      }
      for (let i = 0; i < severityRatingLength; i++) {
        if (
          score >= CVSS31.severityRatings[i].bottom &&
          score <= CVSS31.severityRatings[i].top
        ) {
          return CVSS31.severityRatings[i].name
        }
      }
      return undefined
    }
    CVSS31.XML_MetricNames = {
      E: {
        X: 'NOT_DEFINED',
        U: 'UNPROVEN',
        P: 'PROOF_OF_CONCEPT',
        F: 'FUNCTIONAL',
        H: 'HIGH'
      },
      RL: {
        X: 'NOT_DEFINED',
        O: 'OFFICIAL_FIX',
        T: 'TEMPORARY_FIX',
        W: 'WORKAROUND',
        U: 'UNAVAILABLE'
      },
      RC: {
        X: 'NOT_DEFINED',
        U: 'UNKNOWN',
        R: 'REASONABLE',
        C: 'CONFIRMED'
      },
      CIAR: {
        X: 'NOT_DEFINED',
        L: 'LOW',
        M: 'MEDIUM',
        H: 'HIGH'
      },
      MAV: {
        N: 'NETWORK',
        A: 'ADJACENT_NETWORK',
        L: 'LOCAL',
        P: 'PHYSICAL',
        X: 'NOT_DEFINED'
      },
      MAC: {
        H: 'HIGH',
        L: 'LOW',
        X: 'NOT_DEFINED'
      },
      MPR: {
        N: 'NONE',
        L: 'LOW',
        H: 'HIGH',
        X: 'NOT_DEFINED'
      },
      MUI: {
        N: 'NONE',
        R: 'REQUIRED',
        X: 'NOT_DEFINED'
      },
      MS: {
        U: 'UNCHANGED',
        C: 'CHANGED',
        X: 'NOT_DEFINED'
      },
      MCIA: {
        N: 'NONE',
        L: 'LOW',
        H: 'HIGH',
        X: 'NOT_DEFINED'
      }
    }
    CVSS31.generateXMLFromMetrics = function (
      AttackVector,
      AttackComplexity,
      PrivilegesRequired,
      UserInteraction,
      Scope,
      Confidentiality,
      Integrity,
      Availability,
      ExploitCodeMaturity,
      RemediationLevel,
      ReportConfidence,
      ConfidentialityRequirement,
      IntegrityRequirement,
      AvailabilityRequirement,
      ModifiedAttackVector,
      ModifiedAttackComplexity,
      ModifiedPrivilegesRequired,
      ModifiedUserInteraction,
      ModifiedScope,
      ModifiedConfidentiality,
      ModifiedIntegrity,
      ModifiedAvailability
    ) {
      const xmlTemplate =
        '<?xml version="1.0" encoding="UTF-8"?>\n<cvssv3.1 xmlns="https://www.first.org/cvss/cvss-v3.1.xsd"\n  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n  xsi:schemaLocation="https://www.first.org/cvss/cvss-v3.1.xsd https://www.first.org/cvss/cvss-v3.1.xsd"\n  >\n\n  <base_metrics>\n    <attack-vector>__AttackVector__</attack-vector>\n    <attack-complexity>__AttackComplexity__</attack-complexity>\n    <privileges-required>__PrivilegesRequired__</privileges-required>\n    <user-interaction>__UserInteraction__</user-interaction>\n    <scope>__Scope__</scope>\n    <confidentiality-impact>__Confidentiality__</confidentiality-impact>\n    <integrity-impact>__Integrity__</integrity-impact>\n    <availability-impact>__Availability__</availability-impact>\n    <base-score>__BaseScore__</base-score>\n    <base-severity>__BaseSeverityRating__</base-severity>\n  </base_metrics>\n\n  <temporal_metrics>\n    <exploit-code-maturity>__ExploitCodeMaturity__</exploit-code-maturity>\n    <remediation-level>__RemediationLevel__</remediation-level>\n    <report-confidence>__ReportConfidence__</report-confidence>\n    <temporal-score>__TemporalScore__</temporal-score>\n    <temporal-severity>__TemporalSeverityRating__</temporal-severity>\n  </temporal_metrics>\n\n  <environmental_metrics>\n    <confidentiality-requirement>__ConfidentialityRequirement__</confidentiality-requirement>\n    <integrity-requirement>__IntegrityRequirement__</integrity-requirement>\n    <availability-requirement>__AvailabilityRequirement__</availability-requirement>\n    <modified-attack-vector>__ModifiedAttackVector__</modified-attack-vector>\n    <modified-attack-complexity>__ModifiedAttackComplexity__</modified-attack-complexity>\n    <modified-privileges-required>__ModifiedPrivilegesRequired__</modified-privileges-required>\n    <modified-user-interaction>__ModifiedUserInteraction__</modified-user-interaction>\n    <modified-scope>__ModifiedScope__</modified-scope>\n    <modified-confidentiality-impact>__ModifiedConfidentiality__</modified-confidentiality-impact>\n    <modified-integrity-impact>__ModifiedIntegrity__</modified-integrity-impact>\n    <modified-availability-impact>__ModifiedAvailability__</modified-availability-impact>\n    <environmental-score>__EnvironmentalScore__</environmental-score>\n    <environmental-severity>__EnvironmentalSeverityRating__</environmental-severity>\n  </environmental_metrics>\n\n</cvssv3.1>\n'
      const result = CVSS31.calculateCVSSFromMetrics(
        AttackVector,
        AttackComplexity,
        PrivilegesRequired,
        UserInteraction,
        Scope,
        Confidentiality,
        Integrity,
        Availability,
        ExploitCodeMaturity,
        RemediationLevel,
        ReportConfidence,
        ConfidentialityRequirement,
        IntegrityRequirement,
        AvailabilityRequirement,
        ModifiedAttackVector,
        ModifiedAttackComplexity,
        ModifiedPrivilegesRequired,
        ModifiedUserInteraction,
        ModifiedScope,
        ModifiedConfidentiality,
        ModifiedIntegrity,
        ModifiedAvailability
      )
      if (result.success !== true) {
        return result
      }
      const xmlOutput = xmlTemplate
        .replace('__AttackVector__', CVSS31.XML_MetricNames.MAV[AttackVector])
        .replace(
          '__AttackComplexity__',
          CVSS31.XML_MetricNames.MAC[AttackComplexity]
        )
        .replace(
          '__PrivilegesRequired__',
          CVSS31.XML_MetricNames.MPR[PrivilegesRequired]
        )
        .replace(
          '__UserInteraction__',
          CVSS31.XML_MetricNames.MUI[UserInteraction]
        )
        .replace('__Scope__', CVSS31.XML_MetricNames.MS[Scope])
        .replace(
          '__Confidentiality__',
          CVSS31.XML_MetricNames.MCIA[Confidentiality]
        )
        .replace('__Integrity__', CVSS31.XML_MetricNames.MCIA[Integrity])
        .replace('__Availability__', CVSS31.XML_MetricNames.MCIA[Availability])
        .replace('__BaseScore__', result.baseMetricScore)
        .replace('__BaseSeverityRating__', result.baseSeverity)
        .replace(
          '__ExploitCodeMaturity__',
          CVSS31.XML_MetricNames.E[ExploitCodeMaturity || 'X']
        )
        .replace(
          '__RemediationLevel__',
          CVSS31.XML_MetricNames.RL[RemediationLevel || 'X']
        )
        .replace(
          '__ReportConfidence__',
          CVSS31.XML_MetricNames.RC[ReportConfidence || 'X']
        )
        .replace('__TemporalScore__', result.temporalMetricScore)
        .replace('__TemporalSeverityRating__', result.temporalSeverity)
        .replace(
          '__ConfidentialityRequirement__',
          CVSS31.XML_MetricNames.CIAR[ConfidentialityRequirement || 'X']
        )
        .replace(
          '__IntegrityRequirement__',
          CVSS31.XML_MetricNames.CIAR[IntegrityRequirement || 'X']
        )
        .replace(
          '__AvailabilityRequirement__',
          CVSS31.XML_MetricNames.CIAR[AvailabilityRequirement || 'X']
        )
        .replace(
          '__ModifiedAttackVector__',
          CVSS31.XML_MetricNames.MAV[ModifiedAttackVector || 'X']
        )
        .replace(
          '__ModifiedAttackComplexity__',
          CVSS31.XML_MetricNames.MAC[ModifiedAttackComplexity || 'X']
        )
        .replace(
          '__ModifiedPrivilegesRequired__',
          CVSS31.XML_MetricNames.MPR[ModifiedPrivilegesRequired || 'X']
        )
        .replace(
          '__ModifiedUserInteraction__',
          CVSS31.XML_MetricNames.MUI[ModifiedUserInteraction || 'X']
        )
        .replace(
          '__ModifiedScope__',
          CVSS31.XML_MetricNames.MS[ModifiedScope || 'X']
        )
        .replace(
          '__ModifiedConfidentiality__',
          CVSS31.XML_MetricNames.MCIA[ModifiedConfidentiality || 'X']
        )
        .replace(
          '__ModifiedIntegrity__',
          CVSS31.XML_MetricNames.MCIA[ModifiedIntegrity || 'X']
        )
        .replace(
          '__ModifiedAvailability__',
          CVSS31.XML_MetricNames.MCIA[ModifiedAvailability || 'X']
        )
        .replace('__EnvironmentalScore__', result.environmentalMetricScore)
        .replace(
          '__EnvironmentalSeverityRating__',
          result.environmentalSeverity
        )
      return {
        success: true,
        xmlString: xmlOutput
      }
    }
    CVSS31.generateXMLFromVector = function (vectorString) {
      const metricValues = {
        AV: undefined,
        AC: undefined,
        PR: undefined,
        UI: undefined,
        S: undefined,
        C: undefined,
        I: undefined,
        A: undefined,
        E: undefined,
        RL: undefined,
        RC: undefined,
        CR: undefined,
        IR: undefined,
        AR: undefined,
        MAV: undefined,
        MAC: undefined,
        MPR: undefined,
        MUI: undefined,
        MS: undefined,
        MC: undefined,
        MI: undefined,
        MA: undefined
      }
      const badMetrics = []
      if (!CVSS31.vectorStringRegex_31.test(vectorString)) {
        return {
          success: false,
          errorType: 'MalformedVectorString'
        }
      }
      const metricNameValue = vectorString
        .substring(CVSS31.CVSSVersionIdentifier.length)
        .split('/')
      for (const i in metricNameValue) {
        if (metricNameValue.hasOwnProperty(i)) {
          const singleMetric = metricNameValue[i].split(':')
          if (typeof metricValues[singleMetric[0]] === 'undefined') {
            metricValues[singleMetric[0]] = singleMetric[1]
          } else {
            badMetrics.push(singleMetric[0])
          }
        }
      }
      if (badMetrics.length > 0) {
        return {
          success: false,
          errorType: 'MultipleDefinitionsOfMetric',
          errorMetrics: badMetrics
        }
      }
      return CVSS31.generateXMLFromMetrics(
        metricValues.AV,
        metricValues.AC,
        metricValues.PR,
        metricValues.UI,
        metricValues.S,
        metricValues.C,
        metricValues.I,
        metricValues.A,
        metricValues.E,
        metricValues.RL,
        metricValues.RC,
        metricValues.CR,
        metricValues.IR,
        metricValues.AR,
        metricValues.MAV,
        metricValues.MAC,
        metricValues.MPR,
        metricValues.MUI,
        metricValues.MS,
        metricValues.MC,
        metricValues.MI,
        metricValues.MA
      )
    }
  }
}

export default Cvss31Mixin
