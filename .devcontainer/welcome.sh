#!/usr/bin/env bash
# Print a friendly "what to do next" banner on every Codespace start.
set -e

cyan='\033[1;36m'; green='\033[1;32m'; yellow='\033[1;33m'; reset='\033[0m'

cat <<EOF

${cyan}=====================================================================${reset}
${green} Auto-Dock It is ready.${reset}
${cyan}=====================================================================${reset}

 1. Set your Gemini API key (free at https://aistudio.google.com/apikey):

    ${yellow}export GEMINI_API_KEY=your_key_here${reset}

    Or store it once as a Codespaces secret (Settings -> Codespaces ->
    Secrets) and it will be injected automatically on every start.

 2. Run the agentic pipeline on a public GitHub repo:

    ${yellow}autodock run https://github.com/MelvinJoshua1375/githubactions-demo${reset}

 3. Inspect the captured attempts:

    ${yellow}ls output/*/attempts/  &&  cat output/*/validation.txt${reset}

 Other commands:
   ${yellow}autodock doctor${reset}                check env + docker + LLM reachability
   ${yellow}autodock --help${reset}                full command list
   ${yellow}streamlit run streamlit_app.py${reset} local web UI on port 8501

${cyan}=====================================================================${reset}

EOF

# Soft hint if the key is missing.
if [ -z "${GEMINI_API_KEY:-}" ] && [ -z "${GROQ_API_KEY:-}" ]; then
  printf '%b\n' "${yellow}Heads up:${reset} no GEMINI_API_KEY or GROQ_API_KEY in this shell. Set one before running \`autodock run\`."
fi
