#!/usr/bin/env bash
set -euo pipefail

readonly REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
readonly SKILLS_ROOT="${REPO_ROOT}/skills"
readonly INSTALL_ROOT="${AGENTS_SKILLS_HOME:-${HOME}/.agents/skills}"
readonly CODEX_ROOT="${CODEX_HOME:-${HOME}/.codex}"
readonly -a OWNED_SKILLS=(
  "coding-workflow"
  "initialize-repository-context"
  "summarize-codex-week"
  "structure-technical-documents"
)

usage() {
  printf 'Usage: %s {check|install|status}\n' "${0##*/}"
}

resolve_directory() {
  local path="$1"
  (cd -P -- "${path}" 2>/dev/null && pwd -P)
}

link_target_directory() {
  local link="$1"
  local raw_target

  raw_target="$(readlink "${link}")" || return 1
  if [[ "${raw_target}" == /* ]]; then
    resolve_directory "${raw_target}"
  else
    resolve_directory "$(dirname "${link}")/${raw_target}"
  fi
}

link_matches_source() {
  local link="$1"
  local source="$2"
  local link_target
  local source_target

  link_target="$(link_target_directory "${link}")" || return 1
  source_target="$(resolve_directory "${source}")" || return 1
  [[ "${link_target}" == "${source_target}" ]]
}

source_is_valid() {
  local name="$1"
  local source="${SKILLS_ROOT}/${name}"

  if [[ ! -f "${source}/SKILL.md" ]]; then
    printf 'ERROR  %-37s missing %s\n' "${name}" "${source}/SKILL.md" >&2
    return 1
  fi
}

link_state() {
  local name="$1"
  local source="${SKILLS_ROOT}/${name}"
  local target="${INSTALL_ROOT}/${name}"

  if [[ -L "${target}" ]]; then
    if link_matches_source "${target}" "${source}"; then
      printf 'LINKED %-37s %s\n' "${name}" "${target}"
      return 0
    fi
    printf 'CONFLICT %-35s %s points elsewhere\n' "${name}" "${target}" >&2
    return 1
  fi

  if [[ -e "${target}" ]]; then
    printf 'CONFLICT %-35s %s already exists\n' "${name}" "${target}" >&2
    return 1
  fi

  printf 'MISSING %-36s %s\n' "${name}" "${target}"
}

plugin_cache_status() {
  local name="$1"
  local cache_root="$2"
  local found=0
  local path
  local version

  for path in "${cache_root}"/*; do
    if [[ -d "${path}" ]]; then
      version="${path##*/}"
      printf 'FOUND  %-37s %s\n' "${name}@${version}" "${path}"
      found=1
    fi
  done

  if (( found == 0 )); then
    printf 'ABSENT %-37s managed separately\n' "${name}"
  fi
}

third_party_status() {
  plugin_cache_status \
    "superpowers" \
    "${CODEX_ROOT}/plugins/cache/openai-curated-remote/superpowers"
  plugin_cache_status \
    "plugin-management" \
    "${CODEX_ROOT}/plugins/cache/openai-curated-remote/plugin-management"
}

check_repository() {
  local failed=0
  local name

  for name in "${OWNED_SKILLS[@]}"; do
    source_is_valid "${name}" || failed=1
    link_state "${name}" || failed=1
  done

  third_party_status
  return "${failed}"
}

prune_stale_owned_links() {
  local target
  local raw_target
  local skill_name

  [[ -d "${INSTALL_ROOT}" ]] || return 0

  while IFS= read -r -d '' target; do
    raw_target="$(readlink "${target}")" || continue
    [[ "${raw_target}" == "${SKILLS_ROOT}/"* ]] || continue

    skill_name="${raw_target#${SKILLS_ROOT}/}"
    [[ "${skill_name}" != */* ]] || continue
    [[ -f "${SKILLS_ROOT}/${skill_name}/SKILL.md" ]] && continue

    unlink -- "${target}"
    printf 'REMOVE %-36s %s\n' "${skill_name}" "${target}"
  done < <(find -P "${INSTALL_ROOT}" -mindepth 1 -maxdepth 1 -type l -print0)
}

install_owned_skills() {
  local name
  local source
  local target

  prune_stale_owned_links

  for name in "${OWNED_SKILLS[@]}"; do
    source_is_valid "${name}"
    source="${SKILLS_ROOT}/${name}"
    target="${INSTALL_ROOT}/${name}"

    if [[ -L "${target}" ]]; then
      if link_matches_source "${target}" "${source}"; then
        continue
      fi
      printf 'ERROR  %-37s refusing to overwrite %s\n' "${name}" "${target}" >&2
      return 1
    fi

    if [[ -e "${target}" ]]; then
      printf 'ERROR  %-37s refusing to overwrite %s\n' "${name}" "${target}" >&2
      return 1
    fi
  done

  mkdir -p -- "${INSTALL_ROOT}"

  for name in "${OWNED_SKILLS[@]}"; do
    source="${SKILLS_ROOT}/${name}"
    target="${INSTALL_ROOT}/${name}"

    if [[ -L "${target}" ]] &&
       link_matches_source "${target}" "${source}"; then
      printf 'SKIP   %-37s already linked\n' "${name}"
      continue
    fi

    if [[ -e "${target}" || -L "${target}" ]]; then
      printf 'ERROR  %-37s refusing to overwrite %s\n' "${name}" "${target}" >&2
      return 1
    fi

    ln -s -- "${source}" "${target}"
    printf 'LINK   %-37s %s\n' "${name}" "${target}"
  done
}

main() {
  if (( $# != 1 )); then
    usage >&2
    return 2
  fi

  case "$1" in
    check)
      check_repository
      ;;
    install)
      install_owned_skills
      ;;
    status)
      local name
      for name in "${OWNED_SKILLS[@]}"; do
        link_state "${name}" || true
      done
      third_party_status
      ;;
    -h|--help)
      usage
      ;;
    *)
      usage >&2
      return 2
      ;;
  esac
}

main "$@"
