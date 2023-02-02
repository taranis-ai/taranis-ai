/* Copyright (c) 2015, Chandan B.N.
 *
 * Copyright (c) 2015, FIRST.ORG, INC
 *
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without modification, are permitted provided that the
 * following conditions are met:
 * 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following
 *    disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the
 *    following disclaimer in the documentation and/or other materials provided with the distribution.
 * 3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote
 *    products derived from this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
 * INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
 * WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

export var CVSS = function (id, options) {
  this.options = options
  this.wId = id
  var e = function (tag) {
    return document.createElement(tag)
  }

  // Base Group
  this.bg = {
    AV: 'Attack Vector',
    AC: 'Attack Complexity',
    PR: 'Privileges Required',
    UI: 'User Interaction',
    S: 'Scope',
    C: 'Confidentiality',
    I: 'Integrity',
    A: 'Availability'
  }

  // Base Metrics
  this.bm = {
    AV: {
      N: {
        l: 'Network',
        d: "<b>Worst:</b> A vulnerability exploitable with network access means the vulnerable authorization scope is bound to the network stack and the attacker's path to the vulnerable system is at the network layer. Such a vulnerability is often termed 'remotely exploitable'."
      },
      A: {
        l: 'Adjacent',
        d: "<b>Worse:</b> A vulnerability exploitable with adjacent network access means the vulnerable authorization scope is bound to the network stack and the attacker's path to the vulnerable system is at the data link layer. Examples include local IP subnet, Bluetooth, IEEE 802.11, and local Ethernet segment."
      },
      L: {
        l: 'Local',
        d: "<b>Bad:</b> A vulnerability exploitable with local access means the vulnerable authorization scope is not bound to the network stack and the attacker's path to the vulnerable authorization scope is via read / write / execute capabilities. If the attacker has the necessary Privileges Required to interact with the vulnerable authorization scope, they may be logged in locally; otherwise, they may deliver an exploit to a user and rely on User Interaction"
      },
      P: {
        l: 'Physical',
        d: '<b>Bad:</b> A vulnerability exploitable with physical access requires the ability to physically touch or manipulate a vulnerable authorization scope. Physical interaction may be brief (evil maid attack) or persistent.'
      }
    },
    AC: {
      L: {
        l: 'Low',
        d: '<b>Worst:</b> Specialized access conditions or extenuating circumstances do not exist. An attacker can expect repeatable exploit success against a vulnerable target.'
      },
      H: {
        l: 'High',
        d: "<b>Bad:</b> A successful attack depends on conditions outside the attacker's control. That is, a successful attack cannot be accomplished at-will, but requires the attacker to invest in some measurable amount of effort in preparation or execution against a specific target before successful attack can be expected. A successful attack depends on attackers overcoming one OR both of the following conditions: the attacker must gather target-specific reconnaissance; or the attacker must prepare the target environment to improve exploit reliability."
      }
    },
    PR: {
      N: {
        l: 'None',
        d: '<b>Worst:</b> The attacker is unprivileged or unauthenticated.'
      },
      L: {
        l: 'Low',
        d: '<b>Worse</b> The attacker is authenticated with privileges that provide basic, low-impact capabilities. With these starting privileges an attacker is able to cause a Partial impact to one or more of: Confidentiality, Integrity, or Availability. Alternatively, an attacker with Low privileges may have the ability to cause an impact only to non-sensitive resources.'
      },
      H: {
        l: 'High',
        d: '<b>Bad:</b> The attacker is authenticated with privileges that provide significant control over component resources. With these starting privileges an attacker can cause a Complete impact to one or more of: Confidentiality, Integrity, or Availability. Alternatively, an attacker with High privileges may have the ability to cause a Partial impact to sensitive resources.'
      }
    },
    UI: {
      N: {
        l: 'None',
        d: '<b>Worst:</b> The vulnerable system can be exploited without any interaction from any user.'
      },
      R: {
        l: 'Required',
        d: '<b>Bad:</b> Successful exploitation of this vulnerability requires a user to take one or more actions that may or may not be expected in a scenario involving no exploitation, or a scenario involving content provided by a seemingly trustworthy source.'
      }
    },

    S: {
      C: {
        l: 'Changed',
        d: '<b>Worst:</b> The attacker attacks the vulnerable authorization scope and has an impact to its environment. This causes a direct impact to another scope. Score Impact relative to the Changed Scope.'
      },
      U: {
        l: 'Unchanged',
        d: '<b>Bad:</b> The attacker attacks and impacts the environment that authorizes actions taken by the vulnerable authorization scope. Score Impact relative to the original authorization authority.'
      }
    },
    C: {
      H: {
        l: 'High',
        d: "<b>Worst:</b> There is total information disclosure, resulting in all resources in the affected scope being divulged to the attacker. Alternatively, access to only some restricted information is obtained, but the disclosed information presents a direct, serious impact to the affected scope (e.g. the attacker can read the administrator's password, or private keys in memory are disclosed to the attacker)."
      },
      L: {
        l: 'Low',
        d: '<b>Bad:</b> There is informational disclosure or a bypass of access controls. Access to some restricted information is obtained, but the attacker does not have control over what is obtained, or the scope of the loss is constrained. The information disclosure does not have a direct, serious impact on the affected scope.'
      },
      N: {
        l: 'None',
        d: '<b>Good:</b> There is no impact to confidentiality within the affected scope.'
      }
    },
    I: {
      H: {
        l: 'High',
        d: '<b>Worst:</b> There is a total compromise of system integrity. There is a complete loss of system protection, resulting in the entire system being compromised. The attacker is able to modify any files on the target system.'
      },
      L: {
        l: 'Low',
        d: '<b>Bad:</b> Modification of data is possible, but the attacker does not have control over the end result of a modification, or the scope of modification is constrained. The data modification does not have a direct, serious impact on the affected scope.'
      },
      N: {
        l: 'None',
        d: '<b>Good:</b> There is no impact to integrity within the affected scope.'
      }
    },
    A: {
      H: {
        l: 'High',
        d: '<b>Worst:</b> There is total loss of availability, resulting in the attacker being able to fully deny access to resources in the affected scope; this loss is either sustained (while the attacker continues to deliver the attack) or persistent (the condition persists even after the attack has completed). Alternatively, the attacker has the ability to deny some availability, but the loss of availability presents a direct, serious impact to the affected scope (e.g. the attacker cannot disrupt existing connections, but can prevent new connections; the attacker can repeatedly exploit a vulnerability that, in each instance of a successful attack, leaks a only small amount of memory, but after repeated exploitation causes a service to become completely unavailable).'
      },
      L: {
        l: 'Low',
        d: '<b>Bad:</b> There is reduced performance or interruptions in resource availability. The attacker does not have the ability to completely deny service to legitimate users, even through repeated exploitation of the vulnerability. The resources in the affected scope are either partially available all of the time, or fully available only some of the time, but the overall there is no direct, serious impact to the affected scope.'
      },
      N: {
        l: 'None',
        d: '<b>Good:</b> There is no impact to availability within the affected scope.'
      }
    }
  }

  this.bme = {}
  this.bmgReg = {
    AV: 'NALP',
    AC: 'LH',
    PR: 'NLH',
    UI: 'NR',
    S: 'CU',
    C: 'HLN',
    I: 'HLN',
    A: 'HLN'
  }
  this.bmoReg = {
    AV: 'NALP',
    AC: 'LH',
    C: 'C',
    I: 'C',
    A: 'C'
  }
  var s, f, dl, g, dd, l
  this.el = document.getElementById(id)
  this.el.appendChild((s = e('style')))
  s.innerHTML = ''
  this.el.appendChild((f = e('form')))
  f.className = 'cvssjs'
  this.calc = f
  for (g in this.bg) {
    f.appendChild((dl = e('dl')))
    dl.setAttribute('class', g)
    var dt = e('dt')
    dt.innerHTML = this.bg[g]
    dl.appendChild(dt)
    for (s in this.bm[g]) {
      dd = e('dd')
      dl.appendChild(dd)
      var inp = e('input')
      inp.setAttribute('name', g)
      inp.setAttribute('value', s)
      inp.setAttribute('id', id + g + s)
      inp.setAttribute('class', g + s)
      inp.setAttribute('type', 'radio')
      this.bme[g + s] = inp
      var me = this
      inp.onchange = function () {
        me.setMetric(this)
      }
      dd.appendChild(inp)
      l = e('label')
      dd.appendChild(l)
      l.setAttribute('for', id + g + s)
      l.appendChild(e('i')).setAttribute('class', g + s)
      l.appendChild(document.createTextNode(this.bm[g][s].l + ' '))
      dd.appendChild(e('small')).innerHTML = this.bm[g][s].d
    }
  }
  f.appendChild(e('hr'))
  f.appendChild((dl = e('dl')))
  dl.innerHTML = '<dt>Severity&sdot;Score&sdot;Vector</dt>'
  dd = e('dd')
  dl.appendChild(dd)
  l = dd.appendChild(e('label'))
  l.className = 'results'
  l.appendChild((this.severity = e('span')))
  this.severity.className = 'severity'
  l.appendChild((this.score = e('span')))
  this.score.className = 'score'
  l.appendChild(document.createTextNode(' '))
  l.appendChild((this.vector = e('a')))
  this.vector.className = 'vector'
  this.vector.innerHTML = 'CVSS:3.0/AV:_/AC:_/PR:_/UI:_/S:_/C:_/I:_/A:_'

  if (options.onsubmit) {
    f.appendChild(e('hr'))
    this.submitButton = f.appendChild(e('input'))
    this.submitButton.setAttribute('type', 'submit')
    this.submitButton.onclick = options.onsubmit
  }
}

CVSS.prototype.severityRatings = [
  {
    name: 'None',
    bottom: 0.0,
    top: 0.0
  },
  {
    name: 'Low',
    bottom: 0.1,
    top: 3.9
  },
  {
    name: 'Medium',
    bottom: 4.0,
    top: 6.9
  },
  {
    name: 'High',
    bottom: 7.0,
    top: 8.9
  },
  {
    name: 'Critical',
    bottom: 9.0,
    top: 10.0
  }
]

CVSS.prototype.severityRating = function (score) {
  var i
  var severityRatingLength = this.severityRatings.length
  for (i = 0; i < severityRatingLength; i++) {
    if (
      score >= this.severityRatings[i].bottom &&
      score <= this.severityRatings[i].top
    ) {
      return this.severityRatings[i]
    }
  }
  return {
    name: '?',
    bottom: 'Not',
    top: 'defined'
  }
}

CVSS.prototype.calculate = function () {
  var exploitabilityCoefficient = 8.22
  var scopeCoefficient = 1.08

  var Weight = {
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
    C: {
      N: 0,
      L: 0.22,
      H: 0.56
    },
    I: {
      N: 0,
      L: 0.22,
      H: 0.56
    },
    A: {
      N: 0,
      L: 0.22,
      H: 0.56
    }
  }

  var p
  var val = {}
  var metricWeight = {}
  try {
    for (p in this.bg) {
      val[p] = this.calc.elements[p].value
      if (typeof val[p] === 'undefined' || val[p] === '') {
        return '?'
      }
      metricWeight[p] = Weight[p][val[p]]
    }
  } catch (err) {
    return err
  }
  metricWeight.PR = Weight.PR[val.S][val.PR]
  try {
    var baseScore
    var impactSubScore
    var exploitabalitySubScore =
      exploitabilityCoefficient *
      metricWeight.AV *
      metricWeight.AC *
      metricWeight.PR *
      metricWeight.UI
    var impactSubScoreMultiplier =
      1 -
      (1 - metricWeight.C) *
        (1 - metricWeight.I) *
        (1 - metricWeight.A)
    if (val.S === 'U') {
      impactSubScore = metricWeight.S * impactSubScoreMultiplier
    } else {
      impactSubScore =
        metricWeight.S * (impactSubScoreMultiplier - 0.029) -
        3.25 * Math.pow(impactSubScoreMultiplier - 0.02, 15)
    }

    if (impactSubScore <= 0) {
      baseScore = 0
    } else {
      if (val.S === 'U') {
        baseScore = Math.min(exploitabalitySubScore + impactSubScore, 10)
      } else {
        baseScore = Math.min(
          (exploitabalitySubScore + impactSubScore) * scopeCoefficient,
          10
        )
      }
    }

    baseScore = Math.ceil(baseScore * 10) / 10
    return baseScore
  } catch (err) {
    return err
  }
}

CVSS.prototype.get = function () {
  return {
    score: this.score.innerHTML,
    vector: this.vector.innerHTML
  }
}

CVSS.prototype.setMetric = function (a) {
  var vectorString = this.vector.innerHTML
  if (!/AV:.\/AC:.\/PR:.\/UI:.\/S:.\/C:.\/I:.\/A:./.test(vectorString)) {
    vectorString = 'AV:_/AC:_/PR:_/UI:_/S:_/C:_/I:_/A:_'
  }
  var newVec = vectorString.replace(
    new RegExp('\\b' + a.name + ':.'),
    a.name + ':' + a.value
  )
  this.set(newVec)
}

CVSS.prototype.set = function (vec) {
  var newVec = 'CVSS:3.0/'
  var sep = ''
  var match
  var check
  var m
  for (m in this.bm) {
    if (
      (match = new RegExp('\\b(' + m + ':[' + this.bmgReg[m] + '])').exec(
        vec
      )) != null
    ) {
      check = match[0].replace(':', '')
      this.bme[check].checked = true
      newVec = newVec + sep + match[0]
    } else if (
      m in { C: '', I: '', A: '' } &&
      (match = new RegExp('\\b(' + m + ':C)').exec(vec)) != null
    ) {
      // compatibility with v2 only for CIA:C
      this.bme[m + 'H'].checked = true
      newVec = newVec + sep + m + ':H'
    } else {
      newVec = newVec + sep + m + ':_'
      for (var j in this.bm[m]) {
        this.bme[m + j].checked = false
      }
    }
    sep = '/'
  }
  this.update(newVec)
}

CVSS.prototype.update = function (newVec) {
  this.vector.innerHTML = newVec
  var s = this.calculate()
  this.score.innerHTML = s
  var rating = this.severityRating(s)
  this.severity.className = rating.name + ' severity'
  this.severity.innerHTML =
    rating.name + '<sub>' + rating.bottom + ' - ' + rating.top + '</sub>'
  this.severity.title = rating.bottom + ' - ' + rating.top
  if (this.options !== undefined && this.options.onchange !== undefined) {
    this.options.onchange()
  }
}
