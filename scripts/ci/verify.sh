#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Tout ce qu'un relecteur doit lancer, puis un tableau récapitulatif. Chaque job tourne même si un autre échoue.
#   make verify               api, front, audit (+ stack si Docker répond)
#   SKIP="audit stack" make verify
cd "$(dirname "$0")/../.."
mkdir -p .verify
declare -A res dur
jobs=(api front audit stack)
for j in "${jobs[@]}"; do
  if [[ " ${SKIP:-} " == *" $j "* ]]; then res[$j]="sauté (SKIP)"; dur[$j]="—"; continue; fi
  if [ "$j" = stack ] && ! docker info >/dev/null 2>&1; then res[$j]="non lancé : Docker ne répond pas"; dur[$j]="—"; continue; fi
  t0=$(date +%s)
  if bash "scripts/ci/$j.sh" > ".verify/$j.log" 2>&1; then res[$j]="OK"; else res[$j]="ÉCHEC (voir .verify/$j.log)"; fi
  dur[$j]="$(( $(date +%s) - t0 )) s"
done
summary() {  # une ligne utile tirée du journal de chaque job
  case $1 in
    api) grep -E "passed|failed" ".verify/api.log" | tail -1; grep -E "^TOTAL" ".verify/api.log" | awk '{print "couverture " $NF}' ;;
    front) grep -E "Tests +[0-9]" ".verify/front.log" | tr -s ' ' | paste -sd ';' ;;
    audit) grep -iE "No known vulnerabilities|vulnerabilit" ".verify/audit.log" | tail -2 | paste -sd ';' ;;
    stack) grep -E "Démarrage à froid|passed|failed" ".verify/stack.log" | paste -sd ';' ;;
  esac 2>/dev/null
}
echo
echo "| Job | Résultat | Durée | Détail |"
echo "|---|---|---|---|"
fail=0
for j in "${jobs[@]}"; do
  echo "| $j | ${res[$j]} | ${dur[$j]} | $( [ -f ".verify/$j.log" ] && summary "$j" | tr '\n' ' ') |"
  [[ ${res[$j]} == ÉCHEC* ]] && fail=1
done
exit $fail
